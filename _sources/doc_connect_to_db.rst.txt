====================
Connect to Talsim DB
====================
   
   The second functionality of QTalsim allows users to connect to a Talsim Database, load system elements, sub-basins, outflows and transport reaches. 
   Moreover, users can edit all existing system-elements and the geometries of sub-basins and transport reaches. It is also possible to import sub-basins and transport reaches from external layers.
	
   |DB Connection Overview|
   
Connect to Talsim DB
--------------------
.. _getting-started:
	The first step involves connecting to a Talsim SQLite Database. By clicking "Select Database," you can browse and select the Talsim Database. 
	Note that all geometries must be in the CRS WGS84 (EPSG 4326).
	
	The next step requires selecting a scenario from the list and confirming this scenario by clicking "Confirm Scenario and load Layers".
	As a result, the System Elements, Outflows, TransportReaches Sub-basins are added to a layer group (named after the scenario) in the active QGIS-Project.
	The SystemElement-layer contains all system elements, located based on longitude and latitude attributes. The Sub-basins layer contains the polygons of all 
	sub-basins in the Talsim DB, while TransportReach contains all lines of the TransportReach as defined by the "Geometry"-column. These three layers can be edited. The outflows 
	depict the corresponding lines between the system elements and this layer can not be edited and edits of the Ouflows layer are not saved to the DB.
	
	At any stage, you can click the "Reconnect to DB and Reload Layers" button at the bottom to reconnect to the database, e.g., if you wish to inspect changes. 
	
Edit features of Talsim DB
--------------------------
.. _edit-existing:	

	The layers SystemElement, Sub-basins and TransportReach can be edited by the user. All edits/inserts/deletions made by the user are saved to the connected Talsim DB.
	As shown in the screenshot below, the user must select the layer to be edited in the layer group and then click the 'Toggle Editing' button to start the editing mode for this layer.
	Using the editing options of QGIS, the user is now able to make any changes to the geometries of these three layers
	(find further information `here <https://docs.qgis.org/3.34/en/docs/user_manual/working_with_vector/editing_geometry_attributes.html>`__). 	
	|Edit Sub-basins|
	
SystemElement
^^^^^^^^^^^^^
	The SystemElement-layer is a point layer that holds all SystemElements. Users can insert new elements, delete unwanted ones, or update existing elements. 
	To insert new elements, simply add a new point to the SystemElement-layer and then fill in the fields displayed in the prompt. 
	The most critical field to fill in is the 'Identifier' field. The first character of the identifier represents the ElementTypeCharacter of the system element (e.g., A for sub-basins).
	Therefore, it is essential for users to insert the correct ElementTypeCharacter here. The remainder of the 'Identifier' field serves as the ElementIdentifier. 
	The Id (SystemElementId) is automatically added by the plugin. All other fields are optional and can be left empty (='NULL').

	Another option is to delete system elements by removing the unwanted point feature.

	Users can also edit existing system elements by either modifying the fields in the attribute table or editing the point geometries. Editing the geometries updates the 
	'Latitude' and 'Longitude' columns to reflect the location as defined by the user. Please note that it is not possible to change the element type of system elements.

	Please note that it is important to save changes by clicking the 'Commit Changes' button. As a result, newly added features are inserted into the database, edited geometries of 
	existing features are updated in the database and deleted features are deleted from the DB. A log message (QTalsim-log) provides details on all updated/inserted features.
	

Sub-basins and TransportReach - WIP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
	Additionally to editing SystemElements directly, it is also possible to edit the geometries of transport reaches (lines) and sub-basins (polygons).  
	It is possible to update existing geometries/attributes, delete sub-basins, to insert geometries to existing system elements or to add new sub-basins/transport-reaches.
	
	When confirming the geometry of the new sub-basin, you must insert the identifier of the sub-basin into the field 'Identifier'. Optionally you can update any other fields. Only fields,
	that do not have Null-values are updated in the DB. 
	The field 'Geometry' is automatically filled with the WKT of the new geometry. Fields 'Latitude' and 'Longitude' are automatically filled with the coordinates of the sub-basin's center. 
	
	Once you have finished editing existing polygons and/or inserting all new sub-basins, it is again important to save the edits 
	by clicking the 'Commit Changes' button. 
	
	Another feature provided is the option to update the coordinates of sub-basins to the center of the sub-basins (button "Optional: Update Coordinates to Center of Sub-basins"). 
	Clicking this button calculates the centroid of all sub-basins, and updates all coordinates (columns 'Latitude' and 'Longitude') with the centroid's coordinates.
	
External Sub-basins Layer 
--------------------------
.. _external-layer:	

	An additional feature allows for adding an external polygon layer to include sub-basin geometries into existing sub-basins or to add new sub-basins to the database.
	First, you must select a polygon layer from the list. This layer must contain a Unique Identifier field with the 'ElementTypeCharacter' and the 'ElementIdentifier' (e.g., AA001).
	Select this field from the list, and you can optionally also select a field containing the name of the sub-basin. 
	When selecting a name-field the content is added to the feature's 'Name'-field in the DB. When selecting a name field, the content is added to the feature's 'Name' field in the database. 
	If you are updating existing features, you can update the point coordinates by selecting the corresponding checkbox.
	
	By clicking 'Save New/Updated Features in DB,' all new features or features with updated geometry are saved in the database. By clicking 'Optional: View updated/new Features in Layer' a new
	layer with the updated/inserted features is added to the layer group. 
	Again, the information about the updated/inserted features is logged to the QTalsim-log.
	
	|External layer|
	
.. |DB Connection Overview| image:: qtalsim_screenshots/db_connectionOverview.png
.. |Edit Sub-basins| image:: qtalsim_screenshots/db_editSubBasins.png
.. |External layer| image:: qtalsim_screenshots/db_externalLayer.png



