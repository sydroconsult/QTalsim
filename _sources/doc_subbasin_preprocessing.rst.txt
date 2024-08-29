========================
Sub-basins preprocessing
========================
   The third core functionality allows you to pre-process a sub-basins layer. It calculates the highest and lowest points within the sub-basins, the area and average impermeable area (optional) per sub-basin, and the longest flow path for each sub-basin. Output includes a line layer containing the longest flow paths, a sub-basins layer (and Geopackage) containing the sub-basins with all calculated parameters and an .EZG-ASCII file, which can be used as `input to Talsim <https://www.talsim.de/docs/index.php?title=EZG-Datei>`__ (optional). Please note that to use this functionality, SAGA GIS and WhiteboxTools must be installed. 

Prerequisites
^^^^^^^^^^^^^
   .. prerequisites:

**Input Layers:**

- Sub-basin layer
- Digital Elevation Model (DEM) layer
- Water network layer
- Optional: Layer with impervious areas
   
To use this plugin's functionality, SAGA GIS and WhiteboxTools must be installed.

- SAGA GIS: Ensure that the "Processing Saga NextGen Provider" plugin is installed via the Plugin Manager in QGIS.
- WhiteboxTools: Install the "WhiteboxTools for QGIS" plugin, and make sure the environment path is set correctly. For further guidance, you can watch this instructional `video <https://www.youtube.com/watch?v=xJXDBsNbcTg>`__ produced by Whitebox.

Executing the Plugin
^^^^^^^^^^^^^^^^^^^^
   
   After installing SAGA GIS and WhiteboxTools, you can run the plugin.

Select Layers
-------------

- Choose the correct polygon layer for the sub-basin layer.
- Select the field that contains the unique identifier for the sub-basins.
- Select the DEM layer (raster layer) and the water network layer (line layer).
- Optional: Select a layer containing impervious areas (`Example data set <https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/3bf542bd-eebd-4d73-b53c-a0243f2ed862>`__). 

Output
------
- When choosing the output folder, it is recommended to use a folder that does not contain any spatial files, as using the same file names can lead to issues.
- Optional: Choose ASCII-Output to input a filename for the .EZG-ASCII-file.
- Output Parameters:

  - Area of sub-basin in hectares [ha].
  - Optional: Average impervious area in the sub-basin [%] (=field 'Imp_mean').
  - Maximum height in sub-basin [MASL].
  - Minimum height in sub-basin [MASL].
  - Longest flow path [m] (=field 'Length'). 

Calculation of LongestFlowPath
------------------------------
   The plugin first burns the water network into the DEM using the QGIS "Raster calculator".
   It then applies SAGA's "Fill sinks (Wang & Liu)" tool to fill any sinks in the DEM. After this The plugin uses WhiteboxTools' "LongestFlowPath" (LFP) to generate the longest flowpath for each sub-basin. To address an issue with LFP creating disconnected flowpaths across different sub-basins (see details `here <https://github.com/jblindsay/whitebox-tools/issues/289>`__), the plugin processes each sub-basin individually, generating the LFP for each one separately. Finally, the plugin saves the correct LFP for each sub-basin and merges them into a single layer.
   
   The final LFP layer is added to the current QGIS project and saved to the specified output folder. Additionally, the burned and filled DEM layer is also saved and added to the current project.

   |Screenshot Sub-basin preprocessing|

.. |Screenshot Sub-basin preprocessing| image:: qtalsim_screenshots/SubBasinPreprocessing.png