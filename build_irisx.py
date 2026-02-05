#!/usr/bin/env python3
"""
build_irisx.py

Single script to reproduce the IRISX replication package outputs described by the user:
- IRIS_historiques_IRISX.xlsx (latest version produced by this pipeline)
- IRISX20092019.zip (shapefile and associated files aggregating IRIS into permanent IRISX units for 2009-2019)

This script is written to be robust to different folder layouts.
See README.md for required filenames, processing of input data, and example usage.

Main steps:
1. Read the passage table (CSV) that contains, for each spatial unit, its year-specific IRIS code.
2. Create directed edges between successive non-null IRIS codes for the same unit.
3. Build an undirected graph from edges and compute connected components -> each component is an IRISX and has an IRISX id.
4. Create a historical CSV mapping each IRIS code (year-specific) to its IRISX id and export IRIS_historiques_IRISX.xlsx.
5. If contour shapefiles are provided for 2019, assign each polygon the IRISX id using the IRIS code present in the shapefile's attribute table,
   and dissolve (union) geometries by IRISX to produce IRISX20092019.shp.

Notes:
- The script logs clearly and exits with helpful messages when required inputs are missing.

Author: Nadia Zargouni.
"""

import argparse
import logging
from pathlib import Path
import sys
import re
import os
import shutil
import zipfile
import time
import pandas as pd
import networkx as nx
import numpy as np
from tqdm import tqdm

try:
    import geopandas as gpd
    import mapclassify
    from shapely.ops import unary_union
except Exception as e:
    gpd = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

#Builder functions:

def add_leading_zeros(x):
    """
    Ensures that a value has 9 characters by adding leading zeros if needed.
    IRIS are indexed by 9-digit codes = 5-digit INSEE municipality code + 4-digit IRIS-specific code.
    """
    if pd.isna(x):
        return  np.nan
    if (pd.notna(x) & str(x).isnumeric()):
        return str(int(x)).zfill(9)[:9]
    elif pd.notna(x) & str(x).isnumeric()==False:
        return str(x).zfill(9)[:9]
    else :
        return x


def edge_list_(table_passage):
    """
    Create edges (pairs) between consecutive year-specific IRIS codes.
    """
    edges_list = []
    cols = table_passage.columns

    for i in tqdm(range(len(cols) - 1), desc="Building edge list"):
        current = table_passage[cols[i]]
        next_ = table_passage[cols[i + 1]]
        valid = current.notna() & next_.notna()
        edges_list.extend(zip(current[valid], next_[valid]))

    return edges_list


def edges_list_to_graph(edges_list):
    """
    Build a directed graph from the edge list.
    """
    return nx.from_edgelist(edges_list, create_using=nx.DiGraph)



def build_table_irisx(table_passage):
    """
    Build table_irisx with columns:
        - irisx_id: numeric id of connected component
        - iris_nodes: list of IRIS codes (as Python list string)

    The CSV is written once, cleanly formatted.
    """
    logging.info("Starting IRISX table construction...")
    edges = edge_list_(table_passage)
    G = edges_list_to_graph(edges)
    logging.info("Computing weakly connected components...")
    components = list(nx.weakly_connected_components(G))
    logging.info(f"Found {len(components):,} connected components (IRISX).")

    table_irisx = pd.DataFrame({
        "irisx_id": range(len(components)),
        "iris_nodes": [list(component) for component in components]
    })

    table_irisx['irisx_id'] = table_irisx['iris_nodes'].apply(lambda x:'_'.join([str(element) for element in x])) 


    logging.info(f"Table of weakly connected IRIS nodes created successfully ({len(table_irisx):,} rows).")
    return table_irisx



def table_iris_historiques_irisx(table_passage, table_irisx,
                                  out_xlsx):
    """
    IRIS–IRISX mapping builder with progress bar, 
    to map IRIS (year-specific) to IRISX id
    """

    irisx_expanded = table_irisx[['irisx_id', 'iris_nodes']].copy()

    irisx_expanded['iris_nodes'] = irisx_expanded['iris_nodes'].apply(
        lambda x: x if isinstance(x, list) else eval(x) if isinstance(x, str) else []
    )

    irisx_expanded = irisx_expanded.explode('iris_nodes')

    irisx_expanded = irisx_expanded.rename(columns={'iris_nodes': 'IRIS'})

    # Keep only the two columns
    irisx_expanded = irisx_expanded[['irisx_id', 'IRIS']]

    table_passage_long = (
        table_passage
        .reset_index()
        .melt(id_vars=table_passage.index.name or 'index',
              var_name='annee_corresp_', value_name='IRIS')
        .sort_values(['IRIS', 'annee_corresp_'])
        .dropna(subset=['IRIS'])
        
    )

    merged = pd.merge(table_passage_long, irisx_expanded, on='IRIS', how='left')

    merged = merged[['annee_corresp_', 'irisx_id', 'IRIS']].drop_duplicates()
    merged = merged.reset_index(drop=True)
    merged['annee_corresp_']=merged['annee_corresp_'].apply(lambda x:int(x[-4:]))
    merged = merged.sort_values(['IRIS', 'annee_corresp_'])  # sort by IRIS then year
    merged = merged.drop_duplicates(subset=['IRIS'], keep='first') 
    merged.to_excel(out_xlsx, index=False)
    logging.info(f"Wrote history Excel file to {out_xlsx} ({len(merged):,} rows)")
    return merged

def find_irisx_in_df(table_passage, irisx):
    """
    Find IRISX in correspondence table.
    """

    example_connected_components = set(irisx)
    result = table_passage.isin(example_connected_components)

    rows_with_value = table_passage[result.any(axis=1)]
    return rows_with_value

def find_iris_in_df(table_passage, iris):
    """
    Find IRISX in correspondence table.
    """
    result = table_passage.isin([iris])

    rows_with_value = table_passage[result.any(axis=1)]
    return rows_with_value

def irisx_year_reference(table_irisx, table_passage, iris_cols, year_ref: str, history: pd.DataFrame):
    """
    Create a table with all IRIS codes of a specific year and their corresponding
    IRISX. 
    """
    logging.info("Precomputing IRIS to reference-year (%s) mapping...", year_ref)
    iris_colnames = [f'CODE_IRIS_{i}' for i in iris_cols]
    melted = table_passage.melt(value_vars=iris_colnames, var_name="year_col", value_name="IRIS")
    melted["year"] = melted["year_col"].str.extract(r"(\d{4})").astype(int)

    ref_col = f"CODE_IRIS_{year_ref}"
    if ref_col not in table_passage.columns:
        raise ValueError(f"{ref_col} not found in passage table")

    iris_ref_map = (
        melted.merge(
            table_passage[[ref_col]],
            left_index=True,
            right_index=True,
            how="left"
        )
        [["IRIS", ref_col]]
        .dropna()
        .drop_duplicates()
        .groupby("IRIS")[ref_col]
        .apply(lambda x: list(x.unique()))
        .to_dict()
    )

    #sanity check
    for iris in table_passage[ref_col].dropna().unique():
      if iris not in iris_ref_map:
        iris_ref_map[iris] = [iris]

    def get_ref_from_nodes(nodes):
        codes = set()
        for iris in nodes:
            if iris in iris_ref_map:
                codes.update(iris_ref_map[iris])
        return list(codes)

    table_irisx = table_irisx.copy()
    table_irisx["iris_nodes"] = table_irisx["iris_nodes"].apply(
        lambda x: x if isinstance(x, list) else eval(x) if isinstance(x, str) else []
    )

    logging.info("Building corresp_%s mapping...", year_ref)
    table_irisx[f"corresp_{year_ref}"] = table_irisx["iris_nodes"].apply(get_ref_from_nodes)

    dfyear = table_irisx.explode(f"corresp_{year_ref}").dropna(subset=[f"corresp_{year_ref}"]).reset_index(drop=True)
    dfyear[f"corresp_{year_ref}"] = dfyear[f"corresp_{year_ref}"].astype(str).apply(add_leading_zeros)
    


    logging.info("Adding ANNEE_MODI column (year of code creation) from history...")
    history["IRIS"] = history["IRIS"].astype(str).apply(add_leading_zeros)

    years_per_iris =(history.groupby('IRIS')['annee_corresp_'].apply(
    lambda x: ', '.join(list(set([str(y) for y in x])))).to_dict())

    dfyear["ANNEE_MODI"] = dfyear[f"corresp_{year_ref}"].map(years_per_iris)

    return dfyear



def merging_irisx_iris_year_ref(shpyear, dfyear, year_ref, out_shp):
    """
    Create Shapefile IRISX by dissolving geometries by IRISX from IRIS Shapefile of reference year. 
    """
    gdf = pd.merge(shpyear,dfyear, left_on="CODE_IRIS",right_on=f'corresp_{year_ref}', how='inner')
    logging.info("Dissolving geometries by IRISX...")
    gdf_dissolved = gdf.dissolve(by='irisx_id',
    aggfunc={'CODE_IRIS': lambda x: ', '.join(x.astype(str)),
             'ANNEE_MODI': lambda x: ', '.join(x.astype(str))})
    gdf_dissolved = gdf_dissolved[['CODE_IRIS', 'ANNEE_MODI','geometry']].reset_index()
    gdf_dissolved.columns = ['irisx_id','CODE_IRIS_', 'ANNEE_MODI','geometry']
    gdf_dissolved.to_file(out_shp)
    logging.info(f"Wrote shapefile to {out_shp} (polygons={len(gdf_dissolved):,})")
    return gdf_dissolved


def zip_selected_files(folder_path, output_zip_file, file_criteria=None):
    """
    Zips selected files from the folder based on the provided criteria.
    """
    with zipfile.ZipFile(output_zip_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                if match_criteria(file, file_criteria):
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)

    logging.info(f'Selected files from {folder_path} have been zipped into {output_zip_file}.')

def match_criteria(file, file_criteria):
    """
    Determines whether a file matches the given criteria.
    """
    if isinstance(file_criteria, list):
        return any(file.startswith(root) for root in file_criteria)
    
    elif callable(file_criteria):
        return file_criteria(file)
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Build IRISX outputs (CSV of all modifications + shapefile)")
    parser.add_argument('--passage-table', type=str, default='data/table_passage_2009_2019.csv',
                        help='CSV with passage table')
    parser.add_argument('--year-ref', type=str, default='2019',
                        help='Reference year for building Shapefile. If not 2019 please provide corresponding IRIS contour shapefile')
    parser.add_argument('--contours-folder', type=str, default='data/CONTOURS-IRIS_2019.shp',
                        help='Zipped folder with IRIS contour shapefiles. ' \
                        'If cannot use geopandas on .shp, put data/CONTOURS-IRIS_2019.zip instead. ' \
                        'If provided, shapefile IRISXYYYY.shp will be produced.')
    parser.add_argument('--out-dir', type=str, default='outputs', help='Output folder name')
    parser.add_argument('--iris-columns', nargs="+", type=int, default=range(2009,2020),
                        help='If provided, list column names (in order) to use as IRIS columns in the passage table. Example: 1990 1999 2009 2015 2019')
    # parser.add_argument('--iris-field-names', type=str, nargs='*', default=None,
    #                     help='Preferred column names in shapefiles that contain the IRIS code.')
    args = parser.parse_args()

    print("Passage table:", args.passage_table)
    print("Reference year:", args.year_ref)
    print("Contours folder:", args.contours_folder)
    print("Output directory:", args.out_dir)
    print("IRIS columns:", args.iris_columns)

    out_dir = Path(args.out_dir)

    if out_dir.exists() and out_dir.is_dir():
      shutil.rmtree(out_dir)
      print(f"Deleted existing folder: {out_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = Path('temp')

    if temp_dir.exists() and temp_dir.is_dir():
      shutil.rmtree(temp_dir)
      print(f"Deleted existing folder: {temp_dir}")

    temp_dir.mkdir(parents=True, exist_ok=True)


    passage_path = Path(args.passage_table)
    if not passage_path.exists():
        logging.error("Passage table not found: %s", passage_path)
        logging.error("Please put your table_passage_2009_2019.csv in the working directory or provide --passage-table path.")
        sys.exit(2)

    logging.info("Reading passage table %s", passage_path)
    table_passage = pd.read_csv(passage_path, dtype=str)
    table_passage = table_passage[sorted(table_passage.columns)]
    # select time frame for iris linking
    if args.iris_columns:
        iris_cols = args.iris_columns
    else:
        iris_cols = range(2009, 2020)
    table_passage = table_passage[[f'CODE_IRIS_{i}' for i in iris_cols]]
    for col in table_passage.columns:
     table_passage[col]= table_passage[col].apply(lambda x : add_leading_zeros(x))
    
    
    table_irisx = build_table_irisx(table_passage)


    # produce IRIS_historiques_IRISX csv
    out_xlsx = out_dir / 'IRIS_historiques_IRISX.xlsx'
    history = table_iris_historiques_irisx(table_passage=table_passage, table_irisx=table_irisx,
                                           out_xlsx=out_xlsx)

    # produce IRISX->IRIS reference year table to produce Shapefile. 
    year_ref = args.year_ref
    try:
        dfyear = irisx_year_reference(table_irisx=table_irisx, table_passage=table_passage, iris_cols = iris_cols,
         year_ref=year_ref, history = history)
        dfyear.to_csv(temp_dir / 'temp_iris_ref.csv')
    except Exception as e:
        logging.exception("Failed to produce IRISX -> IRIS(year reference) table: %s", e)
    
    # produce shapefile
    if args.contours_folder:
        try:
            geometry_files_name = f'IRISX{min(iris_cols)}{max(iris_cols)}'
            out_shp = temp_dir / f'{geometry_files_name}.shp'
            shpyear = gpd.read_file(Path(args.contours_folder))
            gdf_dissolvedyear = merging_irisx_iris_year_ref(dfyear=dfyear, shpyear=shpyear, year_ref = year_ref,
                out_shp=out_shp)
        except Exception as e:
            logging.exception("Failed to produce shapefile: %s", e)
            logging.error("Continuing after shapefile failure. The CSV was already produced.")

    out_zip = out_dir /f'{geometry_files_name}.zip'
    zip_selected_files(folder_path=temp_dir, output_zip_file= out_zip, file_criteria=[geometry_files_name])


    logging.info(f"Done. Outputs are in {out_dir}")


if __name__ == '__main__':
    main()
