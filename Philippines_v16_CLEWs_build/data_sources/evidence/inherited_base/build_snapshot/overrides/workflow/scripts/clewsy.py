import yaml
import pandas as pd
import numpy as np
import os
import subprocess
import shutil
from constants import ROOT_DIR
import collections
import ast


def modify_yaml(
    scenario,
    region_codes,
    timeslice,
    emissions,
):
    yaml_file =f"{ROOT_DIR}/config/clews_config/clewsy_template.yaml"
    with open(yaml_file, "r") as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
    data["Model"] = scenario
    data["otooleOutputDirectory"] = f"{ROOT_DIR}/results/{scenario}/clewsy"
    data["DataDirectoryName"] = f"{ROOT_DIR}/results/{scenario}/geoclews/summary_stats"
    data["OperationModes"] = f"{ROOT_DIR}/workflow/submodules/clewsy/optn_mds.txt"
    data["OsemosysGlobalPath"] = f"{ROOT_DIR}/results/{scenario}/osemosys_global"
    data["Years"] = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/osemosys_global/YEAR.csv").VALUE.to_list()
    data["LandRegions"] = list(region_codes.keys())
    data["LandToGridMap"] = region_codes
    data["Timeslices"] = timeslice
    data.pop("TimeSlice", None)
    acronyms = data.setdefault("Acronym_dict", {})
    for key in [key for key in acronyms if "GUY" in key]:
        del acronyms[key]
    technology_labels = {
        "BIO": "Biomass",
        "CSP": "Concentrated Solar Power",
        "ELC": "Electricity",
        "GEO": "Geothermal",
        "HYD": "Hydropower",
        "SPV": "Solar",
        "WAS": "Waste",
        "WAV": "Wave",
        "WOF": "Offshore wind",
        "WON": "Onshore wind",
    }
    fuel_labels = {
        "COA": "Coal",
        "COG": "Cogeneration",
        "GAS": "Natural Gas",
        "OIL": "Oil",
        "OTH": "Other",
        "PET": "Petroleum",
        "URN": "Nuclear",
        "REN": "Rest Renewables",
    }
    for land_region, grid_region in region_codes.items():
        acronyms[land_region] = scenario
        for code, label in technology_labels.items():
            if code == "ELC":
                acronyms[f"ELC{grid_region}01"] = (
                    f"Electricity from power plants in {scenario}"
                )
                acronyms[f"ELC{grid_region}02"] = (
                    f"Electricity from transmission in {scenario}"
                )
            else:
                acronyms[f"{code}{grid_region}"] = label
        for code, label in fuel_labels.items():
            acronyms[f"{code}{land_region}"] = label
    grid_regions = list(dict.fromkeys(region_codes.values()))
    for i in data["EndUseFuels"]:
        fuel_list = data["EndUseFuels"][i]
        for grid_region in grid_regions:
            electricity = f"ELC{grid_region}02"
            if electricity not in fuel_list:
                fuel_list.append(electricity)
        data["EndUseFuels"][i] = fuel_list
    # OSeMOSYS Global already supplies the PWRTRN technology and its
    # ELC<grid>01 -> ELC<grid>02 ratios. Adding it here would duplicate them.
    data["TransformationTechnologies"] = []
    data["Emissions"] = {i: ['Carbon dioxide emissions.', '#000000'] for i in emissions}

    crop_list = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/CROP.csv").to_dict()['FUEL'].values()
    
    data["CropYieldFactors"] = {crop: 1 for crop in crop_list}
    print(data["CropYieldFactors"])
    with open(f"{ROOT_DIR}/config/clews_config/clewsy.yaml", "w") as f:
        yaml.dump(data, f)

    return data


def crop_demand(scenario, country_full_name):
    def set_crop_code(row):
        if row["Item"] in other_crops:
            return "OTH"
        elif pd.isna(row["Code"]):
            return "OTH"
        elif row["Code"] not in modelled_crop_codes:
            return "OTH"
        else:
            return row["Code"]


    data = pd.read_csv(f"{ROOT_DIR}/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/FAOSTAT_2020.csv")
    filtered_data = data[data['Area'] == country_full_name]

    top_10_values = filtered_data.nlargest(10, 'Value')
    all_crops = top_10_values['Item'].tolist()

    other_crops = all_crops[5:]

    country_codes = pd.read_csv(
        f"{ROOT_DIR}/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Country_code.csv"
    ).set_index("Full_name")
    country_code = country_codes.loc[country_full_name, "country_code"]
    cluster_columns = pd.read_csv(
        f"{ROOT_DIR}/results/{scenario}/geoclews/summary_stats/"
        f"clustering_results_{country_code}.csv",
        nrows=0,
    ).columns
    modelled_crop_codes = {
        column.split()[0]
        for column in cluster_columns
        if "Irrigation" in column or "Rain-fed" in column
    }

    data = pd.read_csv(f"{ROOT_DIR}/data/FAOSTAT_production_2020.csv")
    filtered_data = data[data['Area'] == country_full_name]
    filtered_data = filtered_data[filtered_data['Item'].isin(all_crops)].set_index('Item')
    crop_code = pd.read_csv(
        f'{ROOT_DIR}/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Crop_code.csv').set_index('Name')
    data_classified = filtered_data.join(crop_code, how="left")[["Code", "Value"]].reset_index()
    data_classified["Code"] = data_classified.apply(set_crop_code, axis=1)
    data_summarized = data_classified.groupby(['Code']).sum('Value').to_dict()
    demand = data_summarized['Value'] = {
    k: v / 1_000_000
    for k, v in data_summarized['Value'].items()
}
    pd.DataFrame(data=demand.keys(), columns=["FUEL"]).to_csv(f"{ROOT_DIR}/results/{scenario}/CROP.csv", index=False)
    return demand

def get_growth_factors(country_full_name, start_year, end_year):
    gdp = pd.read_excel(
        f"{ROOT_DIR}/workflow/submodules/osemosys_global/resources/data/default/iamc_db_GDPppp_Countries.xlsx",
        sheet_name="data")
    pop = pd.read_excel(
        f"{ROOT_DIR}/workflow/submodules/osemosys_global/resources/data/default/iamc_db_POP_Countries.xlsx",
        sheet_name="data")
    code = pd.read_csv(
        f'{ROOT_DIR}/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Country_code.csv'
    ).set_index("Full_name").to_dict()

    country_code = code['country_code'][country_full_name]

    gdp = gdp[(gdp['Scenario'] == "SSP2") & (gdp['Region'] == country_code) & (gdp['Model'] == 'OECD Env-Growth')]
    pop = pop[(pop['Scenario'] == "SSP2") & (pop['Region'] == country_code) & (pop['Model'] == 'IIASA-WiC POP')]

    base_gdp = gdp.transpose().loc[[2010 + i for i in range(0, 95, 5)], ]
    base_gdp.rename(columns={base_gdp.columns[0]: 'GDP'}, inplace=True)

    base_pop = pop.transpose().loc[[2010 + i for i in range(0, 95, 5)], ]
    base_pop.rename(columns={base_pop.columns[0]: 'POP'}, inplace=True)

    df_gdp = pd.DataFrame(index=[2015 + i for i in range(end_year - 2015 + 1)])
    df_gdp = df_gdp.join(base_gdp, how="left")
    df = df_gdp.join(base_pop, how="left")

    result = df.astype(float).interpolate()
    result = result.loc[start_year:end_year]

    for column in result.columns:
        result[column] = result[column].apply(
            lambda x: x / result.loc[start_year, column] - 1
        )

    return result

def demand_projection(demand, country_full_name, scenario, start_year, end_year):
    result = get_growth_factors(country_full_name, start_year, end_year)

    final_df = pd.DataFrame(columns=["REGION", "FUEL", "YEAR", "VALUE"])

    gdp_factor = 0
    pop_factor = 1

    for crop in demand:
        # Crop demand increasing
        demand_data = (
            1
            + result["GDP"] * gdp_factor
            + result["POP"] * pop_factor
        ) * demand[crop]

        interim_df = pd.DataFrame({
            "YEAR": result.index,
            "VALUE": demand_data
        })

        interim_df["FUEL"] = f"CRP{crop}"
        interim_df["REGION"] = "GLOBAL"

        final_df = pd.concat([final_df, interim_df], ignore_index=True)

    accumulated_a_demand = pd.read_csv(
        f"{ROOT_DIR}/results/{scenario}/clewsy/AccumulatedAnnualDemand.csv"
    )
    accumulated_a_demand = accumulated_a_demand.loc[
        ~accumulated_a_demand["FUEL"].astype(str).str.startswith("CRP")
    ]

    final_df = pd.concat([final_df, accumulated_a_demand], ignore_index=True)

    final_df.to_csv(
        f"{ROOT_DIR}/results/{scenario}/clewsy/AccumulatedAnnualDemand.csv",
        index=False
    )

def cost_land_tech(scenario, country_full_name, start_year, end_year):
    code = pd.read_csv(
    f'{ROOT_DIR}/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Country_code.csv').set_index(
    "Full_name").to_dict()  # More info: https://www.nationsonline.org/oneworld/country_code_list.htm
    country_code = code['country_code'][country_full_name]
    tech_list = list(pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TECHNOLOGY.csv")["VALUE"])
    high_irrigation_tech = [i for i in tech_list if i.startswith("LND") and i.endswith("HITOT")]
    high_rainfed_tech = [i for i in tech_list if i.startswith("LND") and i.endswith("HRTOT")]
    low_irrigation_tech = [i for i in tech_list if i.startswith("LND") and i.endswith("LITOT")]
    low_rainfed_tech = [i for i in tech_list if i.startswith("LND") and i.endswith("LRTOT")]
    cluster_name_pr = [i for i in tech_list if i.startswith("LNDAGR")][0][:-2]
    high_irrigation = 30
    high_rainfed = 15
    low_irrigation = 20
    low_rainfed = 10
    
    capital_cost_list = [(high_irrigation, high_irrigation_tech), (high_rainfed, high_rainfed_tech),
                        (low_rainfed, low_rainfed_tech), (low_irrigation, low_irrigation_tech),]

    capital_cost_df = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/CapitalCost.csv")

    for land_type, land_tech_list  in capital_cost_list:
        for land_tech in land_tech_list:
            interim_df_capital = pd.DataFrame([{"VALUE": land_type, "REGION": "GLOBAL", "TECHNOLOGY": land_tech, "YEAR": i}
                                       for i in range(start_year, end_year+1)])
            capital_cost_df = pd.concat([capital_cost_df, interim_df_capital], ignore_index=True)
    capital_cost_df.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/CapitalCost.csv", index=False)

    opt_list = list(pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/MODE_OF_OPERATION.csv")["VALUE"])
    
    max_capacity = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalAnnualMaxCapacity.csv")
    max_capacity_activity = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityUpperLimit.csv")
    min_capacity_activity = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityLowerLimit.csv")
    land_cover_info = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/geoclews/summary_stats/{country_code}_LandCover_byCluster_summary.csv")
    cluster_lists = land_cover_info["clusters_yield"].tolist()
    land_cover_info.set_index(["clusters_yield"], inplace=True)
    # for cluster_number  in cluster_lists:
    #     cluster_name = cluster_name_pr + str(cluster_number).zfill(2)
    #     interim_df_max_capacity = pd.DataFrame([{"VALUE": land_cover_info['sqkm'][cluster_number], "REGION": "GLOBAL",
    #                                         "TECHNOLOGY": cluster_name, "YEAR": i}
    #                                for i in range(start_year, end_year+1)])
    #     max_capacity = pd.concat([max_capacity, interim_df_max_capacity], ignore_index=True)
    #     max_capacity_activity = pd.concat([max_capacity_activity, interim_df_max_capacity], ignore_index=True)
    # for tech in tech_list:
    #     interim_df_min_capacity = pd.DataFrame([{"VALUE": 0, "REGION": "GLOBAL",
    #                                         "TECHNOLOGY": tech, "YEAR": i}
    #                                for i in range(start_year, end_year+1)])
    #     min_capacity_activity = pd.concat([min_capacity_activity, interim_df_min_capacity], ignore_index=True)
    # max_capacity.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalAnnualMaxCapacity.csv", index=False)
    # # max_capacity_activity.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityUpperLimit.csv",
    # #                              index=False)
    # min_capacity_activity.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityLowerLimit.csv",
                                #  index=False)


def deduplicate_otoole_csvs(data_directory):
    """Keep the final value for each parameter index before conversion.

    Both the upstream append writer and country-specific overrides can emit a
    parameter index more than once. MathProg rejects those duplicate records,
    while the intended semantics here are that the later country-specific
    value replaces the earlier default.
    """
    for csv_path in sorted(os.scandir(data_directory), key=lambda item: item.name):
        if not csv_path.name.endswith(".csv"):
            continue
        dataframe = pd.read_csv(csv_path.path)
        if dataframe.empty:
            continue
        index_columns = [
            column for column in dataframe.columns if column != "VALUE"
        ]
        if not index_columns:
            index_columns = list(dataframe.columns)
        duplicate_rows = dataframe.duplicated(
            subset=index_columns, keep="last"
        )
        if duplicate_rows.any():
            print(
                f"Removing {int(duplicate_rows.sum())} duplicate record(s) "
                f"from {csv_path.name}; keeping the final value."
            )
            dataframe.loc[~duplicate_rows].to_csv(csv_path.path, index=False)


## TODO Make it snakemake processes
def main(
    scenario,
    region_codes,
    timeslice,
    country_full_name,
    emissions,
    start_year,
    end_year,
):
    try:
        shutil.copy(f"{ROOT_DIR}/results/{scenario}/osemosys_global/FUEL.csv",
                    f"{ROOT_DIR}/results/{scenario}/osemosys_global/COMMODITY.csv")
    except shutil.SameFileError:
        os.remove(f"{ROOT_DIR}/results/{scenario}/osemosys_global/COMMODITY.csv")
        shutil.copy(f"{ROOT_DIR}/results/{scenario}/osemosys_global/FUEL.csv",
                    f"{ROOT_DIR}/results/{scenario}/osemosys_global/COMMODITY.csv")
    demand = crop_demand(scenario, country_full_name)
    yaml_data = modify_yaml(
        scenario,
        region_codes,
        timeslice,
        emissions,
    )
    subprocess.run(
        [
            "python",
            "workflow/submodules/clewsy/src/build/clewsy.py",
            "config/clews_config/clewsy.yaml",
        ],
        input="Y",
        text=True,
        check=True,
    )
    try:
        os.remove(f"{ROOT_DIR}/results/{scenario}/clewsy/COMMODITY.csv")
    except FileNotFoundError:
        print("COMMODITY.csv not found")
    with open(f"{ROOT_DIR}/results/{scenario}/clewsy/EMISSION.csv", "w") as f:
        f.write("VALUE\n")
        for i in emissions:
            f.write(f"{i}\n")
    # new parameters here
    land_mapping = {
"LCType1": "Cropland",
"LCType2": "Forest land",
"LCType3": "Grassland & woodland",
"LCType4": "Barren and sparsely vegetated land",
"LCType5": "Cropland",
"LCType6": "Forest land",
"LCType7": "Grassland & woodland",
"LCType8": "Barren and sparsely vegetated land",
"LCType9": "Built-up land",
"LCType10": "Other agricultural land",
"LCType11": "Water bodies"
}
    # Retrieve LandCover by Cluster summary csv from GeoCLEWs results
    files = [
    f for f in os.listdir(yaml_data["DataDirectoryName"])
    if f.endswith("_LandCover_byCluster_summary.csv")
]
    file_path = os.path.join(yaml_data["DataDirectoryName"], files[0])
    df_lndarea = pd.read_csv(file_path) # same as land cover info in another function

    # rename land types and get totals
    df_lndarea["clusters_yield"] = df_lndarea["clusters_yield"].astype(int)
    df_lndarea.columns = df_lndarea.columns.str.strip()
    df_lndarea = df_lndarea.rename(columns=land_mapping)
    cluster_category_totals = df_lndarea.groupby(axis=1, level=0).sum(numeric_only=True)

    TechUpperLim = []
    LandRegion = next(iter(region_codes))
### TotalTechnologyAnnualActivityUpperLimit
    for cluster_num  in range(1, len(cluster_category_totals)+1):
        value = (df_lndarea.loc[
            df_lndarea["clusters_yield"] == cluster_num, "sqkm"
        ].values[0])/1000
        for year in yaml_data['Years']:
            TechUpperLim.append([
                next(iter(yaml_data['Regions'])),
                "LNDAGR" + LandRegion + "C" + str(cluster_num).zfill(2),
                year,
                value #math.ceil(value)
            ])

    TechUpperLim = pd.DataFrame(
        TechUpperLim,
        columns=['REGION','TECHNOLOGY','YEAR','VALUE']
    )
    TechUpperLim_df = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityUpperLimit.csv")
    TechUpperLim_df = pd.concat([TechUpperLim_df, TechUpperLim], ignore_index=True)
    TechUpperLim_df.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TotalTechnologyAnnualActivityUpperLimit.csv", index=False)
### TechnologyActivityByModeLowerLimit
    TechModeLowerLim = []
    
    with open(yaml_data['OperationModes'], 'r') as f:
        ModeList = ast.literal_eval(f.read())
    category_columns = [
        col for col in cluster_category_totals.columns
        if col in ModeList
    ]

    growth_factors = get_growth_factors(country_full_name, start_year, end_year)
    for cluster_num in range(1, len(cluster_category_totals) + 1):
        for col in category_columns:
            mode_idx = ModeList.index(col) + 1

            if col in ['Cropland', 'Forest land', 'Other agricultural land']:
                continue

            base_value = (cluster_category_totals.loc[cluster_num - 1, col]) / 1000

            for year in yaml_data['Years']:
                year = int(year)

                if col == 'Built-up land':
                    value = base_value * (1 + growth_factors.loc[year, "POP"])
                else:
                    value = base_value

                TechModeLowerLim.append([
                    next(iter(yaml_data['Regions'])),
                    "LNDAGR" + LandRegion + "C" + str(cluster_num).zfill(2),
                    mode_idx,
                    year,
                    value
                ])

    TechModeLowerLim = pd.DataFrame(
        TechModeLowerLim,
        columns=['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR','VALUE'])
    TechModeLowerLim.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TechnologyActivityByModeLowerLimit.csv", index=False)

    # TechnologyActivityByModeUpperLimit create empty dataframe
    TechModeUpperLim = pd.DataFrame(
        columns=['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR','VALUE'])
    TechModeUpperLim.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TechnologyActivityByModeUpperLimit.csv", index=False)
    # TechnologyActivityIncreaseByModeLimit create empty dataframe
    TechnologyActivityIncreaseByModeLimit = pd.DataFrame(
        columns=['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR','VALUE'])
    TechnologyActivityIncreaseByModeLimit.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TechnologyActivityIncreaseByModeLimit.csv", index=False)
     # TechnologyActivityDecreaseByModeLimit create empty dataframe
    TechnologyActivityDecreaseByModeLimit = pd.DataFrame(
        columns=['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR','VALUE'])
    TechnologyActivityDecreaseByModeLimit.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/TechnologyActivityDecreaseByModeLimit.csv", index=False)
    # Negative variable cost for forest:
    variable_cost_df = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/VariableCost.csv")
    VarCost = []
    for cluster_num in range(1, len(cluster_category_totals)+1):
        for year in yaml_data['Years']:
            value = -10
            mode = ModeList.index('Forest land')+1
            VarCost.append([
                    next(iter(yaml_data['Regions'])),
                    "LNDAGR" + LandRegion + "C" + str(cluster_num).zfill(2),
                    mode,
                    year,
                    value
                ])
    VarCost = pd.DataFrame(
        VarCost,
        columns=['REGION', "TECHNOLOGY", "MODE_OF_OPERATION", "YEAR", "VALUE"])
    variable_cost_df = pd.concat([variable_cost_df, VarCost], ignore_index=True)
    variable_cost_df.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/VariableCost.csv", index=False)
    # OperationalLife for agricultural land
    operational_life_df = pd.read_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/OperationalLife.csv")
    operational_life_df = operational_life_df.loc[
        ~operational_life_df["TECHNOLOGY"].astype(str).str.startswith("LND")
    ]
    cropcombo = [mode for mode in ModeList if mode not in land_mapping.values()]
    OL = []
    for crop in cropcombo:
        value = 15
        OL.append([
            next(iter(yaml_data['Regions'])),
            'LND' + crop + 'TOT',
            value
        ])

    OL = pd.DataFrame(
        OL,
        columns=['REGION', "TECHNOLOGY", "VALUE"])
    operational_life_df = pd.concat([operational_life_df, OL], ignore_index=True)
    operational_life_df.to_csv(f"{ROOT_DIR}/results/{scenario}/clewsy/OperationalLife.csv", index=False)
    demand_projection(demand, country_full_name, scenario, start_year, end_year)
    cost_land_tech(scenario, country_full_name, start_year, end_year)

    data_out_path = f"{ROOT_DIR}/results/{scenario}/clewsy"
    data_text = f"{ROOT_DIR}/results/{scenario}/data"
    clewsy_otoole_config = f"{ROOT_DIR}/config/clews_config/clewsy_otoole_config.yaml"
    deduplicate_otoole_csvs(data_out_path)
    subprocess.run(
        [
            "otoole", "convert", "csv", "datafile", data_out_path,
            f"{data_text}.txt", clewsy_otoole_config,
        ],
        check=True,
    )
    subprocess.run(
        [
            "python",
            f"{ROOT_DIR}/config/clews_config/preprocess_data.py",
            "otoole",
            f"{data_text}.txt",
            f"{data_text}_pp.txt",
        ],
        check=True,
    )
    subprocess.run(
        [
            "glpsol",
            "-m",
            f"{ROOT_DIR}/config/clews_config/osemosys_fast_preprocessed.txt",
            "-d",
            f"{data_text}_pp.txt",
            "--wlp",
            f"{data_text}.lp",
            "--check",
        ],
        check=True,
    )
    subprocess.run(
        ["cbc", f"{data_text}.lp", "solve", "-solu", f"{data_text}.sol"],
        check=True,
    )
    subprocess.run(
        [
            "otoole", "-v", "results", "cbc", "csv", f"{data_text}.sol",
            f"{ROOT_DIR}/results/{scenario}/results", "datafile",
            f"{data_text}.txt", clewsy_otoole_config,
        ],
        check=True,
    )
    print("clewsy finished successfully")


if __name__ == "__main__":
    if "snakemake" in globals():
        project_scenario = snakemake.config['scenario']
        project_region_codes = snakemake.config['region_codes']
        project_timeslice = snakemake.config['timeslice']
        project_country = snakemake.config['country_full_name']
        project_emissions = snakemake.config['emissions']
        project_start_year = snakemake.config['startYear']
        project_end_year = snakemake.config['endYear']
    else:
        project_scenario = "Guyana'"
        project_region_codes = {
                  'GUY': 'GUYXX',
        }
        project_timeslice = {
              'S1D1': ['Season 1 intermediate', ''],
              'S1D2': ['Season 1 peak', ''],
              'S2D1': ['Season 2 intermediate', ''],
              'S2D2': ['Season 2 peak', '']
}
        project_country = 'Guyana'
        project_emissions = ['CO2GUY']
        project_start_year = 2020
        project_end_year = 2035
    main(
        project_scenario,
        project_region_codes,
        project_timeslice,
        project_country,
        project_emissions,
        project_start_year,
        project_end_year,
    )
