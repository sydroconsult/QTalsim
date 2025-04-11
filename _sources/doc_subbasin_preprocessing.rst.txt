========================
Sub-basins preprocessing
========================

   The third core functionality allows you to pre-process a sub-basins layer. It calculates the highest and lowest points within the sub-basins, the area and average impermeable area (optional) per sub-basin, and the longest flow path for each sub-basin. Output includes a line layer containing the longest flow paths, a sub-basins layer (and Geopackage) containing the sub-basins with all calculated parameters and an .EZG-ASCII file, which can be used as `input to Talsim <https://www.talsim.de/docs/index.php?title=EZG-Datei>`__ (optional). Please note that to use this functionality the QGIS-Plugin WhiteboxTools must be installed. 

Prerequisites
^^^^^^^^^^^^^
   .. prerequisites:

   **Input Layers:**

   -  Sub-basin layer: For optimal performance, the sub-basin layer should be continuous, with no gaps or holes (e.g., no empty areas for dams)
   -  Digital Elevation Model (DEM) layer
   -  Optional: Water network layer (necessary for LongestFlowPath-calculation)
   -  Optional: Layer with impervious areas
   
   To use this plugin's functionality, WhiteboxTools must be installed.

   -  WhiteboxTools: Install the "WhiteboxTools for QGIS" plugin, and make sure the environment path is set correctly. 

      -  Install the "WhiteboxTools for QGIS" plugin.
      -  Download and install `WhiteboxTools Open Core <https://www.whiteboxgeo.com/download-whiteboxtools/>`__ and remember the path where you installed it.
      -  In QGIS go to Settings - Options - Processing - Providers - WhiteboxTools executable and insert the path to the binary of your download (e.g. C:/Users/Test/WhiteboxTools_win_amd64/WBT/whitebox_tools.exe).
      -  For further guidance, you can watch this instructional `video <https://www.youtube.com/watch?v=xJXDBsNbcTg>`__ produced by Whitebox. 

Executing the Plugin
^^^^^^^^^^^^^^^^^^^^
   
   After installing WhiteboxTools, you can run the plugin. 

Select Layers
-------------

   -  Choose the correct polygon layer for the sub-basin layer.
   -  Select the field that contains the unique identifier for the sub-basins.
   -  Select the field that contains the names of the sub-basins.
   -  Select the DEM layer (raster layer) and the water network layer (line layer). The water network layer is only necessary for calculating LFP. 
   -  Optional: Select a layer containing impervious areas (`Example data set <https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/3bf542bd-eebd-4d73-b53c-a0243f2ed862>`__). 
      
      -  Values should be expressed as percentages

Calculation of LongestFlowPath
------------------------------

   The calculation of LongestFlowPath is optional. The plugin first burns the water network into the DEM using the QGIS "Raster calculator".
   It then applies Whitebox' "FillDepressionsWangAndLiu" tool to fill any sinks in the DEM. After this the plugin uses WhiteboxTools' "LongestFlowPath" (LFP) to generate the longest flowpath for each sub-basin. To address an issue with LFP creating disconnected flowpaths across different sub-basins (see details `here <https://github.com/jblindsay/whitebox-tools/issues/289>`__), the plugin processes each sub-basin individually, generating the LFP for each one separately. Finally, the plugin saves the correct LFP for each sub-basin and merges them into a single layer.
   
   The final LFP layer is added to the current QGIS project and saved to the specified output folder. Additionally, the burned and filled DEM layer is also saved and added to the current project.

Output
------

   -  When choosing the output folder, it is recommended to use a folder that does not contain any spatial files, as using the same file names can lead to issues.
   -  Select ASCII-Export and/or SQLite-Export
   -  ASCII-Export: Choose ASCII-Output to input a filename for the .EZG-ASCII-file.
   -  SQLite-Export: Insert names for scenario and database. 
   -  Output Parameters:

      -  Area of sub-basin in hectares [ha].
      -  Optional: Average impervious area in the sub-basin [%] (=field 'Imp_mean').
      -  Maximum height in sub-basin [MASL].
      -  Minimum height in sub-basin [MASL].
      -  Optional (if calculated): Longest flow path [m] (=field 'Length'). 



   |Screenshot Sub-basin preprocessing|

.. |Screenshot Sub-basin preprocessing| image:: qtalsim_screenshots/SubBasinPreprocessing.png