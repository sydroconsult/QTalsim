Welcome to QTalsim's documentation!
===================================

   QTalsim is a QGIS plugin with five principal functionalities that enable the processing of spatial data suitable for `Talsim <https://www.talsim.de/docs/index.php?title=Hauptseite/en>`__.  The core functionality of this plugin is to calculate Hydrological Response Units (HRUs) suitable for Talsim. This feature requires three input layers, that can also be created by the plugin. Further more, it is possible to connect to a Talsim database and to edit elements. 

Main Features
-------------

      -  **Sub-basins Preprocessing** (:doc:`doc_subbasin_preprocessing`)
         
         Calculates various parameters for each sub-basin from a provided sub-basin layer and generates files compatible with Talsim.

      -  **ISRIC Soil Type Converter** (:doc:`doc_soil`) 

         Downloads and processes data from ISRIC, creating a soil layer that includes soil type and bulk density.

      -  **Land Use Mapping** (:doc:`doc_landuse`)

         If your area is in Germany, this feature allows you to convert ATKIS land use data, LBM land cover data or download and convert ESA world cover data into Talsim land use categories.
		 
      -  **HRU Calculation** (:doc:`doc_qtalsim`)
         
         Enables users to calculate Hydrological Response Units (HRUs).
      -  **Connect to Talsim DB** (:doc:`doc_connect_to_db`)

         For users of Talsim NG5, this functionality enables a direct connection to a Talsim database, allowing you to edit system elements, sub-basins, and transport reaches.

Contents
--------

.. toctree::
   :maxdepth: 2

   install_plugin
   doc_subbasin_preprocessing
   doc_soil
   doc_landuse
   doc_qtalsim
   doc_connect_to_db