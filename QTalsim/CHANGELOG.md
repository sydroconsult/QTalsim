# Changelog

## [1.4.1] - 2024-07-12
- Bug fixes
  - Fixes issue for dissolve of final BOA and LNZ layer by only dissolving by land use/soil Features
  - Fixes issue of selecting wrong feature-ids for soil layer
    - Feature-ID of input soil layer is now used if user selects "Feature IDs of Soil Layer"
  - Fixes issue of docs as it was stated that ID is needed as input column name for land use ID rather than ID_LNZ
  - Fixes issue that soil texture id was not in BOD-output
- Enhancement
  - Update Minimum QGIS-Version to 3.34

## [1.4.0] - 2024-06-19
- Bug fixes
  - Fixes issues for invalid geometries in intersection process
  - Fixes issues for invalid geometries in editing overlapping features process
  - Fixes issues when deleting feature with multiple overlaps
- Overlaps with an area smaller than 10 m² are ignored and are not deleted by the plugin
- Add more user feedback for processes
- Add possibility to eliminate small polygons before intersection process
  - Soil/land use polygons below thresholds are removed when confirming the soil/land use feature mapping
- Enhance speed of editing overlapping features

## [1.3.1] - 2024-05-15
- Bug fixes
  - Fixes issue where intersection did not work (Fixes [Issue #15](https://github.com/sydroconsult/QTalsim/issues/15)).
  - Fixes issue of handling of land uses without land use type (Fixes [Issue #14](https://github.com/sydroconsult/QTalsim/issues/14)).
- Change logic of elimination process during intersection
  - Sum of areas of all features with the same parameters is calculated and compared to minimum size and minimum share (rather than each spatial feature itself).
- Add user feedback for processes and also add visual indication ([Issue #12](https://github.com/sydroconsult/QTalsim/issues/12)).
- Change names of edited layers (add name of optional editing step: overlap/gaps removal) ([Issue #11](https://github.com/sydroconsult/QTalsim/issues/11)).
- Add possibility to choose intermediate results in layers drop-down menus ([Issue #10](https://github.com/sydroconsult/QTalsim/issues/10)).



## [1.3.0] - 2024-04-17
- Bug fixes
  - Fixes issue where SVG symbols of SystemElement layer is not working (Fixes [Issue #5](https://github.com/sydroconsult/QTalsim/issues/5)).
  - Fixes issue where raster layers in QGIS project resulted in Python error (Fixes [Issue #3](https://github.com/sydroconsult/QTalsim/issues/3)).
- Add functionalities to "Connect to Talsim DB"
  - Add functionality to also edit transport-reaches and system elements.
  - Add functionality to update attributes.
  - Allow users to use external layers with different CRS than WGS84 (See [Issue #8](https://github.com/sydroconsult/QTalsim/issues/8)).
  - Checks for Talsim DB version (See [Issue #4](https://github.com/sydroconsult/QTalsim/issues/4)).
  - Dynamically updates lists of available layers (See [Issue #9](https://github.com/sydroconsult/QTalsim/issues/9)).
  - Layers are automatically updated after new/updated features were saved to DB (See [Issue #7](https://github.com/sydroconsult/QTalsim/issues/7)).

## [1.2.0] - 2024-03-22
- Add second functionality to QTalsim: Connect to Talsim DB.
  - Enables users to connect directly to a Talsim SQLite Database.
  - Introduces the capability for users to edit sub-basins in QGIS and add new sub-basins to the DB.

## [1.1.0] - 2024-02-21
- Add functionality to export ASCII-files suitable for Talsim. (.EFL, .LNZ, .BOA, .BOD)

## [1.0.0] - 2024-02-01
- Initial release of the QTalsim QGIS plugin with core functionalities.