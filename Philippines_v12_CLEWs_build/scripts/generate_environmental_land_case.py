#!/usr/bin/env python3
"""Generate a Philippines v12 case with exact in-model land accounting.

Water accounting remains reporting-only because its connected technologies
have mode-dependent water coefficients.  This generator treats the land
domain independently and creates a derived case containing:

* seven parallel land-stock commodities;
* one eight-mode ``ENV_LAND`` terminal technology; and
* one exact aggregate land-balance equality.

The source case is never edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12"
DEFAULT_TARGET = (
    REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12_ENV_LAND"
)
EXPECTED_SOURCE_CASE = "Philippines_v12"
TARGET_CASE_NAME = "Philippines_v12_ENV_LAND"
BASE_SCENARIO = "SC_0"
LAND_UNIT = "10<sup>3</sup>km<sup>2</sup>"
LAND_COMMODITY = "PHL_LND"
LAND_SUPPLY_TECH = "MINLNDTOT"
ENV_TECH_ID = "TEC_envland_v12"
ENV_TECH_NAME = "ENV_LAND"
ENV_GROUP_ID = "TG_ENVIRONMENT"
ENV_CONSTRAINT_ID = "CO_envland_v12"
ENV_CONSTRAINT_NAME = "BAL_ENV_LAND"

SELECTED_VIEW_FILES = ("resData.json", "viewDefinitions.json")

DERIVED_README = """# Philippines v12 environmental-land case

This is a derived MUIO case generated from `Philippines_v12`. It adds exact
in-model land accounting through the eight-mode `ENV_LAND` terminal and
`BAL_ENV_LAND` equality constraint. The source case remains unchanged.

Water accounting remains reporting-only because the installed
technology-level user-defined constraint cannot reproduce the source model's
mode-dependent water coefficients exactly.

- Accounting guide:
  `../../../Philippines_v12_CLEWs_build/documentation/ENVIRONMENTAL_ACCOUNTING.md`
- Generator:
  `../../../Philippines_v12_CLEWs_build/scripts/generate_environmental_land_case.py`
- Validator:
  `../../../Philippines_v12_CLEWs_build/scripts/validate_environmental_land_case.py`
- Current evidence:
  `../../../Philippines_v12_CLEWs_build/diagnostics/environmental_accounting/2026-07-25_env_land_final/`
- Local documentation index: `documentation/README.md`

Do not edit generated `data.txt`, solver output or result CSV files by hand.
Regenerate this case from the source JSON with the documented generator.
"""

DERIVED_DOCUMENTATION_README = """# Environmental-land case documentation

The canonical current documentation is kept in the v12 build package:

- `../../../../Philippines_v12_CLEWs_build/documentation/ENVIRONMENTAL_ACCOUNTING.md`
- `../../../../Philippines_v12_CLEWs_build/documentation/CURRENT_MODEL.md`
- `../../../../Philippines_v12_CLEWs_build/data_sources/`

This runtime case contains `ENV_LAND` as an eight-mode MUIO technology:

1. forest
2. grassland
3. other land
4. barren or savannah
5. built-up land
6. inland water bodies
7. cropland
8. unallocated modeled land

`ENV_WATER` is intentionally absent. Use the reporting workflow documented in
the canonical environmental-accounting guide.
"""

LAND_CATEGORIES = (
    {
        "mode": 1,
        "name": "forest",
        "commodity_id": "COM_env_lfor_v12",
        "commodity": "ENV_LND_FOREST",
        "description": "Parallel area stock for model-defined forest land.",
        "technologies": ("LNDFORTOT",),
    },
    {
        "mode": 2,
        "name": "grassland",
        "commodity_id": "COM_env_lgrs_v12",
        "commodity": "ENV_LND_GRASSLAND",
        "description": "Parallel area stock for model-defined grassland.",
        "technologies": ("LNDGRSTOT",),
    },
    {
        "mode": 3,
        "name": "other_land",
        "commodity_id": "COM_env_loth_v12",
        "commodity": "ENV_LND_OTHER",
        "description": "Parallel area stock for model-defined other land.",
        "technologies": ("LNDOTHTOT",),
    },
    {
        "mode": 4,
        "name": "barren_or_savannah",
        "commodity_id": "COM_env_lbar_v12",
        "commodity": "ENV_LND_BARREN",
        "description": "Parallel area stock for model-defined barren land.",
        "technologies": ("LNDBARTOT",),
    },
    {
        "mode": 5,
        "name": "built_up_land",
        "commodity_id": "COM_env_lblt_v12",
        "commodity": "ENV_LND_BUILT",
        "description": "Parallel area stock for model-defined built-up land.",
        "technologies": ("LNDBLTTOT",),
    },
    {
        "mode": 6,
        "name": "inland_water_bodies",
        "commodity_id": "COM_env_lwat_v12",
        "commodity": "ENV_LND_WATER",
        "description": "Parallel area stock for modeled inland water bodies.",
        "technologies": ("LNDWATTOT",),
    },
    {
        "mode": 7,
        "name": "cropland",
        "commodity_id": "COM_env_lcrp_v12",
        "commodity": "ENV_LND_CROPLAND",
        "description": "Parallel area stock for the 24 modeled crop-land options.",
        "technologies": (
            "LNDRCPHITOT",
            "LNDRCPHRTOT",
            "LNDRCPLITOT",
            "LNDRCPLRTOT",
            "LNDCONHITOT",
            "LNDCONHRTOT",
            "LNDCONLITOT",
            "LNDCONLRTOT",
            "LNDMZEHITOT",
            "LNDMZEHRTOT",
            "LNDMZELITOT",
            "LNDMZELRTOT",
            "LNDTOMHITOT",
            "LNDTOMHRTOT",
            "LNDTOMLITOT",
            "LNDTOMLRTOT",
            "LNDSGCHITOT",
            "LNDSGCHRTOT",
            "LNDSGCLITOT",
            "LNDSGCLRTOT",
            "LNDOTHHITOT",
            "LNDOTHHRTOT",
            "LNDOTHLITOT",
            "LNDOTHLRTOT",
        ),
    },
)


class GenerationError(RuntimeError):
    """Raised when the source cannot support exact land accounting."""


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=4)
        handle.write("\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_files(model: Path) -> list[Path]:
    files = sorted(model.glob("*.json"))
    files.extend(
        model / "view" / filename
        for filename in SELECTED_VIEW_FILES
        if (model / "view" / filename).is_file()
    )
    return files


def manifest(model: Path) -> dict[str, str]:
    return {
        path.relative_to(model).as_posix(): sha256(path)
        for path in selected_files(model)
    }


def manifest_digest(values: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(values.items()):
        digest.update(f"{name}\0{value}\n".encode())
    return digest.hexdigest()


def resolve_paths(source: Path, target: Path) -> tuple[Path, Path]:
    source = source.resolve()
    target = target.resolve(strict=False)
    if not source.is_dir():
        raise GenerationError(f"Source case does not exist: {source}")
    if source.is_symlink() or (target.exists() and target.is_symlink()):
        raise GenerationError("Source and target case paths must not be symlinks")
    if source == target:
        raise GenerationError("Source and target case paths must differ")
    if source in target.parents or target in source.parents:
        raise GenerationError("Source and target must not be ancestor/descendant paths")
    if target.parent != source.parent:
        raise GenerationError(
            "The derived case must be a sibling of the source under DataStorage"
        )
    return source, target


def year_row(
    years: Iterable[str],
    base_value: Any,
    scenario: str,
    **dimensions: Any,
) -> dict[str, Any]:
    row = dict(dimensions)
    value = base_value if scenario == BASE_SCENARIO else None
    row.update({year: value for year in years})
    return row


def all_year_values(row: dict[str, Any], years: Iterable[str]) -> list[Any]:
    return [row[year] for year in years]


def effective_nonzero_modes(
    ratios: dict[str, Any],
    tech_id: str,
    years: list[str],
) -> set[int]:
    modes: set[int] = set()
    for parameter in ("IAR", "OAR"):
        for row in ratios[parameter][BASE_SCENARIO]:
            if row["TechId"] != tech_id:
                continue
            if any(float(row[year] or 0) != 0 for year in years):
                modes.add(int(row["MoId"]))
    return modes


def nonzero_land_graph(
    gen_data: dict[str, Any],
    ratios: dict[str, Any],
) -> dict[str, Any]:
    years = list(gen_data["osy-years"])
    tech_names = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    land_id = next(
        row["CommId"]
        for row in gen_data["osy-comm"]
        if row["Comm"] == LAND_COMMODITY
    )
    graph: dict[str, list[dict[str, Any]]] = {"producers": [], "consumers": []}
    for parameter, key in (("OAR", "producers"), ("IAR", "consumers")):
        for row in ratios[parameter][BASE_SCENARIO]:
            if row["CommId"] != land_id:
                continue
            values = [float(value or 0) for value in all_year_values(row, years)]
            if any(value != 0 for value in values):
                graph[key].append(
                    {
                        "technology": tech_names[row["TechId"]],
                        "technology_id": row["TechId"],
                        "mode": int(row["MoId"]),
                        "minimum": min(values),
                        "maximum": max(values),
                    }
                )
    return {"commodity_id": land_id, **graph}


def assert_inherited_rows(
    data: dict[str, Any],
    dimensions: dict[str, Any],
    years: list[str],
    label: str,
) -> None:
    for scenario, rows in data.items():
        matches = [
            row
            for row in rows
            if all(row.get(key) == value for key, value in dimensions.items())
        ]
        if not matches:
            raise GenerationError(f"Missing {label} row in scenario {scenario}")
        if scenario != BASE_SCENARIO:
            for row in matches:
                if any(row[year] is not None for year in years):
                    raise GenerationError(
                        f"{label} has a non-base scenario override in {scenario}"
                    )


def audit_source(source: Path) -> dict[str, Any]:
    gen_data = read_json(source / "genData.json")
    if gen_data.get("osy-casename") != EXPECTED_SOURCE_CASE:
        raise GenerationError(
            f"Expected source {EXPECTED_SOURCE_CASE}, found "
            f"{gen_data.get('osy-casename')!r}"
        )
    years = list(gen_data["osy-years"])
    scenarios = [row["ScenarioId"] for row in gen_data["osy-scenarios"]]
    modes = list(range(1, int(gen_data["osy-mo"]) + 1))
    tech_by_name = {row["Tech"]: row for row in gen_data["osy-tech"]}
    tech_by_id = {row["TechId"]: row for row in gen_data["osy-tech"]}
    comm_by_name = {row["Comm"]: row for row in gen_data["osy-comm"]}
    ratios = read_json(source / "RYTCM.json")
    graph = nonzero_land_graph(gen_data, ratios)

    expected_consumers = {
        name
        for category in LAND_CATEGORIES
        for name in category["technologies"]
    }
    actual_producers = {row["technology"] for row in graph["producers"]}
    actual_consumers = {row["technology"] for row in graph["consumers"]}
    if actual_producers != {LAND_SUPPLY_TECH}:
        raise GenerationError(
            f"Unexpected {LAND_COMMODITY} producers: {sorted(actual_producers)}"
        )
    if actual_consumers != expected_consumers:
        raise GenerationError(
            "Unexpected land-consumer graph; "
            f"missing={sorted(expected_consumers - actual_consumers)}, "
            f"extra={sorted(actual_consumers - expected_consumers)}"
        )
    for side in ("producers", "consumers"):
        for row in graph[side]:
            if row["mode"] != 1 or row["minimum"] != 1 or row["maximum"] != 1:
                raise GenerationError(
                    f"{row['technology']} has an unsafe land coefficient: {row}"
                )
            active_modes = effective_nonzero_modes(
                ratios, row["technology_id"], years
            )
            if active_modes != {1}:
                raise GenerationError(
                    f"{row['technology']} has active modes {sorted(active_modes)}; "
                    "the parallel stock proof expected mode 1 only"
                )

    if LAND_COMMODITY not in comm_by_name:
        raise GenerationError(f"Missing commodity {LAND_COMMODITY}")
    if comm_by_name[LAND_COMMODITY]["UnitId"] != LAND_UNIT:
        raise GenerationError(
            f"Unexpected {LAND_COMMODITY} unit "
            f"{comm_by_name[LAND_COMMODITY]['UnitId']!r}"
        )

    existing_names = {
        *(row["Tech"] for row in gen_data["osy-tech"]),
        *(row["Comm"] for row in gen_data["osy-comm"]),
        *(row["Con"] for row in gen_data["osy-constraints"]),
        *(row["TechGroup"] for row in gen_data["osy-techGroups"]),
    }
    new_names = {
        ENV_TECH_NAME,
        ENV_CONSTRAINT_NAME,
        "ENVIRONMENT",
        *(category["commodity"] for category in LAND_CATEGORIES),
    }
    collisions = sorted(existing_names & new_names)
    if collisions:
        raise GenerationError(f"Accounting-name collisions: {collisions}")

    existing_ids = {
        *(row["TechId"] for row in gen_data["osy-tech"]),
        *(row["CommId"] for row in gen_data["osy-comm"]),
        *(row["ConId"] for row in gen_data["osy-constraints"]),
        *(row["TechGroupId"] for row in gen_data["osy-techGroups"]),
    }
    new_ids = {
        ENV_TECH_ID,
        ENV_CONSTRAINT_ID,
        ENV_GROUP_ID,
        *(category["commodity_id"] for category in LAND_CATEGORIES),
    }
    collisions = sorted(existing_ids & new_ids)
    if collisions:
        raise GenerationError(f"Accounting-ID collisions: {collisions}")
    if len(new_ids) != 10:
        raise GenerationError("New accounting IDs are not unique")

    ryc = read_json(source / "RYC.json")
    land_id = graph["commodity_id"]
    for parameter in ("SAD", "AAD"):
        assert_inherited_rows(
            ryc[parameter],
            {"CommId": land_id},
            years,
            f"{parameter}/{LAND_COMMODITY}",
        )
        base = next(
            row
            for row in ryc[parameter][BASE_SCENARIO]
            if row["CommId"] == land_id
        )
        if any(float(base[year] or 0) != 0 for year in years):
            raise GenerationError(f"{parameter}/{LAND_COMMODITY} is nonzero")

    for tech in gen_data["osy-tech"]:
        if land_id in tech.get("INCR", []) or land_id in tech.get("ITCR", []):
            raise GenerationError(
                f"{LAND_COMMODITY} has a capacity-input term on {tech['Tech']}"
            )

    for parameter in ("IAR", "OAR"):
        for row in ratios[parameter][BASE_SCENARIO]:
            if row["CommId"] == land_id:
                assert_inherited_rows(
                    ratios[parameter],
                    {
                        "TechId": row["TechId"],
                        "CommId": land_id,
                        "MoId": row["MoId"],
                    },
                    years,
                    f"{parameter}/{tech_by_id[row['TechId']]['Tech']}/{LAND_COMMODITY}",
                )

    land_supply_id = tech_by_name[LAND_SUPPLY_TECH]["TechId"]
    ryt = read_json(source / "RYT.json")
    rt = read_json(source / "RT.json")
    annual_supply_upper = max(
        float(row[year])
        for row in ryt["TAU"][BASE_SCENARIO]
        if row["TechId"] == land_supply_id
        for year in years
    )
    model_period_supply_upper = float(
        rt["TMPAU"][BASE_SCENARIO][0][land_supply_id]
    )
    if annual_supply_upper <= 0 or model_period_supply_upper <= 0:
        raise GenerationError("Land-supply activity bounds are not positive")

    return {
        "gen_data": gen_data,
        "years": years,
        "scenarios": scenarios,
        "modes": modes,
        "timeslice_ids": [row["TsId"] for row in gen_data["osy-ts"]],
        "tech_by_name": tech_by_name,
        "land_id": land_id,
        "land_supply_id": land_supply_id,
        "graph": graph,
        "annual_supply_upper": annual_supply_upper,
        "model_period_supply_upper": model_period_supply_upper,
        "category_technology_count": len(expected_consumers),
    }


def append_technology_parameters(
    data: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    years = audit["years"]
    scenarios = audit["scenarios"]
    modes = audit["modes"]
    annual_upper = audit["annual_supply_upper"]
    model_period_upper = audit["model_period_supply_upper"]

    rt_values = {
        "TMPAU": model_period_upper,
        "TMPAL": 0,
        "OL": 1,
        "CAU": 1,
        "DRI": 0.05,
    }
    rt = data["RT.json"]
    for parameter, value in rt_values.items():
        for scenario in scenarios:
            rt[parameter][scenario][0][ENV_TECH_ID] = (
                value if scenario == BASE_SCENARIO else None
            )

    ryt_values = {
        "COTU": 0,
        "TAU": annual_upper,
        "TAL": 0,
        "TAMinCI": 0,
        "TAMinC": 0,
        "TAMaxCI": 0,
        "TAMaxC": annual_upper,
        "RC": annual_upper,
        "FC": 0,
        "CC": 0,
        "AF": 1,
    }
    ryt = data["RYT.json"]
    for parameter, value in ryt_values.items():
        for scenario in scenarios:
            ryt[parameter][scenario].append(
                year_row(
                    years,
                    value,
                    scenario,
                    TechId=ENV_TECH_ID,
                )
            )

    rytm_values = {
        "TAIML": 0,
        "TADML": 0,
        "TAMUL": annual_upper,
        "TAMLL": 0,
        "VC": 0,
    }
    rytm = data["RYTM.json"]
    for parameter, value in rytm_values.items():
        for scenario in scenarios:
            for mode in modes:
                rytm[parameter][scenario].append(
                    year_row(
                        years,
                        value,
                        scenario,
                        TechId=ENV_TECH_ID,
                        MoId=mode,
                    )
                )

    rytts = data["RYTTs.json"]
    for scenario in scenarios:
        for timeslice_id in audit["timeslice_ids"]:
            rytts["CF"][scenario].append(
                year_row(
                    years,
                    1,
                    scenario,
                    TechId=ENV_TECH_ID,
                    TsId=timeslice_id,
                )
            )


def append_commodity_parameters(
    data: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    years = audit["years"]
    scenarios = audit["scenarios"]
    timeslice_ids = audit["timeslice_ids"]
    commodity_ids = [category["commodity_id"] for category in LAND_CATEGORIES]
    for parameter in ("SAD", "AAD"):
        for scenario in scenarios:
            for commodity_id in commodity_ids:
                data["RYC.json"][parameter][scenario].append(
                    year_row(
                        years,
                        0,
                        scenario,
                        CommId=commodity_id,
                    )
                )
    for scenario in scenarios:
        for commodity_id in commodity_ids:
            for timeslice_id in timeslice_ids:
                data["RYCTs.json"]["SDP"][scenario].append(
                    year_row(
                        years,
                        0,
                        scenario,
                        CommId=commodity_id,
                        TsId=timeslice_id,
                    )
                )


def append_activity_ratios(
    data: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    years = audit["years"]
    scenarios = audit["scenarios"]
    modes = audit["modes"]
    tech_by_name = audit["tech_by_name"]
    ratios = data["RYTCM.json"]

    for category in LAND_CATEGORIES:
        commodity_id = category["commodity_id"]
        for technology in category["technologies"]:
            technology_id = tech_by_name[technology]["TechId"]
            for scenario in scenarios:
                for mode in modes:
                    ratios["OAR"][scenario].append(
                        year_row(
                            years,
                            1 if mode == 1 else 0,
                            scenario,
                            TechId=technology_id,
                            CommId=commodity_id,
                            MoId=mode,
                        )
                    )

    terminal_inputs = [
        *(category["commodity_id"] for category in LAND_CATEGORIES),
        audit["land_id"],
    ]
    for input_mode, commodity_id in enumerate(terminal_inputs, start=1):
        for scenario in scenarios:
            for mode in modes:
                ratios["IAR"][scenario].append(
                    year_row(
                        years,
                        1 if mode == input_mode else 0,
                        scenario,
                        TechId=ENV_TECH_ID,
                        CommId=commodity_id,
                        MoId=mode,
                    )
                )


def append_constraint_parameters(
    data: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    years = audit["years"]
    scenarios = audit["scenarios"]
    members = (audit["land_supply_id"], ENV_TECH_ID)

    for scenario in scenarios:
        data["RYCn.json"]["UCC"][scenario].append(
            year_row(
                years,
                0,
                scenario,
                ConId=ENV_CONSTRAINT_ID,
            )
        )
    for parameter in ("CAM", "CNCM", "CCM"):
        for scenario in scenarios:
            for technology_id in members:
                value = 0
                if parameter == "CAM":
                    value = 1 if technology_id == audit["land_supply_id"] else -1
                data["RYTCn.json"][parameter][scenario].append(
                    year_row(
                        years,
                        value,
                        scenario,
                        TechId=technology_id,
                        ConId=ENV_CONSTRAINT_ID,
                    )
                )


def build_generated_data(
    source: Path,
    audit: dict[str, Any],
) -> dict[str, Any]:
    data = {
        path.name: deepcopy(read_json(path))
        for path in sorted(source.glob("*.json"))
    }
    gen_data = data["genData.json"]
    gen_data["osy-casename"] = TARGET_CASE_NAME
    gen_data["osy-desc"] = (
        f"{gen_data.get('osy-desc', '').rstrip()} "
        "Derived case with exact in-model ENV_LAND accounting; "
        "water accounting remains reporting-only."
    ).strip()
    gen_data["osy-date"] = date.today().isoformat()

    gen_data["osy-techGroups"].append(
        {
            "TechGroup": "ENVIRONMENT",
            "TechGroupId": ENV_GROUP_ID,
            "Desc": "Environmental accounting terminal technologies.",
        }
    )
    for category in LAND_CATEGORIES:
        gen_data["osy-comm"].append(
            {
                "CommId": category["commodity_id"],
                "Comm": category["commodity"],
                "Desc": category["description"],
                "UnitId": LAND_UNIT,
            }
        )

    for category in LAND_CATEGORIES:
        commodity_id = category["commodity_id"]
        for technology_name in category["technologies"]:
            technology = next(
                row
                for row in gen_data["osy-tech"]
                if row["Tech"] == technology_name
            )
            technology["OAR"].append(commodity_id)

    terminal_inputs = [
        *(category["commodity_id"] for category in LAND_CATEGORIES),
        audit["land_id"],
    ]
    mode_dictionary = "; ".join(
        [
            *(f"{category['mode']}={category['name']}" for category in LAND_CATEGORIES),
            "8=unallocated_modeled_land",
        ]
    )
    gen_data["osy-tech"].append(
        {
            "TechId": ENV_TECH_ID,
            "Tech": ENV_TECH_NAME,
            "Desc": (
                "Exact multimode land-accounting terminal. "
                f"Mode dictionary: {mode_dictionary}. "
                "Every mode consumes one area-stock commodity at IAR 1."
            ),
            "CapUnitId": LAND_UNIT,
            "ActUnitId": LAND_UNIT,
            "TG": [ENV_GROUP_ID],
            "IAR": terminal_inputs,
            "OAR": [],
            "INCR": [],
            "ITCR": [],
            "EAR": [],
        }
    )
    gen_data["osy-constraints"].append(
        {
            "ConId": ENV_CONSTRAINT_ID,
            "Con": ENV_CONSTRAINT_NAME,
            "Desc": (
                "Exact aggregate land closure: MINLNDTOT annual activity equals "
                "total ENV_LAND annual activity."
            ),
            "Tag": 1,
            "CM": [audit["land_supply_id"], ENV_TECH_ID],
        }
    )

    append_technology_parameters(data, audit)
    append_commodity_parameters(data, audit)
    append_activity_ratios(data, audit)
    append_constraint_parameters(data, audit)
    return data


def validate_generated_data(
    source: Path,
    generated: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    source_gen = audit["gen_data"]
    gen_data = generated["genData.json"]
    expected_counts = {
        "technologies": len(source_gen["osy-tech"]) + 1,
        "commodities": len(source_gen["osy-comm"]) + len(LAND_CATEGORIES),
        "constraints": len(source_gen["osy-constraints"]) + 1,
        "technology_groups": len(source_gen["osy-techGroups"]) + 1,
    }
    actual_counts = {
        "technologies": len(gen_data["osy-tech"]),
        "commodities": len(gen_data["osy-comm"]),
        "constraints": len(gen_data["osy-constraints"]),
        "technology_groups": len(gen_data["osy-techGroups"]),
    }
    if actual_counts != expected_counts:
        raise GenerationError(
            f"Generated counts differ: expected={expected_counts}, "
            f"actual={actual_counts}"
        )
    if any(row["Tech"] == "ENV_WATER" for row in gen_data["osy-tech"]):
        raise GenerationError("Unsafe ENV_WATER terminal was added")
    if sum(row["Tech"] == ENV_TECH_NAME for row in gen_data["osy-tech"]) != 1:
        raise GenerationError("Expected exactly one ENV_LAND technology")

    source_files = {path.name for path in source.glob("*.json")}
    changed_files = {
        "genData.json",
        "RT.json",
        "RYT.json",
        "RYTM.json",
        "RYTTs.json",
        "RYC.json",
        "RYCTs.json",
        "RYTCM.json",
        "RYCn.json",
        "RYTCn.json",
    }
    for filename in source_files - changed_files:
        if generated[filename] != read_json(source / filename):
            raise GenerationError(f"Unexpected change in {filename}")

    for filename in changed_files - {"genData.json", "RT.json"}:
        source_data = read_json(source / filename)
        candidate_data = generated[filename]
        for parameter, scenarios in source_data.items():
            for scenario, rows in scenarios.items():
                if candidate_data[parameter][scenario][: len(rows)] != rows:
                    raise GenerationError(
                        f"Original rows changed in {filename}/{parameter}/{scenario}"
                    )

    source_rt = read_json(source / "RT.json")
    generated_rt = generated["RT.json"]
    for parameter, scenarios in source_rt.items():
        for scenario, rows in scenarios.items():
            if len(rows) != 1 or len(generated_rt[parameter][scenario]) != 1:
                raise GenerationError(f"Unexpected RT shape for {parameter}/{scenario}")
            candidate = dict(generated_rt[parameter][scenario][0])
            candidate.pop(ENV_TECH_ID, None)
            if candidate != rows[0]:
                raise GenerationError(
                    f"Original RT values changed in {parameter}/{scenario}"
                )

    source_tech_by_id = {
        row["TechId"]: row for row in source_gen["osy-tech"]
    }
    generated_tech_by_id = {
        row["TechId"]: row for row in gen_data["osy-tech"]
    }
    additions_by_tech = {
        audit["tech_by_name"][technology]["TechId"]: category["commodity_id"]
        for category in LAND_CATEGORIES
        for technology in category["technologies"]
    }
    for technology_id, source_technology in source_tech_by_id.items():
        candidate = deepcopy(generated_tech_by_id[technology_id])
        expected_addition = additions_by_tech.get(technology_id)
        if expected_addition is not None:
            if candidate["OAR"][-1] != expected_addition:
                raise GenerationError(
                    f"Missing stock output on {source_technology['Tech']}"
                )
            candidate["OAR"] = candidate["OAR"][:-1]
        if candidate != source_technology:
            raise GenerationError(
                f"Unexpected metadata change on {source_technology['Tech']}"
            )

    ratios = generated["RYTCM.json"]
    years = audit["years"]
    domain_ids = {
        audit["land_id"],
        *(category["commodity_id"] for category in LAND_CATEGORIES),
    }
    tech_names = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    active_modes = {
        tech_id: effective_nonzero_modes(ratios, tech_id, years)
        for tech_id in tech_names
    }
    net: dict[tuple[str, int, str], float] = {}
    for technology_id, modes in active_modes.items():
        for mode in modes:
            for year in years:
                value = 0.0
                for parameter, sign in (("OAR", 1.0), ("IAR", -1.0)):
                    for row in ratios[parameter][BASE_SCENARIO]:
                        if (
                            row["TechId"] == technology_id
                            and row["CommId"] in domain_ids
                            and int(row["MoId"]) == mode
                        ):
                            value += sign * float(row[year] or 0)
                net[(technology_id, mode, year)] = value

    unsafe: list[dict[str, Any]] = []
    for technology_id, modes in active_modes.items():
        values = {
            net[(technology_id, mode, year)]
            for mode in modes
            for year in years
        }
        connected = any(value != 0 for value in values) or technology_id in {
            audit["land_supply_id"],
            ENV_TECH_ID,
        }
        if connected and len(values) != 1:
            unsafe.append(
                {
                    "technology": tech_names[technology_id],
                    "values": sorted(values),
                }
            )
    if unsafe:
        raise GenerationError(f"Mode-dependent generated land coefficients: {unsafe}")

    terminal_modes = active_modes[ENV_TECH_ID]
    if terminal_modes != set(range(1, 9)):
        raise GenerationError(
            f"ENV_LAND modes are {sorted(terminal_modes)}, expected 1-8"
        )
    if {
        net[(ENV_TECH_ID, mode, year)]
        for mode in terminal_modes
        for year in years
    } != {-1.0}:
        raise GenerationError("ENV_LAND does not have net coefficient -1")
    if {
        net[(audit["land_supply_id"], 1, year)]
        for year in years
    } != {1.0}:
        raise GenerationError("MINLNDTOT does not have net coefficient +1")

    return {
        "status": "PASS",
        "counts": actual_counts,
        "source_land_graph": audit["graph"],
        "land_domain_commodities": sorted(domain_ids),
        "terminal_modes": sorted(terminal_modes),
        "aggregate_coefficients": {
            LAND_SUPPLY_TECH: 1,
            ENV_TECH_NAME: -1,
        },
        "annual_terminal_activity_upper_bound": audit["annual_supply_upper"],
        "model_period_terminal_activity_upper_bound": audit[
            "model_period_supply_upper"
        ],
        "water_architecture": "reporting-only; ENV_WATER intentionally absent",
    }


def update_res_data(res_data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(res_data)
    for run in result.get("osy-cases", []):
        run["CaseId"] = f"{run['CaseId']}_ENVLAND"
        run["Desc"] = (
            f"{run.get('Desc', '').rstrip()} "
            "Derived run with exact in-model ENV_LAND accounting."
        ).strip()
        run["Runtime"] = date.today().isoformat()
    return result


def materialize_stage(
    source: Path,
    target: Path,
    generated: dict[str, Any],
) -> Path:
    stage = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.stage.", dir=target.parent)
    )
    try:
        for filename, data in generated.items():
            write_json(stage / filename, data)
        (stage / "view").mkdir()
        for filename in SELECTED_VIEW_FILES:
            source_file = source / "view" / filename
            if filename == "resData.json":
                write_json(
                    stage / "view" / filename,
                    update_res_data(read_json(source_file)),
                )
            else:
                shutil.copy2(source_file, stage / "view" / filename)
        (stage / "documentation").mkdir()
        (stage / "README.md").write_text(DERIVED_README, encoding="utf-8")
        (stage / "documentation" / "README.md").write_text(
            DERIVED_DOCUMENTATION_README,
            encoding="utf-8",
        )
        for run in read_json(stage / "view" / "resData.json").get(
            "osy-cases", []
        ):
            (stage / "res" / run["Case"] / "csv").mkdir(parents=True)
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def promote(stage: Path, target: Path, overwrite: bool) -> Path | None:
    backup: Path | None = None
    if target.exists():
        if not overwrite:
            raise GenerationError(
                f"Target already exists: {target}; use --overwrite explicitly"
            )
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = target.with_name(f"{target.name}.backup.{timestamp}")
        if backup.exists():
            raise GenerationError(f"Backup path already exists: {backup}")
        target.rename(backup)
    try:
        stage.rename(target)
    except Exception:
        if backup is not None and not target.exists():
            backup.rename(target)
        raise
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source, target = resolve_paths(args.source, args.target)
    source_before = manifest(source)
    audit = audit_source(source)
    generated = build_generated_data(source, audit)
    validation = validate_generated_data(source, generated, audit)
    source_after = manifest(source)
    if source_before != source_after:
        raise GenerationError("Source case changed during generation")

    result = {
        "status": "PASS",
        "dry_run": args.dry_run,
        "source": str(source),
        "target": str(target),
        "source_file_count": len(source_before),
        "source_manifest_digest": manifest_digest(source_before),
        "validation": validation,
    }
    if args.dry_run:
        print(json.dumps(result, indent=2))
        return

    stage = materialize_stage(source, target, generated)
    try:
        backup = promote(stage, target, args.overwrite)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    result["backup"] = str(backup) if backup is not None else None
    result["target_file_count"] = len(manifest(target))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
