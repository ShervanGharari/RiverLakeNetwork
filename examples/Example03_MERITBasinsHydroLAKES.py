# outputfolder for where the files will be sitting
OutFolder = '/Users/shg096/Desktop/LakeRiverOut/MERITBasins/'

# location of MERIT-Basin bug fixed files
regions = {
    "71": {
        "files": {
            "riv": '/Users/shg096/Desktop/MERIT_Hydro/riv/riv_pfaf_71_MERIT_Hydro_v07_Basins_v01_bugfix1.shp',
            "cat": '/Users/shg096/Desktop/MERIT_Hydro/cat/cat_pfaf_71_MERIT_Hydro_v07_Basins_v01_bugfix1.shp',
            "cst": '/Users/shg096/Desktop/MERIT_Hydro/hill/hillslope_71_clean.shp',
        }
    },
    # "74": {
    #     "files": {
    #         "riv": '/Users/shg096/Desktop/MERIT_Hydro/riv/riv_pfaf_74_MERIT_Hydro_v07_Basins_v01_bugfix1.shp',
    #         "cat": '/Users/shg096/Desktop/MERIT_Hydro/cat/cat_pfaf_74_MERIT_Hydro_v07_Basins_v01_bugfix1.shp',
    #         "cst": '/Users/shg096/Desktop/MERIT_Hydro/hill/hillslope_74_clean.shp',
    #     }
    # },
}

# location of HydroLAKES
lake_file = '/Volumes/F:/hydrography/hydrolakes/HydroLAKES_polys_v10_shp/HydroLAKES_polys_v10_shp/HydroLAKES_polys_v10.shp'

# load the needed packages
import os
import shutil
import geopandas as gpd
from   riverlakenetwork import Utility, BurnLakes
import warnings; warnings.filterwarnings("ignore")


#load hydrolakeDataset
lake = gpd.read_file(lake_file) # read the hydrolake dataset
# merge lake Michigan and Huron as they are hydraulically connected
lake = Utility.FixHydroLAKESv1(lake, merge_lakes={"Michigan+Huron": [6, 8]})
lake = lake.set_crs("EPSG:4326") # make sure the lake has projection


# loop over regions and their files
for pfaf, files in regions.items():

    # read the pfaf merit folder
    riv, cat = Utility.merit_read_file(riv_file=files["files"]["riv"],
                                       cat_file=files["files"]["cat"],
                                       cst_file=files["files"]["cst"])

    # create folder to save
    pfaf_base = f"pfaf{pfaf}"
    # create the folder if not existed
    org_folder = os.path.join(OutFolder, f"{pfaf_base}_org")
    if os.path.isdir(org_folder):
        try:
            shutil.rmtree(org_folder)
        except OSError as e:
            raise RuntimeError(f"Failed to remove {org_folder}: {e}")
    os.makedirs(org_folder, exist_ok=True)

    # Manual correction for various pfafs from bugfix version
    # for pfaf 74, COMID 74030207, downstream COMID is similar to COMID! turn into a coastal
    riv.loc[riv["COMID"] == 74030207, ["NextDownID", "geometry", "maxup", "up1", "length"]] = [-9999, None, 0, 0, 0]

    # make sure the riv, and cat have projection
    riv = riv.set_crs("EPSG:4326")
    cat = cat.set_crs("EPSG:4326")

    # save riv, and cat
    riv.to_file(os.path.join(org_folder, "riv.gpkg"))
    cat.to_file(os.path.join(org_folder, "cat.gpkg"))

    # create the config and pass it to the Burn lake
    config = {
        "riv": riv,
        "riv_dict": {
            "COMID": {"col":"COMID"},
            "NextDownCOMID": {"col":"NextDownID"},
            "length": {"col":"lengthkm"},
            "uparea": {"col":"uparea","unit":"km2"}
        },
        "cat": cat,
        "cat_dict": {
            "COMID": {"col":"COMID"},
            "unitarea": {"col":"unitarea","unit":"km2"},
        },
        "lake": lake,
        "lake_dict": {
            "LakeCOMID": {"col":"Hylak_id"},
            "unitarea": {"col":"Lake_area","unit":"km2"}
        },
    }

    # burn lakes into river network
    bl = BurnLakes(config,
        single_segment_lakes_activate_flag = True,
        single_segment_lakesID_position = {83279: "up",
                                           84896: "up",
                                           6550: "up",
                                           87073: None, # will be populated by single_segment_global_position
                                           86960: None, # will be populated by single_segment_global_position
                                           6643: None, # will be populated by single_segment_global_position
                                           },
        single_segment_lakesID_restrict = True, # if false it will try to resolve as much as one segment lakes
        single_segment_lakes_global_position = "down")

    # create folder to save
    pfaf_base = f"pfaf{pfaf}"
    # create the folder if not existed
    corrected_folder = os.path.join(OutFolder, f"{pfaf_base}_corrected")
    if os.path.isdir(corrected_folder):
        try:
            shutil.rmtree(corrected_folder)
        except OSError as e:
            raise RuntimeError(f"Failed to remove {corrected_folder}: {e}")
    os.makedirs(corrected_folder, exist_ok=True)

    # save riv, cat, and lake
    bl.riv.to_file(os.path.join(corrected_folder, "riv.gpkg"))
    bl.cat.to_file(os.path.join(corrected_folder, "cat.gpkg"))
    bl.lake.to_file(os.path.join(corrected_folder, "lake.gpkg"))

    #
    bl.single_segment_lake.to_file(os.path.join(corrected_folder, "single_segment_lake.gpkg"))