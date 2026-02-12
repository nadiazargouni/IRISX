**Paper**: [Click to read explanatory paper](https://nadiazargouni.github.io/IRISX/)

# README

This repository reproduces the **IRISX outputs** for the period 2009–2019. It was initially constructed for Garrouste and Lafourcade (2025). 
The **outputs** include:

- `IRIS_historiques_IRISX.xlsx` is a historical table mapping each IRIS code (column `IRIS`) to its IRISX (column `irisx_id`), and to its year of creation (`annee_corresp_`). 
- `IRISX20092019.shp` is a shapefile aggregating IRIS boundaries for reference year (2019 in our case) by IRISX (requires geopandas). Column `irisx_id` is the IRISX unique ID, column `CODE_IRIS_` is IRIS code in reference year, and column `geometry` is the resulting IRISX polygon coordinates. 


---

## Methodology of IRISX creation

Our analysis required stable geographical units, which means units which boundaries do not move over time. One way to create these units is to form what we will later call IRISX, which are geographical units constructed from IRIS but designed to remain stable over time. Thanks to their “neutral” form—that is, units that are not malleable according to periods of densification or depopulation of specific IRIS. To construct IRISX, we implemented a directed graph approach, inspired by Behrens and Martin (2015). This approach groups together IRIS that have shared the same code at some point within a given period. The algorithm, developed in Python, outputs a geographical database of IRISX, representing each IRISX as a grouping of at least one IRIS from a reference year (denoted IRIS_year|IRISX). Our strategy was based on graph theory, and our IRIS groups can be theoretically associated to weakly connected components, which are subgraphs that are unreachable from other nodes/vertices of another graph or subgraph.
 One limitation of this method is that it is not fully robust to code recycling. Code recycling occurs when a code assigned to an IRIS in year n is transferred to another IRIS elsewhere in year n+1 due to changes in the shape or composition of the original IRIS. This limitation is compounded by the lack of documentation on the IRIS code construction process. IRIS naming do not seem to follow a clear logic, and if it does in main agglomerations, this logic is not exactly harmonized at the national level. However, fortunately, testing on the transition tables revealed that code recycling does not actually occur in our data.
Our algorithm also differs from that of Behrens and Martin (2015), as we do not have a pre-existing file recording all modifications by date. Instead, we rely mainly on an IRIS annual correspondence table, Insee references of IRIS, and Insee recordings of IRIS changes, which provide the necessary information to track changes and construct the IRISX units.


## Input data

- `table_passage_2009_2019.csv` is a correspondence table that retraces the trajectory of each IRIS, for each IRIS code that has ever existed from 2009 to 2019. This table was created by replicating the work of Adélaïde et al. (2023), enriched by the latest Insee documentation (see [Insee page](https://www.insee.fr/fr/information/7708995))

## Folder structure

```root/
├─ data/
│ ├─ table_passage_2009_2019.csv # IRIS correspondence table
│ └─ CONTOURS-IRIS_2019.zip # Zipped shapefiles of IRIS boundaries (polygons) - EPSG:2154
│ └─ CONTOURS-IRIS_2019.shp, .dbf, .cpg, .shx, .prj # files of IRIS boundaries (polygons) - EPSG:2154 (if can't open .zip)

├─ outputs/
│ ├─ IRIS_historiques_IRISX.xlsx # Historical IRIS data
│ └─ IRISX20092019.zip # IRISX boundaries - EPSG:2154
├─ build_irisx.py # Main code to generate IRISX
├─ requirements.txt # List of dependencies
└─ README.md # documentation (you are here)
```
---

## Installation

0. **Local or cloud environment?**  
   The script can be executed either:
   - Locally, using **Python 3.8 or higher** installed on your system.  
   - Or in any **cloud-based Python environment** such as **Google Colab**, **Kaggle Notebooks**, ... 
1. Clone the repository (or replication package).  
2. Install dependencies:

```bash
pip install -r requirements.txt
```
3. Download on [IGN website](https://geoservices.ign.fr/contoursiris) IRIS boundaries Shapefile for your reference year (here by default 2019). This step is extensively explained in `data/link_to_download_IRIS_shapefile.md`. 

## Running the script

This script is not designed to run in a notebook and should be executed from the **command line**.

```bash
python build_irisx.py --passage-table data/table_passage_2009_2019.csv \
                      --year-ref 2019 \
                      --contours-folder data/CONTOURS-IRIS_2019.zip \
                      --out-dir outputs \
                      --iris-columns 2009 2010 2011 2012 2013 2014 2015 2016 2017 2018 2019
```

Default arguments will return the files used in this article. 
```bash
    python build_irisx.py
```

Use help to get a description of the arguments. 
```bash
python build_irisx.py --help
```



## References
- Adélaïde, L., Stempfelet, M., Babut, C., Bulté, A., Ehrhart, B., and Jaccy, N. (2023). HistorIRIS: table de passage des IRIS de 1999 à 2022. *Technical report, Commissariat Général au Développement durable (CGDD)*.
- Behrens, K. and Martin, J. (2015). Concording large datasets over time: The c3 method. *Unpublished paper*.
- Garrouste, M. and Lafourcade, M. (2025). Place-based policies: A path to opportunity or a mark of stigma for targeted neighborhoods? *Journal of the European Economic Association*. Conditionally accepted. Revised version of CEPR Discussion Paper No. 17750.

## Contact 

The author acknowledges the support of the French Agence Nationale de la Recherche (ANR), under grant \href{https://anr.fr/Project-ANR-23-CE26-0001}{ANR-23-CE26-0001} (project URBOPP).
Nadia Zargouni, nadia.zargouni@ensae.fr





