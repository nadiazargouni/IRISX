# Downloading IRIS shapefiles (France)

In France, shapefiles of census blocks (*IRIS – Ilots Regroupés pour l’Information Statistique*) are produced and updated on a **yearly basis** by the **IGN (Institut national de l’information géographique et forestière)**, the national agency in charge of authoritative geospatial reference data. 

The official IRIS datasets are distributed through the IGN GeoServices platform and include:
- polygon geometries,
- attribute tables containing IRIS identifiers and administrative information,
- projection files (`.prj`) and metadata,
- standardized delivery packages suitable for GIS and spatial analysis workflows.

The full documentation and download options for IRIS products are available on the IGN website:  
[https://geoservices.ign.fr/contoursiris](https://geoservices.ign.fr/contoursiris)


---


## Use the IRIS shapefiles to create IRISX

To create IRISX, the code works provided that you give as inputs the right arguments. Namely, in order to create a *Shapefile* of IRISX based on the the geometry of IRIS of a reference year (say, 2019), you would have to upload a 'Contours…IRIS®' Shapefile from IGN inside the `data/` folder. 

Pass the `--contours-folder` argument with your own path (for example, `data/CONTOURS-IRIS_2019.zip`) to run the main code from the command line.


---


## Replication of Garrouste & Lafourcade (2025)

The IRISX construction algorithm implemented in this repository was developed for the following paper:

> **Manon Garrouste, Miren Lafourcade (2025).** *Place-Based Policies: A Path to Opportunity or a Mark of Stigma for Targeted Neighborhoods?* *Journal of the European Economic Association*.

As the empirical analysis relies on **panel data covering the period 2009-2019**, the **2019 reference version of IRIS boundaries** is used as the baseline geometry. All IRISX geometries are constructed by aggregating IRIS polygons from this reference year, ensuring spatial consistency across the study period.

The default `--contours-folder` argument of our main function is `CONTOURS-IRIS_2019.zip`. 

The exact IRIS shapefile used in this project can be downloaded directly from the official IGN distribution platform:  
[Download Link for 2019 Contours…IRIS®](https://data.geopf.fr/telechargement/download/CONTOURS-IRIS/CONTOURS-IRIS_2-1__SHP__FRA_2019-01-01/CONTOURS-IRIS_2-1__SHP__FRA_2019-01-01.7z)


---


## Troubleshooting

Depending on the local geospatial stack (GeoPandas / Fiona / GDAL versions and installation method), loading a shapefile directly from a `.zip` archive may fail. If you encounter errors when providing a path to a zipped shapefile (e.g. `CONTOURS-IRIS_2019.zip`), the recommended solution is to:

1. Unzip the archive so that all shapefile components are available in a directory inside `data/`  
   (`.shp`, `.shx`, `.dbf`, `.prj`, and any additional files).
2. Provide the path to the `.shp` file directly in the  `--contours-folder` argument.
