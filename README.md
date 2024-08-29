# QTalsim

QTalsim is a QGIS plugin with two principal functionalities that enable the processing of spatial data suitable for [Talsim](https://www.talsim.de/docs/index.php?title=Hauptseite/en). 

The functionality "HRU Calculation" is designed to create hyrological response units (HRUs) suitable for Talsim. It processes three layer, including a catchment area layer, soil layer and land use layer. It clips the layers in accordance with the catchment area layer’s boundaries. The plugin then intersects those three layers and creates HRUs. Additionally, "HRU calculation" offers functionality to remove duplicate geometries, overlapping features and unwanted gaps.

The second functionality of QTalsim allows users to connect to a Talsim database, load system elements, and sub-basins. Moreover, users can edit existing sub-basins and import new sub-basins from an external polygon layer.

For detailed information, please refer to the [Full Documentation](https://sydroconsult.github.io/QTalsim/index.html).