# Changelog

## \[1.6.4] - 2025-07-25

* Enhancement

  * Land use Mapping: Add possibility to map LBM-DE2021 data to Talsim land uses

* Fixes

  * ISRIC Soil Type Converter: reproject layer correctly if geodetic system is not WGS84
  * HRU-calculation: ensure manual Ids are used by resetting AUTOINCREMENT when reusing a Talsim DB

## \[1.6.3] - 2025-04-17

* New feature - Land use Mapping

  * Plugin feature to map ATKIS land use data to Talsim land use categories
  * Output layer can be used as input to HRU calculation

* Enhancement

  * HRU Calculation

    * Implemented possibility to export to Talsim DB (#18)
    * Enhance Performance
    * Very small HRUs (< 0.001%) are deleted (#19)
    * Updated LNZ file output Format to v2.1 (#21)
    * Styling: Deleted deprecated buttons and updated export format

  * Sub-basins preprocessing

    * Implemented possibility to export to Talsim DB (#18)
    * Styling: Deleted deprecated buttons and updated export format

* Fixes

  * HRU Calculation

    * Clipping layers does not lead to errors if geometries are invalid
    * Updated land use parameter "RootDepthMonthlyPatternId" to "RootDepthAnnualPatternId" (#20)

  * Sub-basins preprocessing

    * LongestFlowPath now works correctly with QGIS 3.40 (fixes #22)

## \[1.6.2] - 2024-12-06

* Enhancement

  * ISRIC Soil Type Converter

    * Enhance Performance
    * Added possibility to resume from a previous conversion
    * Added option to run plugin without saving all layers

  * HRU Calculation

    * Dynamic text explanations now update based on user clicks
    * Improved the overview of different calculation steps for better clarity
    * Added a warning for sub-basin UI inputs that do not start with an "A"

* Fixes

  * HRU-Calculation

    * Sub-basins layer with complex geometries can now be handled (e.g., support for features with nested or multipart geometries)
    * Maximum size of polygons/HRUs is no longer restricted

  * Connect to Talsim DB

    * Fixes bug when opening this feature

  * Sub-basins preprocessing

    * Unique identifier field can have any name and field type now



## \[1.6.1] - 2024-10-31

* Enhancement

  * ISRIC Soil Type Converter: Order field names in final layer by soil horizon/layer

* Fixes

  * HRU-Calculation

    * Do not allow null-references in EFL-layer (e.g. soil ID is null)
    * Fix but do not delete complex geometries

## \[1.6.0] - 2024-10-25

* Add fourth functionality: ISRIC Soil Type Converter

  * Downloads soil data from ISRIC, converts it to soil types and bulk density class and combines this data for the area of interest in one layer
  * Created layer can be used as soil layer input to HRU Calculation

* Update HRU Calculation

  * Bug fix of invalid geometries that can arise when performing spatial operations
  * Enhancement: HRU Calculation can now process up to 6 soil horizons
  * Set bulk density class to 3 for missing values

## \[1.5.0] - 2024-08-23

* Add third functionality: Sub-basin preprocessing

  * Enable calculation of the longest flowpath for every sub-basin in input layer
  * Enable calculation of area, max/min height and average impervious areas for each sub-basin
  * ASCII-Export for .EZG-file

## \[1.4.3] - 2024-08-09

* Enhancements

  * Land use mapping has been improved to match the process of soil mapping (CSV upload is no longer required)
  * Slope calculation is now available for each HRU by uploading a DEM
  * HRU creation now allows for the omission of parameters, requiring only a unique identifier

## \[1.4.2] - 2024-07-18

* Minor Bug fix

  * Fixes ordering issue for ASCII outputs to ensure they are ordered by ID columns

## \[1.4.1] - 2024-07-12

* Bug fixes

  * Fixes issue for dissolve of final BOA and LNZ layer by only dissolving by land use/soil Features
  * Fixes issue of selecting wrong feature-ids for soil layer

    * Feature-ID of input soil layer is now used if user selects "Feature IDs of Soil Layer"

  * Fixes issue of docs as it was stated that ID is needed as input column name for land use ID rather than ID\_LNZ
  * Fixes issue that soil texture id was not in BOD-output

* Enhancement

  * Update Minimum QGIS-Version to 3.34

## \[1.4.0] - 2024-06-19

* Bug fixes

  * Fixes issues for invalid geometries in intersection process
  * Fixes issues for invalid geometries in editing overlapping features process
  * Fixes issues when deleting feature with multiple overlaps

* Overlaps with an area smaller than 10 m² are ignored and are not deleted by the plugin
* Add more user feedback for processes
* Add possibility to eliminate small polygons before intersection process

  * Soil/land use polygons below thresholds are removed when confirming the soil/land use feature mapping

* Enhance speed of editing overlapping features

## \[1.3.1] - 2024-05-15

* Bug fixes

  * Fixes issue where intersection did not work (Fixes [Issue #15](https://github.com/sydroconsult/QTalsim/issues/15)).
  * Fixes issue of handling of land uses without land use type (Fixes [Issue #14](https://github.com/sydroconsult/QTalsim/issues/14)).

* Change logic of elimination process during intersection

  * Sum of areas of all features with the same parameters is calculated and compared to minimum size and minimum share (rather than each spatial feature itself).

* Add user feedback for processes and also add visual indication ([Issue #12](https://github.com/sydroconsult/QTalsim/issues/12)).
* Change names of edited layers (add name of optional editing step: overlap/gaps removal) ([Issue #11](https://github.com/sydroconsult/QTalsim/issues/11)).
* Add possibility to choose intermediate results in layers drop-down menus ([Issue #10](https://github.com/sydroconsult/QTalsim/issues/10)).



## \[1.3.0] - 2024-04-17

* Bug fixes

  * Fixes issue where SVG symbols of SystemElement layer is not working (Fixes [Issue #5](https://github.com/sydroconsult/QTalsim/issues/5)).
  * Fixes issue where raster layers in QGIS project resulted in Python error (Fixes [Issue #3](https://github.com/sydroconsult/QTalsim/issues/3)).

* Add functionalities to "Connect to Talsim DB"

  * Add functionality to also edit transport-reaches and system elements.
  * Add functionality to update attributes.
  * Allow users to use external layers with different CRS than WGS84 (See [Issue #8](https://github.com/sydroconsult/QTalsim/issues/8)).
  * Checks for Talsim DB version (See [Issue #4](https://github.com/sydroconsult/QTalsim/issues/4)).
  * Dynamically updates lists of available layers (See [Issue #9](https://github.com/sydroconsult/QTalsim/issues/9)).
  * Layers are automatically updated after new/updated features were saved to DB (See [Issue #7](https://github.com/sydroconsult/QTalsim/issues/7)).

## \[1.2.0] - 2024-03-22

* Add second functionality to QTalsim: Connect to Talsim DB.

  * Enables users to connect directly to a Talsim SQLite Database.
  * Introduces the capability for users to edit sub-basins in QGIS and add new sub-basins to the DB.

## \[1.1.0] - 2024-02-21

* Add functionality to export ASCII-files suitable for Talsim. (.EFL, .LNZ, .BOA, .BOD)

## \[1.0.0] - 2024-02-01

* Initial release of the QTalsim QGIS plugin with core functionalities.
