#!/usr/bin/env python3
"""Build and BASE-validate Philippines vIS2 agriculture/land spatialization."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import philippines_vis15_water_boundary as v15


ROOT = v15.ROOT
STORAGE = v15.STORAGE
SOURCE = v15.TARGET
TARGET = STORAGE / ".Philippines_vIS2-agriculture-spatial-r3-candidate-20260901"
RUN = "BASE_VIS2_AGRICULTURE_SPATIAL_R3"
BASE = "SC_0"
NODES = ("LUZ", "VIS", "MIN", "OFF")
YEARS = v15.YEARS
LAND_NAMES = tuple(f"LNDAGRPHLC{i:02d}" for i in range(1, 9))
IRRIGATION = "PHL_AGR_IRRIGATION"
IRRIGATION_COMMODITY = "PHL_IRRIGATION_SERVICE"
MODEL = v15.MODEL
TIMEOUT = 500
TAMLL_REL_TOL = 1e-9
CAPACITY_HEADROOM = 1.001
DISABLED_LAND_MODES = frozenset({2, 7, 9, 12, 13, 14, 15, 17, 18, 20, 21, 23})
ACTIVE_LAND_MODES = tuple(mode for mode in range(1, 31) if mode not in DISABLED_LAND_MODES)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream); fields = list(reader.fieldnames or []); old = list(reader)
    identity = fields[0]
    existing = {row[identity] for row in old}
    rows = [row for row in rows if row[identity] not in existing]
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(old); writer.writerows(rows)


def spatial_inputs() -> dict:
    allocation = SOURCE / "data_sources/evidence/v32_rice_spatial_yield/derived/phl_rice_province_cluster_allocation_2020.csv"
    lookup_path = SOURCE / "documentation/province_node_lookup_vIS11.csv"
    land_path = SOURCE / "data_sources/evidence/v32_rice_spatial_yield/reconstructed_geospatial/PHL_LandCover_byCluster_summary.csv"
    lookup = {r["province"]: r["node"] for r in csv.DictReader(lookup_path.open(encoding="utf-8"))}
    rows = list(csv.DictReader(allocation.open(encoding="utf-8")))
    provinces = {r["province"] for r in rows}
    if provinces != set(lookup) or len(provinces) != 81:
        raise RuntimeError("province-node join is not an exact 81-province match")
    raw = defaultdict(float); seen = {}
    for row in rows:
        seen[(row["province"], int(row["clusters_yield"]))] = float(row["allocated_sqkm"])
    for (province, cluster), value in seen.items():
        raw[(lookup[province], cluster)] += value
    cluster_model = {int(r["clusters_yield"]): float(r["sqkm"])
                     for r in csv.DictReader(land_path.open(encoding="utf-8"))}
    adjusted = {}
    for cluster in range(1, 9):
        denominator = sum(raw[(node, cluster)] for node in NODES)
        for node in NODES:
            adjusted[(node, cluster)] = cluster_model[cluster] * raw[(node, cluster)] / denominator
    cropping_intensity = 3253454.36 / 2006000.0
    rice = defaultdict(lambda: {"production_t": 0.0, "harvested_area_ha": 0.0})
    for row in rows:
        key = (lookup[row["province"]], int(row["clusters_yield"]), row["regime"])
        rice[key]["production_t"] += float(row["allocated_production_t"])
        rice[key]["harvested_area_ha"] += float(row["allocated_harvested_area_ha"])
    for (node, cluster, regime), values in rice.items():
        physical = values["harvested_area_ha"] / 100000.0
        if regime == "irrigated": physical /= cropping_intensity
        values["physical_area_1000km2"] = physical
        values["yield_mt_per_1000km2"] = values["production_t"] / 1e6 / physical if physical else 0.0
    for node in NODES:
        for cluster in range(1, 9):
            for regime in ("rainfed", "irrigated"):
                values = rice[(node, cluster, regime)]
                values.setdefault("production_t", 0.0)
                values.setdefault("harvested_area_ha", 0.0)
                values.setdefault("physical_area_1000km2", 0.0)
                values.setdefault("yield_mt_per_1000km2", 0.0)
    return {"lookup": lookup, "allocation_rows": rows, "raw": raw,
            "cluster_model": cluster_model, "adjusted": adjusted,
            "rice": rice, "cropping_intensity": cropping_intensity,
            "allocation_path": allocation, "lookup_path": lookup_path, "land_path": land_path}


def observed_irrigation_stock(lookup: dict[str, str]) -> dict[str, float]:
    path = Path("/tmp/vis2_palay_corn_area.csv")
    if not path.is_file():
        raise FileNotFoundError("official PSA palay/corn area query is absent")
    psa_alias_node = {
        "Zamboanga City": "MIN",
        "Davao de Oro (Compostela Valley)": "MIN",
        "Davao Occidental": "MIN",
        "City of Davao": "MIN",
        "Cotabato (North Cotabato)": "MIN",
        "Maguindanao del Sur": "MIN",
        "Tawi-tawi": "OFF",
    }
    harvested = defaultdict(float)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            geo = row["Geolocation"].lstrip(".")
            if row["Ecosystem/Croptype"] == "Irrigated Palay" and row["2020 Annual"] not in ("", ".."):
                node = lookup.get(geo, psa_alias_node.get(geo))
                if node:
                    harvested[node] += float(row["2020 Annual"])
    total = sum(harvested.values())
    if not math.isclose(total, 3253454.36, abs_tol=0.02):
        raise RuntimeError(f"PSA irrigated harvested-area total mismatch: {total}")
    return {node: 20.06 * harvested[node] / total for node in NODES}


def clone_structure(gen: dict, spatial: dict, stocks: dict) -> dict:
    tech_by_name = {row["Tech"]: row for row in gen["osy-tech"]}
    comm_by_name = {row["Comm"]: row for row in gen["osy-comm"]}
    old_land = {name: tech_by_name[name] for name in LAND_NAMES}
    old_irr = tech_by_name[IRRIGATION]
    old_irr_comm = comm_by_name[IRRIGATION_COMMODITY]
    land_clones = {}; irrigation_clones = {}; irrigation_comms = {}
    for node in NODES:
        cid = f"COM_phl_irrig_vis2_{node.lower()}"
        irrigation_comms[node] = cid
        gen["osy-comm"].append({"CommId": cid, "Comm": f"{IRRIGATION_COMMODITY}_{node}",
                                "Desc": f"Annual irrigation-area service physically installed in {node}.",
                                "UnitId": old_irr_comm["UnitId"]})
        tid = f"TEC_phl_irrig_vis2_{node.lower()}"
        irrigation_clones[node] = tid
        clone = json.loads(json.dumps(old_irr)); clone.update({
            "TechId": tid, "Tech": f"{IRRIGATION}_{node}",
            "Desc": f"Physical irrigation-service stock in {node}; 2020 residual capacity is allocated from observed provincial irrigated-palay area.",
            "OAR": [cid if x == old_irr_comm["CommId"] else x for x in clone["OAR"]],
        })
        gen["osy-tech"].append(clone)
    for cluster, name in enumerate(LAND_NAMES, 1):
        old = old_land[name]
        for node in NODES:
            if spatial["adjusted"][(node, cluster)] <= 1e-9:
                continue
            tid = f"TEC_phl_land_vis2_c{cluster:02d}_{node.lower()}"
            land_clones[(node, cluster)] = tid
            clone = json.loads(json.dumps(old)); clone.update({
                "TechId": tid, "Tech": f"{name}_{node}",
                "Desc": f"{node} share of CLEWs land/yield cluster {cluster}; physical area follows the retained GADM province-cell intersection.",
                "IAR": [irrigation_comms[node] if x == old_irr_comm["CommId"] else x for x in clone["IAR"]],
            })
            gen["osy-tech"].append(clone)
    removed_tech_ids = {row["TechId"] for row in old_land.values()} | {old_irr["TechId"]}
    gen["osy-tech"] = [row for row in gen["osy-tech"] if row["TechId"] not in removed_tech_ids]
    gen["osy-comm"] = [row for row in gen["osy-comm"] if row["CommId"] != old_irr_comm["CommId"]]
    replacements = {old_irr["TechId"]: list(irrigation_clones.values())}
    for cluster, name in enumerate(LAND_NAMES, 1):
        replacements[old_land[name]["TechId"]] = [tid for (node, c), tid in land_clones.items() if c == cluster]
    for constraint in gen["osy-constraints"]:
        expanded = []
        for tid in constraint["CM"]:
            expanded.extend(replacements.get(tid, [tid]))
        constraint["CM"] = expanded
    gen.update({"osy-casename": "Philippines_vIS2", "osy-date": str(date.today()),
                "osy-desc": "Philippines vIS2: vIS1.5 plus LUZ/VIS/MIN/OFF land-cluster and irrigation-stock spatialization."})
    return {"old_land": old_land, "old_irr": old_irr, "old_irr_comm": old_irr_comm,
            "land_clones": land_clones, "irrigation_clones": irrigation_clones,
            "irrigation_comms": irrigation_comms}


def overlay_cloned_parameters(mapping: dict, spatial: dict, stocks: dict) -> None:
    source_gen = read(SOURCE / "genData.json")
    old_land_ids = {i: mapping["old_land"][f"LNDAGRPHLC{i:02d}"]["TechId"] for i in range(1, 9)}
    substitutions = []
    for (node, cluster), new_tid in mapping["land_clones"].items():
        substitutions.append((old_land_ids[cluster], new_tid,
                              mapping["old_irr_comm"]["CommId"], mapping["irrigation_comms"][node]))
    for node, new_tid in mapping["irrigation_clones"].items():
        substitutions.append((mapping["old_irr"]["TechId"], new_tid,
                              mapping["old_irr_comm"]["CommId"], mapping["irrigation_comms"][node]))
    for path in sorted(SOURCE.glob("RY*.json")):
        src = read(path); dst_path = TARGET / path.name; dst = read(dst_path)
        for parameter, scenarios in src.items():
            if parameter not in dst or not isinstance(scenarios, dict):
                continue
            for scenario, rows in scenarios.items():
                if scenario not in dst[parameter] or not isinstance(rows, list):
                    continue
                target_rows = dst[parameter][scenario]
                for old_tid, new_tid, old_cid, new_cid in substitutions:
                    for source_row in rows:
                        if source_row.get("TechId") != old_tid:
                            continue
                        identity = {k: (new_tid if k == "TechId" else new_cid if k == "CommId" and v == old_cid else v)
                                    for k, v in source_row.items() if k not in YEARS}
                        matches = [row for row in target_rows if all(row.get(k) == v for k, v in identity.items())]
                        if len(matches) != 1:
                            raise RuntimeError(f"clone row mismatch {path.name}/{parameter}/{scenario}/{identity}: {len(matches)}")
                        for year in YEARS:
                            matches[0][year] = source_row[year]
        write(dst_path, dst)
    ryt = read(TARGET / "RYT.json")
    ryts = read(TARGET / "RYTs.json")
    min_year_split = {
        year: min(float(row[year]) for row in ryts["YS"][BASE])
        for year in YEARS
    }
    for (node, cluster), tid in mapping["land_clones"].items():
        value = spatial["adjusted"][(node, cluster)] / 1000.0
        for scenario in ryt["TAU"]:
            for parameter in ("TAU", "TAL"):
                row = next(r for r in ryt[parameter][scenario] if r["TechId"] == tid)
                for year in YEARS: row[year] = value
            envelope = next(r for r in ryt["RC"][scenario] if r["TechId"] == tid)
            total_cap = next(r for r in ryt["TAMaxC"][scenario] if r["TechId"] == tid)
            max_investment = next(r for r in ryt["TAMaxCI"][scenario] if r["TechId"] == tid)
            min_investment = next(r for r in ryt["TAMinCI"][scenario] if r["TechId"] == tid)
            for year in YEARS:
                capacity_envelope = CAPACITY_HEADROOM * value / min_year_split[year]
                envelope[year] = capacity_envelope
                total_cap[year] = CAPACITY_HEADROOM * capacity_envelope
                max_investment[year] = 0
                min_investment[year] = 0
    for node, tid in mapping["irrigation_clones"].items():
        row = next(r for r in ryt["RC"][BASE] if r["TechId"] == tid)
        for year in YEARS: row[year] = stocks[node]
    write(TARGET / "RYT.json", ryt)
    # TAMLL is an absolute land-use floor, so allocate rather than duplicate it.
    # Zero TAMUL suppresses redundant per-mode upper rows; AAC2 still enforces TAU.
    source_rytm = read(SOURCE / "RYTM.json")
    rytm = read(TARGET / "RYTM.json")
    for (node, cluster), tid in mapping["land_clones"].items():
        parent_tid = old_land_ids[cluster]
        share = spatial["adjusted"][(node, cluster)] / spatial["cluster_model"][cluster]
        for scenario in rytm["TAMLL"]:
            parent_floor = {row["MoId"]: row for row in source_rytm["TAMLL"][scenario]
                            if row["TechId"] == parent_tid}
            for row in (r for r in rytm["TAMLL"][scenario] if r["TechId"] == tid):
                for year in YEARS:
                    value = parent_floor[row["MoId"]][year]
                    row[year] = None if value is None else float(value) * share
            for row in (r for r in rytm["TAMUL"][scenario] if r["TechId"] == tid):
                for year in YEARS:
                    row[year] = 0
            for parameter in ("TAIML", "TADML", "VC"):
                for row in (r for r in rytm[parameter][scenario]
                            if r["TechId"] == tid and r["MoId"] in DISABLED_LAND_MODES):
                    for year in YEARS:
                        row[year] = 0 if scenario == BASE else None
    write(TARGET / "RYTM.json", rytm)

    # A mode exists in generated MODEperTECHNOLOGY when any IAR/OAR/EAR/EACR row
    # is nonzero. Clear all such coefficients for the structurally disabled modes.
    for filename in ("RYTCM.json", "RYTEM.json"):
        data = read(TARGET / filename)
        for scenarios in data.values():
            for scenario, rows in scenarios.items():
                for row in rows:
                    if row.get("TechId") in mapping["land_clones"].values() and row.get("MoId") in DISABLED_LAND_MODES:
                        for year in YEARS:
                            row[year] = 0 if scenario == BASE else None
        write(TARGET / filename, data)
    gen = read(TARGET / "genData.json")
    crop_cid = next(r["CommId"] for r in gen["osy-comm"] if r["Comm"] == "CRPRCP")
    rytcm = read(TARGET / "RYTCM.json")
    mode_regime = {11: "rainfed", 19: "irrigated"}
    for (node, cluster), tid in mapping["land_clones"].items():
        for mode, regime in mode_regime.items():
            row = next(r for r in rytcm["OAR"][BASE]
                       if r["TechId"] == tid and r["CommId"] == crop_cid and r["MoId"] == mode)
            new_anchor = spatial["rice"][(node, cluster, regime)]["yield_mt_per_1000km2"]
            old_anchor = float(row["2020"])
            for year in YEARS:
                row[year] = new_anchor * float(row[year]) / old_anchor
    write(TARGET / "RYTCM.json", rytcm)


def write_evidence(spatial: dict, stocks: dict, mapping: dict) -> None:
    evidence = TARGET / "data_sources/evidence/vIS2_agriculture_spatial_2026-09-01"
    evidence.mkdir(parents=True, exist_ok=True)
    for name in ("vis2_palay_corn_production.csv", "vis2_palay_corn_area.csv",
                 "vis2_major_crop_production.csv", "vis2_major_crop_area.csv"):
        shutil.copy2(Path("/tmp") / name, evidence / name)
    with (evidence / "node_cluster_land_allocation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream); writer.writerow(["node", "cluster", "raw_gadm_intersection_km2", "adjusted_model_km2", "model_1000km2"])
        for node in NODES:
            for cluster in range(1, 9):
                writer.writerow([node, cluster, spatial["raw"][(node, cluster)], spatial["adjusted"][(node, cluster)], spatial["adjusted"][(node, cluster)]/1000])
    with (evidence / "irrigation_stock_by_node.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream); writer.writerow(["node", "residual_capacity_1000km2"])
        writer.writerows((node, stocks[node]) for node in NODES)
    with (evidence / "rice_node_cluster_yields_2020.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream); writer.writerow(["node", "cluster", "regime", "production_t", "harvested_area_ha", "physical_area_1000km2", "yield_mt_per_1000km2"])
        for node in NODES:
            for cluster in range(1, 9):
                for regime in ("rainfed", "irrigated"):
                    row = spatial["rice"][(node, cluster, regime)]
                    writer.writerow([node, cluster, regime, row["production_t"], row["harvested_area_ha"], row["physical_area_1000km2"], row["yield_mt_per_1000km2"]])
    sources = TARGET / "data_sources/SOURCES.csv"
    append_csv(sources, [
        {"source_id":"SRC_PHL_VIS2_PSA_PALAY_CORN_2020", "provider":"Philippine Statistics Authority", "product":"OpenSTAT Palay and Corn production and harvested-area PXWeb tables", "edition":"API re-query retrieved 2026-08-31", "reference_period":"2020 Annual", "geography":"Philippines; region and province", "variable":"Irrigated and rainfed palay and corn production and harvested area", "source_unit":"metric tonnes; hectares", "exact_locator":"Tables 0012E4EVCP0 and 0022E4EAHC0; 2020 Annual; all ecosystems/crop types; all geolocations", "url":"https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS/0012E4EVCP0.px; https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS/0022E4EAHC0.px", "access_date":"2026-08-31", "license":"Philippine government open-data terms", "sha256":"production=ff8a9d1a58fe56136f7ad9fbc661b24c06e909b18da1f04c8d35259946be2488;area=98cc046d81afe70488e596d07ed320d646a071dd377b8d1a5c62449dfaaa1ae4", "local_file":"evidence/vIS2_agriculture_spatial_2026-09-01/vis2_palay_corn_production.csv; evidence/vIS2_agriculture_spatial_2026-09-01/vis2_palay_corn_area.csv", "notes":"Full-precision official API re-query; the vIS2 build uses palay rows and retains corn rows for validation."},
        {"source_id":"SRC_PHL_VIS2_PSA_MAJOR_CROPS_2020", "provider":"Philippine Statistics Authority", "product":"OpenSTAT Selected Major Crops production and area PXWeb tables", "edition":"API re-query retrieved 2026-08-31", "reference_period":"2020 Annual", "geography":"Philippines and region", "variable":"Production and area of selected major crops", "source_unit":"metric tonnes; hectares", "exact_locator":"Tables 0142E4EVCP1 and 0152E4EAHM0; 2020 Annual; all crops; all geolocations", "url":"https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS/0142E4EVCP1.px; https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS/0152E4EAHM0.px", "access_date":"2026-08-31", "license":"Philippine government open-data terms", "sha256":"production=60b269d15ea34e7920a60921cbf2e9ff1f1382c6fbc07586adaa2de1c8374c93;area=03b0f8adfe3e1ff3b3e6dd493a98d5d36591dae092f0a4a559962a8d1efa1d8c", "local_file":"evidence/vIS2_agriculture_spatial_2026-09-01/vis2_major_crop_production.csv; evidence/vIS2_agriculture_spatial_2026-09-01/vis2_major_crop_area.csv", "notes":"Retained as regional validation evidence; no non-rice crop activity or regional share is imposed."},
        {"source_id":"SRC_PHL_VIS2_GADM_CLUSTER_LEDGER", "provider":"GADM and retained CLEWs/GAEZ reconstruction", "product":"GADM 4.1 level-1 province by recovered CLEWs cell-cluster intersection ledger", "edition":"GADM 4.1; reconstruction retained 2026-08-27", "reference_period":"Boundary version 4.1; model land base 2020", "geography":"Philippines; all 81 provinces and eight CLEWs clusters", "variable":"Province-cluster land intersection and allocated 2020 palay production and harvested area", "source_unit":"km2; metric tonnes; hectares", "exact_locator":"evidence/v32_rice_spatial_yield/manifest.json and derived/phl_rice_province_cluster_allocation_2020.csv", "url":"https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_PHL_shp.zip", "access_date":"2026-08-27", "license":"GADM license and provider terms; PSA open-data terms for agricultural observations", "sha256":"GADM_archive=a7bb9d6593fbc372bb10c80af8714ec04f12df18e9bc6b36565878f43b93b566;derived_ledger=5b07ebbe104e3e536ba36f3a646542fc13777c6194ff575aac674c91241cd366", "local_file":"evidence/v32_rice_spatial_yield/derived/phl_rice_province_cluster_allocation_2020.csv", "notes":"The manifest freezes the official archive checksum, recovered 3,457-cell layer, derivation code and validation; the level-1 archive is not duplicated locally."},
    ])
    append_csv(TARGET / "data_sources/ASSUMPTIONS.csv", [
        {"assumption_id":"ASM_PHL_VIS2_CLEWS_AREA_ADJUSTMENT", "statement":"Allocate each cluster's difference between raw GADM-intersected area and the CLEWs adjusted model area proportionally across its observed node shares.", "evidence_source_ids":"SRC_PHL_VIS2_GADM_CLUSTER_LEDGER", "rationale":"Preserves both exact model cluster totals and observed province-node geography without fabricating new geometry."},
        {"assumption_id":"ASM_PHL_VIS2_OFF_NODE", "statement":"Retain OFF as an explicit fourth residual geography for land and agriculture.", "evidence_source_ids":"SRC_PHL_VIS2_GADM_CLUSTER_LEDGER", "rationale":"Avoids silently reallocating the 14 OFF provinces to grid-island nodes; agricultural output can enter the national crop market."},
        {"assumption_id":"ASM_PHL_VIS2_WITHIN_PROVINCE_CROP_ALLOCATION", "statement":"Within each province and water regime, allocate observed palay production and harvested area to CLEWs clusters in proportion to the province's intersected cluster land.", "evidence_source_ids":"SRC_PHL_VIS2_GADM_CLUSTER_LEDGER;SRC_PHL_VIS2_PSA_PALAY_CORN_2020", "rationale":"No public crop observation exists at the CLEWs-cell level; this transparent allocation preserves every provincial total and is used to derive spatial yield drivers, not to impose activity shares.", "notes":"Documented and reproducible in evidence/v32_rice_spatial_yield/derive_philippines_rice_cluster_yields.py and manifest.json."},
        {"assumption_id":"ASM_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "statement":"Represent the land technology capacity side as a nonbinding numerical envelope with 0.1% headroom above the maximum timeslice rate implied by annual TAU; prohibit all new land capacity.", "evidence_source_ids":"", "rationale":"Physical land is limited by annual TAL/TAU. The envelope retains unchanged OSeMOSYS CAa4 equations without creating an exact-binding timeslice surface or a cost-free NewCapacity plateau."},
    ])
    append_csv(TARGET / "data_sources/CALCULATIONS.csv", [
        {"calculation_id":"CALC_PHL_VIS2_NODE_CLUSTER_AREA", "formula":"adjusted_node_cluster_km2=model_cluster_km2*raw_node_cluster_km2/sum_nodes(raw_node_cluster_km2)", "source_ids":"SRC_PHL_VIS2_GADM_CLUSTER_LEDGER", "assumption_ids":"ASM_PHL_VIS2_CLEWS_AREA_ADJUSTMENT", "input_values":"81-province GADM intersections; 8 CLEWs cluster totals", "input_units":"km2", "output_value":"evidence/vIS2_agriculture_spatial_2026-09-01/node_cluster_land_allocation.csv", "output_unit":"km2 and 1000 km2", "script_path":"scripts/philippines_vis2_agriculture_spatial.py", "script_version":"r3"},
        {"calculation_id":"CALC_PHL_VIS2_PROVINCE_CLUSTER_CROP_ALLOCATION", "formula":"allocated_value(province,cluster,regime)=observed_value(province,regime)*intersected_land(province,cluster)/sum_clusters(intersected_land(province,cluster))", "source_ids":"SRC_PHL_VIS2_PSA_PALAY_CORN_2020;SRC_PHL_VIS2_GADM_CLUSTER_LEDGER", "assumption_ids":"ASM_PHL_VIS2_WITHIN_PROVINCE_CROP_ALLOCATION", "input_values":"province palay production and harvested area by regime; province-cluster intersections", "input_units":"t;ha;km2", "output_value":"evidence/v32_rice_spatial_yield/derived/phl_rice_province_cluster_allocation_2020.csv", "output_unit":"t;ha", "script_path":"data_sources/evidence/v32_rice_spatial_yield/derive_philippines_rice_cluster_yields.py", "script_version":"sha256 1cc8b2546cf60b2799097a47b06bac6b05158d248896e5c398ee234c3a4e1ae9", "notes":"All provincial totals reconcile; the allocation is a yield-driver derivation and does not constrain modeled activity."},
        {"calculation_id":"CALC_PHL_VIS2_IRRIGATION_STOCK", "formula":"20.06*node irrigated-palay harvested area/national harvested area", "source_ids":"SRC_PHL_VIS2_PSA_PALAY_CORN_2020;SRC_PSA_SSAF_2022", "assumption_ids":"ASM_PHL_V24_IRRIGATION_STOCK", "input_calculation_ids":"CALC_PHL_V16_RICE_CAPACITY;CALC_PHL_VIS2_PROVINCE_CLUSTER_CROP_ALLOCATION", "input_values":"3,253,454.36 ha national; 20.06 thousand km2 physical stock", "input_units":"ha;1000 km2", "output_value":json.dumps(stocks, sort_keys=True), "output_unit":"1000 km2", "script_path":"scripts/philippines_vis2_agriculture_spatial.py", "script_version":"r3"},
        {"calculation_id":"CALC_PHL_VIS2_RICE_NODE_CLUSTER_YIELDS", "formula":"production_mt/physical_area_1000km2; irrigated physical area=harvested area/(100000*1.6218615952143568)", "source_ids":"SRC_PHL_VIS2_PSA_PALAY_CORN_2020;SRC_PHL_VIS2_GADM_CLUSTER_LEDGER;SRC_PSA_SSAF_2022", "assumption_ids":"ASM_PHL_VIS2_WITHIN_PROVINCE_CROP_ALLOCATION;ASM_PHL_V16_IRRIGATION_CROPPING_INTENSITY", "input_calculation_ids":"CALC_PHL_VIS2_PROVINCE_CLUSTER_CROP_ALLOCATION;CALC_PHL_V16_RICE_CROPPING_INTENSITY", "input_values":"province-regime production and harvested area allocated by retained province-cluster shares", "input_units":"t;ha", "output_value":"evidence/vIS2_agriculture_spatial_2026-09-01/rice_node_cluster_yields_2020.csv", "output_unit":"Mt/1000 km2", "script_path":"scripts/philippines_vis2_agriculture_spatial.py", "script_version":"r3"},
        {"calculation_id":"CALC_PHL_VIS2_TAMLL_ALLOCATION", "formula":"clone_TAMLL=parent_TAMLL*clone_TAU/parent_TAU", "source_ids":"", "assumption_ids":"ASM_PHL_VIS2_CLEWS_AREA_ADJUSTMENT", "input_values":"parent cluster mode/year TAMLL and node-cluster area shares", "input_units":"1000 km2;dimensionless share", "output_value":"RYTM.json/TAMLL", "output_unit":"1000 km2", "script_path":"scripts/philippines_vis2_agriculture_spatial.py", "script_version":"r3"},
        {"calculation_id":"CALC_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "formula":"RC=1.001*TAU/min_timeslice(YearSplit); TAMaxC=1.001*RC; TAMaxCI=TAMinCI=0", "source_ids":"", "assumption_ids":"ASM_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "input_values":"node-cluster TAU and model YearSplit", "input_units":"1000 km2;year share", "output_value":"RYT.json/RC,TAMaxC,TAMaxCI,TAMinCI", "output_unit":"1000 km2", "script_path":"scripts/philippines_vis2_agriculture_spatial.py", "script_version":"r3"},
    ])
    append_csv(TARGET / "data_sources/MODEL_MAP.csv", [
        {"map_id":"MAP_PHL_VIS2_LAND_CLUSTER_NODES", "model_file":"genData.json;RYT.json", "parameter":"technology structure;TAU;TAL", "entity":"LNDAGRPHLC01-08_{LUZ,VIS,MIN,OFF} where intersection is nonzero", "mode":"all", "scenario":"SC_0 with policy inheritance", "years":"2020-2053", "value_or_expression":"CALC_PHL_VIS2_NODE_CLUSTER_AREA", "model_unit":"1000 km2", "evidence_ids":"CALC_PHL_VIS2_NODE_CLUSTER_AREA", "evidence_type":"continuing physical land constraint"},
        {"map_id":"MAP_PHL_VIS2_IRRIGATION_NODES", "model_file":"genData.json;RYT.json;RYTCM.json", "parameter":"node commodity;ResidualCapacity;IAR/OAR", "entity":"PHL_AGR_IRRIGATION_{LUZ,VIS,MIN,OFF}", "mode":"1 and irrigated crop modes", "scenario":"SC_0 with policy inheritance", "years":"2020-2053", "value_or_expression":"CALC_PHL_VIS2_IRRIGATION_STOCK", "model_unit":"1000 km2", "evidence_ids":"CALC_PHL_VIS2_IRRIGATION_STOCK", "evidence_type":"initial physical stock"},
        {"map_id":"MAP_PHL_VIS2_RICE_NODE_CLUSTER_YIELDS", "model_file":"RYTCM.json", "parameter":"OAR", "entity":"LNDAGRPHLC01-08_{LUZ,VIS,MIN,OFF}", "mode":"11 rainfed;19 irrigated", "scenario":"SC_0 with policy inheritance", "years":"2020-2053", "value_or_expression":"2020 node-cluster achieved yield; inherited parent-cluster year/2020 trajectory", "model_unit":"Mt/1000 km2", "evidence_ids":"CALC_PHL_VIS2_RICE_NODE_CLUSTER_YIELDS", "evidence_type":"physical achieved-yield driver"},
        {"map_id":"MAP_PHL_VIS2_LAND_MODE_FLOORS", "model_file":"RYTM.json", "parameter":"TAMLL;TAMUL", "entity":"29 LNDAGRPHLC node-cluster technologies", "mode":"active modes; disabled set 2,7,9,12,13,14,15,17,18,20,21,23 excluded from generated MODEperTECHNOLOGY", "scenario":"all", "years":"2020-2053", "value_or_expression":"CALC_PHL_VIS2_TAMLL_ALLOCATION; TAMUL=0 because AAC2 implies each nonnegative mode is <=TAU", "model_unit":"1000 km2", "evidence_ids":"CALC_PHL_VIS2_TAMLL_ALLOCATION", "evidence_type":"continuing physical land allocation and structural cleanup"},
        {"map_id":"MAP_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "model_file":"RYT.json", "parameter":"RC;TAMaxC;TAMaxCI;TAMinCI", "entity":"29 LNDAGRPHLC node-cluster technologies", "mode":"all retained", "scenario":"all", "years":"2020-2053", "value_or_expression":"CALC_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "model_unit":"1000 km2", "evidence_ids":"CALC_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "evidence_type":"nonbinding formulation envelope; physical cap remains TAL/TAU"},
        {"map_id":"MAP_PHL_VIS2_DISABLED_LAND_MODES", "model_file":"RYTM.json;RYTCM.json;RYTEM.json", "parameter":"TAIML;TADML;VC;IAR;OAR;EAR", "entity":"29 LNDAGRPHLC node-cluster technologies", "mode":"2;7;9;12;13;14;15;17;18;20;21;23", "scenario":"all", "years":"2020-2053", "value_or_expression":"zero in BASE and null in overlays so the modes are absent from generated MODEperTECHNOLOGY", "model_unit":"parameter-specific", "evidence_ids":"ASM_PHL_VIS2_LAND_CAPACITY_ENVELOPE", "evidence_type":"structural cleanup", "notes":"Zeroing TAMUL alone would remove LU1 because of its nonzero guard; all activity coefficients are cleared instead. Preflight proves every clone has exactly the 18 retained modes."},
        {"map_id":"MAP_PHL_VIS2_CLONE_INHERITANCE", "model_file":"RY*.json", "parameter":"all technology-indexed rows except explicitly remapped area, floors, capacity envelope, disabled-mode coefficients, rice OAR and irrigation RC", "entity":"29 land clones and four irrigation-service clones", "mode":"all retained", "scenario":"all", "years":"2020-2053", "value_or_expression":"exact parent parameter value copied by full row identity with technology and irrigation-commodity substitution", "model_unit":"parameter-specific", "evidence_ids":"SRC_PHL_INHERITED_BASE_SNAPSHOT", "evidence_type":"inherited model parameter", "notes":"This includes irrigation costs, lifetime representation, efficiencies and post-2020 build freedom; no node-specific value is invented."},
    ])
    append_csv(TARGET / "data_sources/GAPS.csv", [
        {"item":"Subnational non-rice crop observations below region", "why_absent":"The retained major-crop OpenSTAT table exposes regions, while palay/corn exposes provinces.", "upgrade_source":"Province-level coconut, sugarcane and other crop area/production series or PSA microdata.", "priority":"high", "notes":"No modeled crop share or production is forced."},
        {"item":"Subnational water withdrawal and resource caps", "why_absent":"No public subnational withdrawal series exists and hydrologic units do not follow island nodes.", "upgrade_source":"NWRB basin/aquifer framework and demand-side withdrawal allocation research.", "priority":"high", "notes":"vIS2 retains the national surface and groundwater UDC caps from vIS1.5."},
    ])
    append_csv(TARGET / "data_sources/CHANGES.csv", [
        {"change_id":"CHG_PHL_VIS2_AGRICULTURE_SPATIAL_R3_20260901", "date":"2026-09-01", "class":"B", "description":"Split eight land/yield clusters and irrigation infrastructure across LUZ/VIS/MIN/OFF; allocate absolute TAMLL floors rather than duplicating them; remove disabled land modes from generated mode sets; and prohibit cost-free land NewCapacity.", "model_objects":"genData.json;RY*.json", "evidence_path":"documentation/MODEL_FIXES_AGRICULTURE_SPATIAL_VIS2_2026-09-01.md", "map_rows_affected":"MAP_PHL_VIS2_LAND_CLUSTER_NODES;MAP_PHL_VIS2_IRRIGATION_NODES;MAP_PHL_VIS2_RICE_NODE_CLUSTER_YIELDS;MAP_PHL_VIS2_LAND_MODE_FLOORS;MAP_PHL_VIS2_LAND_CAPACITY_ENVELOPE;MAP_PHL_VIS2_DISABLED_LAND_MODES;MAP_PHL_VIS2_CLONE_INHERITANCE", "resolve_status":"candidate_pending_BASE", "author":"Codex", "commit":"", "notes":"No crop activity, production, mix, irrigation use or node share is forced. TAMLL reconciliation uses relative tolerance 1e-9; generated LP must fix every land NewCapacity variable at zero."},
    ])
    note = TARGET / "documentation/MODEL_FIXES_AGRICULTURE_SPATIAL_VIS2_2026-09-01.md"
    note.write_text(f"""# Philippines vIS2 agriculture and land spatialization

Date: 2026-09-01
Parent: Philippines vIS1.5
Status: candidate; BASE only; not promoted

## Equation-first classification

The retained GADM province-cell intersections and CLEWs adjusted cluster areas are continuing physical land constraints. Official 2020 irrigated-palay harvested area allocates the inherited 20.06-thousand-km2 irrigation residual stock and is an initial-stock observation. Provincial crop area and production otherwise remain validation benchmarks. No crop activity, crop production, crop share, source share, irrigation use, or node outcome is fixed.

The eight national cluster technologies are replaced by {len(mapping['land_clones'])} nonzero node-cluster intersections. Rainfed and irrigated rice OARs are recalculated from the retained PSA/GADM node-cluster allocation, with the parent yield trajectory preserved after 2020. `TAU=TAL` is split by the retained province-node geometry and reconciles to every parent cluster within relative tolerance {TAMLL_REL_TOL}. OFF remains an explicit residual node.

Each absolute parent `TAMLL` mode/year floor is allocated by the same node share as `TAU` and `TAL`; it is never copied at national magnitude into each clone. The epsilon-disabled modes {sorted(DISABLED_LAND_MODES)} are removed from each clone's generated `MODEperTECHNOLOGY` by clearing their IAR/OAR/EAR/EACR coefficients. For the {len(ACTIVE_LAND_MODES)} retained modes, `TAMUL=0` suppresses redundant LU1 rows because nonnegative activity and annual AAC2 already imply each mode cannot exceed total `TAU`.

Land is not an investable technology. `TAMaxCI=TAMinCI=0` fixes `NewCapacity` at zero. A nonbinding formulation envelope, `RC=1.001*TAU/min(YearSplit)` and `TAMaxC=1.001*RC`, preserves the unchanged CAa4/CAb1 equations with at least 0.1% timeslice headroom. The physical land statement remains in annual `TAL=TAU`; the residual-capacity value is explicitly not interpreted as additional physical land.

The national irrigation-service technology and commodity are replaced by four node technologies and commodities. Their residual capacities sum to the unchanged 20.06. Capital cost, variable cost, lifetime, build freedom after 2020, and all irrigated-mode service coefficients are inherited. National crop markets, national raw agricultural water, and the vIS1.5 national surface/groundwater UDCs remain unchanged.

## Validation contract

Before solving: exact 81-province join; land and irrigation reconciliation; every clone's summed mode floors within its total activity; parent-to-clone `TAMLL` reconciliation using relative tolerance {TAMLL_REL_TOL}; structural absence of disabled modes; 0.1% CAa4 headroom; application generation and preprocessing; `glpsol --check`; and direct LP proof that all {len(mapping['land_clones']) * len(YEARS)} land `NewCapacity` variables are fixed at zero. Then run one BASE optimization with a {TIMEOUT}-second timeout and stop. No policy solve, seal, or promotion is authorized.
""", encoding="utf-8")
    return evidence


def build() -> None:
    if TARGET.exists():
        raise FileExistsError(f"candidate exists: {TARGET}")
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("res", ".DS_Store"))
    spatial = spatial_inputs(); stocks = observed_irrigation_stock(spatial["lookup"])
    gen = read(TARGET / "genData.json")
    mapping = clone_structure(gen, spatial, stocks)
    v15.Config.DATA_STORAGE = STORAGE
    v15.UpdateCase(TARGET.name, gen).updateCase()
    write(TARGET / "genData.json", gen)
    overlay_cloned_parameters(mapping, spatial, stocks)
    evidence = write_evidence(spatial, stocks, mapping)
    manifest = {"schema":"philippines-vis2-agriculture-spatial-build-v1", "source_case":str(SOURCE), "candidate":str(TARGET),
                "land_clone_count":len(mapping["land_clones"]), "irrigation_clone_count":4,
                "adjusted_land_km2":sum(spatial["adjusted"].values()), "irrigation_stock_1000km2":sum(stocks.values()),
                "node_land_km2":{node:sum(spatial["adjusted"][(node,c)] for c in range(1,9)) for node in NODES},
                "node_irrigation_stock_1000km2":stocks, "optimizer_runs":0, "evidence":str(evidence)}
    write(TARGET / "documentation/vis2_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


def preflight() -> None:
    gen = read(TARGET / "genData.json"); names={r["Tech"]:r["TechId"] for r in gen["osy-tech"]}; comms={r["Comm"] for r in gen["osy-comm"]}
    spatial=spatial_inputs(); stocks=observed_irrigation_stock(spatial["lookup"]); checks={}
    checks["81_province_join"] = len(spatial["lookup"]) == 81
    checks["national_land_exact"] = math.isclose(sum(spatial["adjusted"].values()), 295813.1, abs_tol=1e-7)
    checks["cluster_land_exact"] = all(math.isclose(sum(spatial["adjusted"][(n,c)] for n in NODES), spatial["cluster_model"][c], abs_tol=1e-7) for c in range(1,9))
    expected_land={f"LNDAGRPHLC{c:02d}_{n}" for n in NODES for c in range(1,9) if spatial["adjusted"][(n,c)]>1e-9}
    checks["land_structure"] = expected_land <= set(names) and not any(n in names for n in LAND_NAMES) and len(expected_land)==29
    checks["irrigation_structure"] = all(f"{IRRIGATION}_{n}" in names and f"{IRRIGATION_COMMODITY}_{n}" in comms for n in NODES) and IRRIGATION not in names and IRRIGATION_COMMODITY not in comms
    checks["no_zero_area_node_cluster_techs"] = not any(
        f"LNDAGRPHLC{c:02d}_{n}" in names for n in NODES for c in range(1, 9)
        if spatial["adjusted"][(n, c)] <= 1e-9
    )
    checks["no_crop_aggregation_objects"] = not any(
        ("AGG" in row["Tech"] or "AGG" in row["Desc"].upper()) and "CROP" in (row["Tech"] + row["Desc"]).upper()
        for row in gen["osy-tech"]
    ) and not any(row["Comm"].startswith(("CRPRCP_", "CRPMZE_", "CRPCON_", "CRPSGC_")) for row in gen["osy-comm"])
    checks["irrigation_stock_exact"] = math.isclose(sum(stocks.values()),20.06,abs_tol=1e-10)
    checks["local_rice_area_fits_node_cluster_land"] = all(
        spatial["rice"][(node, cluster, "irrigated")]["physical_area_1000km2"]
        + spatial["rice"][(node, cluster, "rainfed")]["physical_area_1000km2"]
        <= spatial["adjusted"][(node, cluster)] / 1000.0 + 1e-10
        for node in NODES for cluster in range(1, 9)
    )
    checks["local_irrigated_area_equals_local_stock"] = all(
        math.isclose(sum(spatial["rice"][(node, cluster, "irrigated")]["physical_area_1000km2"]
                         for cluster in range(1, 9)), stocks[node], abs_tol=1e-10)
        for node in NODES
    )
    ryt=read(TARGET/"RYT.json"); ryts=read(TARGET/"RYTs.json")
    rytm=read(TARGET/"RYTM.json"); rytcm=read(TARGET/"RYTCM.json"); rytem=read(TARGET/"RYTEM.json")
    source_rytm=read(SOURCE/"RYTM.json")
    source_names={r["Tech"]:r["TechId"] for r in read(SOURCE/"genData.json")["osy-tech"]}
    crop_cid=next(r["CommId"] for r in gen["osy-comm"] if r["Comm"]=="CRPRCP")
    land_tids=set()
    for n in NODES:
        for c in range(1,9):
            name=f"LNDAGRPHLC{c:02d}_{n}"
            if name not in names: continue
            value=spatial["adjusted"][(n,c)]/1000
            land_tids.add(names[name])
            for p in ("TAU","TAL"):
                row=next(r for r in ryt[p][BASE] if r["TechId"]==names[name])
                checks[f"{p}_{name}"]=all(math.isclose(float(row[y]),value,abs_tol=1e-10) for y in YEARS)
            tid=names[name]
            for mode, regime in ((11,"rainfed"),(19,"irrigated")):
                oar=next(r for r in rytcm["OAR"][BASE] if r["TechId"]==tid and r["MoId"]==mode and r["CommId"]==crop_cid)
                expected=spatial["rice"][(n,c,regime)]["yield_mt_per_1000km2"]
                checks[f"rice_oar_{name}_{mode}"]=math.isclose(float(oar["2020"]),expected,abs_tol=1e-10)
            floor_rows=[r for r in rytm["TAMLL"][BASE] if r["TechId"]==tid]
            total_row=next(r for r in ryt["TAL"][BASE] if r["TechId"]==tid)
            checks[f"mode_floor_within_total_{name}"]=all(
                sum(float(r[year]) for r in floor_rows) <= float(total_row[year]) * (1 + TAMLL_REL_TOL)
                for year in YEARS
            )
            rc=next(r for r in ryt["RC"][BASE] if r["TechId"]==tid)
            max_cap=next(r for r in ryt["TAMaxC"][BASE] if r["TechId"]==tid)
            max_inv=next(r for r in ryt["TAMaxCI"][BASE] if r["TechId"]==tid)
            min_inv=next(r for r in ryt["TAMinCI"][BASE] if r["TechId"]==tid)
            checks[f"capacity_envelope_{name}"]=all(
                math.isclose(float(rc[year]), CAPACITY_HEADROOM*value/min(float(r[year]) for r in ryts["YS"][BASE]), rel_tol=1e-12)
                and math.isclose(float(max_cap[year]), CAPACITY_HEADROOM*float(rc[year]), rel_tol=1e-12)
                and float(max_inv[year]) == 0 and float(min_inv[year]) == 0
                and float(rc[year])*min(float(r[year]) for r in ryts["YS"][BASE]) >= CAPACITY_HEADROOM*value*(1-1e-12)
                for year in YEARS
            )
    # Reconcile every absolute parent mode/year floor to its node clones. This
    # deliberately uses relative tolerance because the area shares carry ~1e-14
    # floating-point reconciliation noise.
    tamll_reconciles=True
    tamll_proportional=True
    for cluster, parent_name in enumerate(LAND_NAMES, 1):
        parent_tid=source_names[parent_name]
        clone_tids=[names[f"{parent_name}_{node}"] for node in NODES if f"{parent_name}_{node}" in names]
        clone_shares={names[f"{parent_name}_{node}"]:spatial["adjusted"][(node,cluster)]/spatial["cluster_model"][cluster]
                      for node in NODES if f"{parent_name}_{node}" in names}
        for scenario, parent_rows in source_rytm["TAMLL"].items():
            for parent_row in (r for r in parent_rows if r["TechId"]==parent_tid):
                clone_rows=[next(r for r in rytm["TAMLL"][scenario]
                                 if r["TechId"]==tid and r["MoId"]==parent_row["MoId"])
                            for tid in clone_tids]
                for year in YEARS:
                    parent_value=parent_row[year]
                    clone_values=[r[year] for r in clone_rows]
                    if parent_value is None:
                        tamll_reconciles &= all(v is None for v in clone_values)
                        tamll_proportional &= all(v is None for v in clone_values)
                    else:
                        tamll_reconciles &= all(v is not None for v in clone_values) and math.isclose(
                            sum(float(v) for v in clone_values), float(parent_value),
                            rel_tol=TAMLL_REL_TOL, abs_tol=0.0)
                        tamll_proportional &= all(
                            math.isclose(float(row[year]), float(parent_value)*clone_shares[row["TechId"]],
                                         rel_tol=TAMLL_REL_TOL, abs_tol=0.0)
                            for row in clone_rows
                        )
    checks["TAMLL_parent_clone_reconciliation_rel_1e_9"]=tamll_reconciles
    checks["TAMLL_node_area_share_allocation_rel_1e_9"]=tamll_proportional
    checks["no_redundant_land_TAMUL"]=all(
        row[year] in (0, None) for rows in rytm["TAMUL"].values()
        for row in rows if row["TechId"] in land_tids for year in YEARS
    )
    checks["disabled_land_mode_coefficients_zero"]=all(
        row[year] in (0, None)
        for data in (rytcm, rytem) for scenarios in data.values() for rows in scenarios.values()
        for row in rows if row.get("TechId") in land_tids and row.get("MoId") in DISABLED_LAND_MODES
        for year in YEARS
    )
    checks["disabled_land_mode_floors_zero"]=all(
        row[year] in (0, None) for rows in rytm["TAMLL"].values() for row in rows
        if row["TechId"] in land_tids and row["MoId"] in DISABLED_LAND_MODES for year in YEARS
    )
    checks["land_investment_zero_all_scenarios"]=all(
        float(row[year]) == 0 for parameter in ("TAMaxCI", "TAMinCI")
        for rows in ryt[parameter].values() for row in rows if row["TechId"] in land_tids for year in YEARS
    )
    checks["no_land_99999_or_999999_bounds"]=all(
        row[year] not in (99999, 999999) for parameter in ("TAMaxC", "TAMaxCI")
        for rows in ryt[parameter].values() for row in rows if row["TechId"] in land_tids for year in YEARS
    )
    checks["no_other_copied_absolute_lower_bound"]=all(
        row[year] in (0, None) for parameter in ("TAIML", "TADML")
        for rows in rytm[parameter].values() for row in rows if row["TechId"] in land_tids for year in YEARS
    ) and all(
        row[year] in (0, None) for parameter in ("TAMinC", "TAMinCI")
        for rows in ryt[parameter].values() for row in rows if row["TechId"] in land_tids for year in YEARS
    )
    source_gen = read(SOURCE / "genData.json")
    source_constraints = {r["Con"]: r["ConId"] for r in source_gen["osy-constraints"]}
    target_constraints = {r["Con"]: r["ConId"] for r in gen["osy-constraints"]}
    src_rycn, dst_rycn = read(SOURCE / "RYCn.json"), read(TARGET / "RYCn.json")
    checks["water_cap_rhs_unchanged"] = all(
        next(r for r in src_rycn["UCC"][scenario] if r["ConId"] == source_constraints[con]) ==
        next(r for r in dst_rycn["UCC"][scenario] if r["ConId"] == target_constraints[con])
        for con in ("WATER_SUR_AVAIL", "WATER_GWT_POTENTIAL") for scenario in src_rycn["UCC"]
    )
    src_rtcn, dst_rtcn = read(SOURCE / "RYTCn.json"), read(TARGET / "RYTCn.json")
    water_techs = {r["TechId"] for r in source_gen["osy-tech"] if "_WAT" in r["Tech"] and r["Tech"].startswith("PHL_DEM_")} | {
        next(r["TechId"] for r in source_gen["osy-tech"] if r["Tech"] == name) for name in ("DEMAGRSURPHL", "DEMAGRGWTPHL")
    }
    checks["water_cap_coefficients_unchanged"] = all(
        sorted((r for r in src_rtcn[p][s] if r["TechId"] in water_techs and r["ConId"] in {source_constraints["WATER_SUR_AVAIL"], source_constraints["WATER_GWT_POTENTIAL"]}), key=lambda r:(r["TechId"],r["ConId"])) ==
        sorted((r for r in dst_rtcn[p][s] if r["TechId"] in water_techs and r["ConId"] in {target_constraints["WATER_SUR_AVAIL"], target_constraints["WATER_GWT_POTENTIAL"]}), key=lambda r:(r["TechId"],r["ConId"]))
        for p in ("CAM", "CCM", "CNCM") for s in src_rtcn[p]
    )
    failures=[k for k,v in checks.items() if not v]
    report={"schema":"philippines-vis2-preflight-v1","status":"passed" if not failures else "failed","checks":checks,"failures":failures,"optimizer_runs":0,
            "feasibility_note":"Each parent cluster land envelope and absolute TAMLL floor is allocated, not duplicated; every clone's mode floors fit its annual activity; disabled modes are structurally prepared for removal; land NewCapacity is zero; CAa4 has 0.1% headroom; national crop and water markets remain available."}
    write(TARGET/"documentation/vis2_preflight.json",report); print(json.dumps({"status":report["status"],"check_count":len(checks),"failures":failures},indent=2))
    if failures: raise RuntimeError(failures)


def datafile():
    v15.Config.DATA_STORAGE=STORAGE
    return v15.DataFile(TARGET.name)


def generate() -> None:
    if read(TARGET/"documentation/vis2_preflight.json")["status"]!="passed": raise RuntimeError("preflight not passed")
    run=TARGET/"res"/RUN
    if run.exists(): raise FileExistsError(run)
    df=datafile(); scenarios=[{"ScenarioId":r["ScenarioId"],"Scenario":r["Scenario"],"Desc":r.get("Desc",""),"Active":r["Scenario"]=="BASE"} for r in df.genData["osy-scenarios"]]
    created=df.createCaseRun(RUN,{"Case":RUN,"CaseId":"CS_PHL_VIS2_AGRICULTURE_SPATIAL_BASE","Desc":"Philippines vIS2 agriculture spatial BASE","Runtime":str(date.today()),"Scenarios":scenarios})
    if created.get("status_code")!="success": raise RuntimeError(created)
    started=time.monotonic(); df.generateDatafile(RUN); df.preprocessData(run/"data.txt",run/"data_processed.txt")
    glpsol=v15.Osemosys._find_solver_binary(df.glpkFolder.resolve(),"glpsol",recursive=False)
    checked=subprocess.run([str(glpsol),"--check","-m",str(MODEL),"-d",str(run/"data_processed.txt"),"--wlp",str(run/"lp.lp")],cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,capture_output=True,text=True,timeout=300)
    log=checked.stdout+"\n"+checked.stderr; (run/"glpsol_check.log").write_text(log,encoding="utf-8")
    matrix=v15._v14.matrix_metrics(log); text=(run/"data_processed.txt").read_text(encoding="utf-8")
    land_names={x["Tech"] for x in df.genData["osy-tech"] if re.fullmatch(r"LNDAGRPHLC\d{2}_(LUZ|VIS|MIN|OFF)",x["Tech"])}
    semantic=all(name in text for name in land_names) and len(land_names)==29 and all(f"{IRRIGATION}_{n}" in text for n in NODES)
    generated_modes={}
    for name in land_names:
        match=re.search(rf"^set MODEperTECHNOLOGY\[{re.escape(name)}\]:=\s*(.*?)\s*;$",text,re.M)
        generated_modes[name]=set(map(int,match.group(1).split())) if match else set()
    modes_tight=all(modes==set(ACTIVE_LAND_MODES) for modes in generated_modes.values())
    zero_new_capacity_rows=set(); nonzero_new_capacity_rows=[]; redundant_lu1_rows=0; pending_name=None; pending_year=None
    with (run/"lp.lp").open(encoding="utf-8",errors="replace") as lp_stream:
        for line in lp_stream:
            label=re.match(r"\s*NCC1_TotalAnnualMaxNewCapacityConstraint\(RE1,(LNDAGRPHLC\d{2}_(?:LUZ|VIS|MIN|OFF)),(\d{4})\):",line)
            if label and label.group(1) in land_names:
                pending_name,pending_year=label.group(1),label.group(2)
                continue
            if pending_name is not None:
                bound=re.match(r"\s*\+ NewCapacity\(RE1,([^,]+),(\d{4})\) <= ([-+0-9.eE]+)\s*$",line)
                if bound and bound.group(1)==pending_name and bound.group(2)==pending_year:
                    if float(bound.group(3))==0:
                        zero_new_capacity_rows.add((pending_name,pending_year))
                    else:
                        nonzero_new_capacity_rows.append((pending_name,pending_year,float(bound.group(3))))
                pending_name=pending_year=None
            if "LU1_TechnologyActivityByModeUL(RE1,LNDAGRPHLC" in line and any(name in line for name in land_names):
                redundant_lu1_rows+=1
    expected_zero_rows={(name,year) for name in land_names for year in YEARS}
    new_capacity_fixed_zero=zero_new_capacity_rows==expected_zero_rows and not nonzero_new_capacity_rows
    matrix_smaller=bool(matrix) and matrix["rows"]<699907 and matrix["columns"]<1062560 and matrix["matrix_nonzeros"]<22749070
    passed=(checked.returncode==0 and "Model has been successfully generated" in log and semantic
            and modes_tight and redundant_lu1_rows==0 and new_capacity_fixed_zero and matrix_smaller)
    report={"schema":"philippines-vis2-generation-gate-v1","status":"passed" if passed else "failed","optimizer_runs":0,"active_scenarios":["BASE"],"elapsed_seconds":time.monotonic()-started,"matrix_dimensions":matrix,"semantic_node_objects":semantic,
            "generated_land_mode_sets_exact":modes_tight,"expected_active_land_modes":list(ACTIVE_LAND_MODES),
            "redundant_land_LU1_rows":redundant_lu1_rows,"land_new_capacity_fixed_zero_in_lp":new_capacity_fixed_zero,
            "land_new_capacity_zero_row_count":len(zero_new_capacity_rows),"land_new_capacity_expected_row_count":len(expected_zero_rows),
            "land_new_capacity_nonzero_rows":nonzero_new_capacity_rows,"matrix_smaller_than_rejected_r2":matrix_smaller}
    write(run/"generation_matrix_report.json",report); print(json.dumps(report,indent=2))
    if report["status"]!="passed": raise RuntimeError("generation gate failed")


def cbc_diagnostics(log: str) -> dict:
    lines=log.splitlines()
    declarations=[i+1 for i,line in enumerate(lines) if "Primal infeasible - objective value" in line]
    continuation_after=False
    if declarations:
        first=declarations[0]
        continuation_after=any(
            re.match(r"\s*\d+\s+Obj\s",line) or "resolve after postsolve" in line
            for line in lines[first:]
        )
    iterations=[]
    for line in lines:
        match=re.match(r"\s*(\d+)\s+Obj\s+([-+0-9.eE]+)(?:\s+Primal inf\s+([-+0-9.eE]+)\s+\((\d+)\))?",line)
        if match:
            iterations.append({"iteration":int(match.group(1)),"objective":float(match.group(2)),
                               "primal_infeasibility":float(match.group(3)) if match.group(3) else None,
                               "violated_rows":int(match.group(4)) if match.group(4) else None})
    return {"early_primal_infeasibility_declared":bool(declarations),
            "primal_infeasibility_declaration_lines":declarations,
            "cbc_continued_after_infeasibility_declaration":continuation_after,
            "last_iteration_record":iterations[-1] if iterations else None}


def solve() -> None:
    run=TARGET/"res"/RUN; gate=read(run/"generation_matrix_report.json")
    if gate["status"]!="passed" or gate["optimizer_runs"]!=0: raise RuntimeError("unclean gate")
    df=datafile(); cbc=v15.Osemosys._find_solver_binary(df.cbcFolder.resolve(),"cbc",recursive=False)
    started=time.monotonic(); log_path=run/"cbc.log"; timed_out=False
    with log_path.open("w",encoding="utf-8",buffering=1) as log_stream:
        process=subprocess.Popen(
            [str(cbc),str(run/"lp.lp"),"solve","-printing","all","-solu",str(run/"results.txt")],
            cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            returncode=process.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out=True; process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            returncode=process.returncode
    elapsed=time.monotonic()-started; log=log_path.read_text(encoding="utf-8")
    diagnostics=cbc_diagnostics(log)
    if timed_out:
        report={"schema":"philippines-vis2-base-validation-v1","status":"timed_out","optimizer_runs":1,"timeout_seconds":TIMEOUT,"solve_seconds":elapsed,"cbc_log_live":True,"promotion_attempted":False,
                "stop_point":"500-second BASE deadline reached; CBC terminated; no policy scenario, seal, or promotion run",**diagnostics}; write(run/"optimization_record.json",report); write(TARGET/"documentation/vis2_base_validation.json",report)
        with (TARGET/"documentation/MODEL_FIXES_AGRICULTURE_SPATIAL_VIS2_2026-09-01.md").open("a",encoding="utf-8") as stream:
            stream.write(f"\n## BASE validation\n\nCBC timed out and was terminated at {elapsed:.3f} seconds under the {TIMEOUT}-second contract. Early primal-infeasibility declaration: {diagnostics['early_primal_infeasibility_declared']}; CBC continued afterward: {diagnostics['cbc_continued_after_infeasibility_declaration']}. No policy scenario, seal, or promotion was run.\n")
        print(json.dumps(report,indent=2)); return
    if returncode!=0 or not (run/"results.txt").is_file(): raise RuntimeError(log[-10000:])
    status=(run/"results.txt").read_text(encoding="utf-8").splitlines()[0]; match=re.search(r"objective value\s+([-+0-9.eE]+)",status); objective=float(match.group(1)) if match else None
    df.generateCSVfromCBC(run/"data.txt",run/"results.txt",run)
    base=read(SOURCE/"res/BASE_VIS15_WATER_BOUNDARY/optimization_record.json")
    report={"schema":"philippines-vis2-base-validation-v1","status":status,"optimizer_runs":1,"timeout_seconds":TIMEOUT,"solve_seconds":elapsed,"objective":objective,"vIS15_objective":base["objective"],"objective_change":objective-base["objective"],"objective_change_percent":100*(objective/base["objective"]-1),"vIS15_solve_seconds":base["solve_seconds"],"runtime_ratio":elapsed/base["solve_seconds"],"promotion_attempted":False,"stop_point":"BASE finished; no policy scenario, seal, or promotion run",**diagnostics}
    write(run/"optimization_record.json",report); write(TARGET/"documentation/vis2_base_validation.json",report)
    with (TARGET/"documentation/MODEL_FIXES_AGRICULTURE_SPATIAL_VIS2_2026-09-01.md").open("a",encoding="utf-8") as stream: stream.write(f"\n## BASE validation\n\nCBC status: `{status}`. Runtime: {elapsed:.3f} seconds under {TIMEOUT} seconds. Objective: {objective:.8f}, {report['objective_change_percent']:.6f}% versus vIS1.5. Early primal-infeasibility declaration: {diagnostics['early_primal_infeasibility_declared']}; CBC continued afterward: {diagnostics['cbc_continued_after_infeasibility_declaration']}. No policy scenario, seal, or promotion was run.\n")
    print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("phase",choices=("build","preflight","generate","solve")); args=parser.parse_args()
    {"build":build,"preflight":preflight,"generate":generate,"solve":solve}[args.phase]()


if __name__=="__main__": main()
