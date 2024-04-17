# Changelog

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