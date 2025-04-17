
Getting Started with HRUs
-------------------------
.. _getting-started:

Requirements for Input Layers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   .. _requirements-for-input-layers:

   All three necessary input layers must be polygon layers and included in the
   current QGIS project. Additionally a raster DEM layer can be used as input to calculate the slope. 

   #. Sub-basin layer

      This layer should contain the sub-basins as well as a field for
      Unique Identifiers and another one for slope.

      - If you want to export to Talsim NG5, you should first create a Talsim database using the plugin feature **Sub-basins Preprocessing**.

   #. Soil Layer

      This layer should contain all soil types within the study area and can consist of up to 6 soil layers. It must contain at least a
      field specifying the names of the soil types of one soil layer. Plugin feature "ISRIC soil type converter" can be used to create this input layer. 

   #. Land Use Layer

      This layer should contain all land use areas within the study
      area, and it must contain a field specifying the names of the land
      use types. The land use input layer can be created by the plugin feature "Land use mapping", if your area is in Germany and you want to use ATKIS land use data. 

   #. Optional: DEM Layer

      The DEM layer is optional, and if a DEM layer is uploaded, the slope for each HRU will be calculated.


   Continue to the next section for detailed step-by-step instructions: `Step-by-Step Guide <https://sydroconsult.github.io/QTalsim/hrus_step_by_step.html>`__ 
      

      

