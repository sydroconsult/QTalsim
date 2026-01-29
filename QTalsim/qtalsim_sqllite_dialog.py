import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog, QDialogButtonBox, QMessageBox
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis, QgsPointXY, QgsPoint, QgsFields, QgsLayerTreeLayer, QgsWkbTypes, QgsMapLayer, QgsLayerTreeGroup, QgsMapLayerProxyModel
from qgis.PyQt.QtCore import QVariant, pyqtSignal, QTimer
from qgis.gui import QgsMessageBar

import sqlite3
import webbrowser
import sys
import processing
import xml.etree.ElementTree as ET

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qtalsim_sqllite.ui'))

class SQLConnectDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, mainPluginInstance, parent=None):
        """Constructor."""
        super(SQLConnectDialog, self).__init__(parent)
        self.iface = iface
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.mainPlugin = mainPluginInstance
        self.initialize_parameters()
        self.finalButtonBox.button(QDialogButtonBox.Help).setText('Help')

    def initialize_parameters(self):
        #Clear from previous runs
        
        self.comboxDBScenarios.clear()
        self.talsimDBPath.clear()
        self.comboboxesSubBasins = [self.comboboxFieldName, self.comboboxFieldDescription, self.comboboxFieldRotation, 
                                    self.comboboxFieldArea, self.comboboxFieldImperviousness, self.comboboxFieldMaxHeight, 
                                    self.comboboxFieldMinHeight, self.comboboxFieldFlowLength]
        self.comboboxesTransportReaches = [self.comboboxFieldTRName, self.comboboxFieldTRDescription,
                                            self.comboboxFieldTRRotation, self.comboboxFieldTRLength]

        self.comboboxesSystemLogic = [
            self.comboboxUISystemLogic,
            self.comboboxDS1, 
            self.comboboxDS2, 
            self.comboboxDS3
        ]

        for box in self.comboboxesSubBasins:
            box.clear()
        
        for box in self.comboboxesTransportReaches:
            box.clear()

        for box in self.comboboxesSystemLogic:
            box.clear()

        for box in self.comboboxesSystemLogic:  
            if box != self.comboboxUISystemLogic:
                box.setAllowEmptyFieldName(True)
            box.setLayer(self.maplayerComboboxSystemLogic.currentLayer())     
        self.maplayerComboboxSystemLogic.layerChanged.connect(self.on_system_logic_layer_changed)

        self.comboboxPolygonLayer.clear()
        self.comboboxUIFieldPolygon.clear()
        self.checkboxUpdateCoordinates.setChecked(False)

        self.comboboxTransportReachLayer.clear()
        self.comboboxUIFieldTransportReach.clear()
        self.checkboxUpdateCoordinatesTransportReach.setChecked(False)
        #Parameter initialization
        self.noLayerSelected = 'No Layer selected'
        self.geometryFieldName = 'Geometry' 
        self.updateFieldName = 'Updated'
        self.layerGroup = None

        self.maplayerComboboxSystemLogic.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.maplayerComboboxSystemLogic.setAllowEmptyLayer(True, self.noLayerSelected)
        self.maplayerComboboxSystemLogic.setLayer(None)
        #Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.connectButtontoFunction(self.finalButtonBox.button(QDialogButtonBox.Help), self.openDocumentation)
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab
        self.connectButtontoFunction(self.onSelectDB, self.selectDB)
        self.comboxDBScenarios.currentIndexChanged.connect(self.on_scenario_change)
        self.comboboxUIFieldPolygon.clear()
        self.connectButtontoFunction(self.onCreateSubBasinsLayer, self.createLayers)
        self.connectButtontoFunction(self.onUpdateCoordinatesToCenter, self.updateCoordinatesSystemElements)
        #self.connectButtontoFunction(self.onViewUpdatedFeatures, self.loadUpdateLayer)

        self.connectButtontoFunction(self.onLoadExternalSubBasinsinDB, self.updateFromExternalSubBasinsLayer) #self.loadUpdatedFeaturesinDB
        self.connectButtontoFunction(self.onLoadExternalTransportReachinDB, self.updateFromExternalTransportReachLayer)
        self.connectButtontoFunction(self.onLoadExternalOutflowsinDB, self.updateOutflowsFromExternalLayer)
        self.connectButtontoFunction(self.onReconnectToDB, self.reconnectTriggeredByButton)

        self.root = QgsProject.instance().layerTreeRoot()
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers
        self.feedback = self.mainPlugin.CustomFeedback(self.log_to_qtalsim_tab)
        
        #External Layers Function
        QgsProject.instance().layersAdded.connect(self.layersAddedHandler)
        QgsProject.instance().layersRemoved.connect(self.layersAddedHandler)
       
        #External Sub Basins
        self.fillPolygonsCombobox() #Fill the combobox with all polygon layers

        #External TransportReach Layer
        self.fillTransportReachCombobox() #Fill the combobox with all line layers
        
        #Options for inserting/updating polygons
        #CHANGE TO 4326!!!!
        self.epsg = 4326 #25832
        self.updateOption1 = 'Insert Geometries only'
        self.updateOption2 = 'Insert Geometries & Update Coordinates'
        self.updateOption3 = 'Insert new Elements'
        self.updateOption4 = 'Update existing Elements'
        self.updateOption5 = 'Update existing Elements and Coordinates'
        self.updatedPolygonFeatures = []

        self.mappingElementTypeTableName = {'A': 'SubBasin', 'E': 'PointSource', 'G': 'Groundwater', 'S': 'TransportReach', 
                                'T': 'Storage', 'U':'Consumer', 'V': 'Diversion', 'Z': 'SystemOutlet'}
        self.mappingElementType = {'A': '2', 'E': '6', 'G': '11', 'S': '3', 
                                 'T': '10', 'U':'8', 'V': '7', 'Z': '0'}
        
    def openDocumentation(self):
        webbrowser.open('https://sydroconsult.github.io/QTalsim/doc_connect_to_db.html')

    def safeConnect(self, signal: pyqtSignal, slot):
        '''
        Safely connects a signal to a slot by first disconnecting existing connections.
        '''

        try:
            signal.disconnect(slot)
        except TypeError:
            # If the disconnect fails, it means there was no connection, which is fine.
            pass

        # Connect the signal to the slot.
        signal.connect(slot)

    def selectDB(self):
        '''
            Prompt for user to select DB and then connect to DB and select Scenarios
        '''
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.file_path_db = None
        try:
            self.file_path_db, _ = QFileDialog.getOpenFileName(self, "Select Talsim Database", "", "Databases (*.db);;All Files (*)", options=options)
            if self.file_path_db:
                self.talsimDBPath.setText(self.file_path_db)
        except Exception as e:
            self.log_to_qtalsim_tab(e,Qgis.Critical)

        try:
            self.conn = sqlite3.connect(self.file_path_db)
            self.cur = self.conn.cursor()
            sql_check_version = "SELECT MigrationId FROM __EFMigrationsHistory ORDER BY MigrationId DESC LIMIT 1;"
            self.cur.execute(sql_check_version)
            self.migrationId = self.cur.fetchall()[0][0]
            
            if self.migrationId[:8] < '20251201':  # Check version of Talsim DB
                message = f"Talsim DB with date {self.migrationId[:8]} is too old. Please use a more recent version."
                raise Exception(message)
            elif self.migrationId[:8] > '20251201':
                self.log_to_qtalsim_tab(f"Talsim DB with date {self.migrationId[:8]} is newer than the tested version.", Qgis.Warning)

            sql_query = "SELECT Name, Id FROM Scenario;"
            self.cur.execute(sql_query)
            self.scenariosAvailable = self.cur.fetchall()
            self.comboxDBScenarios.clear() #clear combobox EZG from previous runs
            self.comboxDBScenarios.addItems([f"{scenario[0]} (Id: {scenario[1]})" for scenario in self.scenariosAvailable])
        except sqlite3.Error as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    def on_scenario_change(self):
        '''
            Whenever the Scenario is changed by the user (in the corresponding combobox)
        '''
        try:
            #scenarioCombo = self.comboxDBScenarios.currentText()
            self.reconnectDatabase()
            scenarioComboId = self.comboxDBScenarios.currentIndex()
            self.scenarioName = self.scenariosAvailable[scenarioComboId][0]
            #scenarioName = scenarioCombo.split(" (", 1)[0]
            self.scenarioId = self.scenariosAvailable[scenarioComboId][1]
            sql_query = f"SELECT Distinct ElementTypeCharacter FROM SystemElement WHERE scenarioId = {self.scenarioId}"
            self.cur.execute(sql_query)
            self.elementTypes = self.cur.fetchall()
            #self.comboboxElementType.addItems([elementType[0] for elementType in self.elementTypes])

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    def block_editing(self):
        '''
            Block editing (for layer Outflows).
        '''
        if self.line_layer.isEditable():
            self.line_layer.rollBack()  # Discard changes and stop editing
            self.log_to_qtalsim_tab("Editing blocked for this layer.", Qgis.Info)

    def getAllLineLayers(self, root):
        '''
            Load all Layers
        '''
        layers = []
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                # If the child is a group, recursively get layers from this group
                layers.extend(self.getAllLineLayers(child))
            elif isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if layer and layer.type() == QgsMapLayer.VectorLayer:
                    # If the child is a layer, add it to the list
                    if layer.geometryType() == QgsWkbTypes.LineGeometry:
                        layers.append(layer)
        return layers
    
    def layersAddedHandler(self):
        '''
            QTimer is needed to ensure that added layers are correctly added to the comboboxes.
        '''
        QTimer.singleShot(100, self.fillTransportReachCombobox)
        QTimer.singleShot(100, self.fillPolygonsCombobox)

    def fillPolygonsCombobox(self):
        '''
            Fills the combobox of external sub-basins with all polygon layers in the project.        
        '''
        #Get Layers
        polygonLayers, _ = self.getAllLayers(QgsProject.instance().layerTreeRoot())

        self.comboboxPolygonLayer.clear() #clear combobox EZG from previous runs
        
        self.comboboxPolygonLayer.addItem(self.noLayerSelected)
        self.comboboxPolygonLayer.addItems([layer.name() for layer in polygonLayers])

        self.safeConnect(self.comboboxPolygonLayer.currentIndexChanged, self.on_polygon_layer_changed) #Refill the other comboboxes whenever user selects different layer

    def fillTransportReachCombobox(self):
        '''
            Fills the combobox of external transportreaches with all line layers in the project.        
        '''
        lineLayers = self.getAllLineLayers(QgsProject.instance().layerTreeRoot())
        self.comboboxTransportReachLayer.clear() #clear combobox EZG from previous runs
        
        self.comboboxTransportReachLayer.addItems([self.noLayerSelected])
        self.comboboxTransportReachLayer.addItems([layer.name() for layer in lineLayers])
        self.safeConnect(self.comboboxTransportReachLayer.currentIndexChanged, self.on_transport_reach_layer_changed) #Refill the other comboboxes whenever user selects different layer
    
    def changeSymbolsSymbology(self, pathSymbology, svg_base_path):  
        tree = ET.parse(pathSymbology)
        root = tree.getroot()
        for svg_option in root.findall(".//layer[@class='SvgMarker']/Option/Option[@name='name']"):
            old_path = svg_option.get('value')  # Get the current (old) SVG path
            filename = os.path.basename(old_path)  # Extract the filename for simplicity
            new_path = os.path.join(svg_base_path, filename)
            svg_option.set('value', new_path)

        modified_qml_path = pathSymbology
        tree.write(modified_qml_path)

    def createLayers(self):
        '''
            Creates all Input Layers.
        '''
        if self.layerGroup:
            self.root.removeChildNode(self.layerGroup)
        self.reconnectDatabase()
        try:
            sql_query = f'''SELECT Id
                                ,ElementTypeCharacter || ElementIdentifier AS Identifier
                                ,Name
                                ,Description
                                ,Longitude
                                ,Latitude
                                ,Rotation
                                ,Outflow1
                                ,Outflow2
                                ,Outflow3
                                ,Geometry
                            FROM SystemElement
                            WHERE scenarioId = {self.scenarioId} 
                        '''
            #AND ElementTypeCharacter = '{self.elementTypeCharacter}'
            self.cur.execute(sql_query)

            columns = [description[0] for description in self.cur.description]
            lat_index = columns.index('Latitude')
            lon_index = columns.index('Longitude')
            self.systemElementData = self.cur.fetchall()

            self.elementsPointLayer = QgsVectorLayer(f"Point?crs=epsg:{self.epsg}", "SystemElements", "memory") #Qgis Layer with sub basin points

            pr = self.elementsPointLayer.dataProvider()
            
            fields = QgsFields()
            for i, column in enumerate(columns):
                fields.append(QgsField(column, QVariant.String))
            pr.addAttributes(fields)
            self.elementsPointLayer.updateFields()

            #Start editing the point layer
            self.elementsPointLayer.startEditing()
            for row in self.systemElementData:
                [x for x in row]
                lat = row[lat_index]
                lon = row[lon_index]
                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                fet.setAttributes(list(row))
                pr.addFeatures([fet])
            
            self.elementsPointLayer.updateExtents()
            self.elementsPointLayer.commitChanges()

            #Symbology of point layer
            current_path = os.path.dirname(os.path.abspath(__file__))
            pathSymbology = os.path.join(current_path, "symbology", "ElementTypes.qml")
            svg_base_path = os.path.join(current_path, "symbology")

            self.changeSymbolsSymbology(pathSymbology, svg_base_path)
            
            #self.adjust_symbology_paths(self.elementsPointLayer, pathSymbology, svg_base_path)
            self.elementsPointLayer.loadNamedStyle(pathSymbology)
            self.elementsPointLayer.triggerRepaint()

            #Create LineLayer for Outflows
            self.line_layer = QgsVectorLayer(f"MultiLineString?crs=epsg:{self.epsg}", "Outflows", "memory")
            pr = self.line_layer.dataProvider()

            fields = QgsFields()
            fields.append(QgsField("start_id", QVariant.Int))
            fields.append(QgsField("end_id", QVariant.Int))
            pr.addAttributes(fields)
            self.line_layer.updateFields()

            # Dictionary to map Id to feature for quick lookup
            id_to_feature = {feature['Id']: feature for feature in self.elementsPointLayer.getFeatures()}
            for feature in self.elementsPointLayer.getFeatures():
                for outflow_column in ['Outflow1', 'Outflow2', 'Outflow3']:
                    outflow_id = feature[outflow_column]
                    if outflow_id is not 'NULL' and outflow_id in id_to_feature:
                        start_feature = feature
                        end_feature = id_to_feature[outflow_id]
                        
                        # Extract start and end points
                        start_point = start_feature.geometry().asPoint()
                        end_point = end_feature.geometry().asPoint()
                        
                        # Create a line feature
                        line = QgsFeature(fields)
                        line.setGeometry(QgsGeometry.fromPolyline([QgsPoint(start_point), QgsPoint(end_point)]))
                        
                        # Set attribute values (optional)
                        line.setAttribute("start_id", start_feature['Id'])
                        line.setAttribute("end_id", end_feature['Id'])
                        # Add the line feature to the layer
                        pr.addFeature(line)
            self.line_layer.updateExtents()
            
            #Add Layer-Group
            group_name = f"{self.scenarioName}"
            self.layerGroup = self.root.insertGroup(0, group_name)
            #self.CustomDockWidget.layerGroup(self.layerGroup)
            
            #Point Layer
            self.elementsPointLayer.setName("SystemElement")
            self.elementsPointLayerTree = QgsLayerTreeLayer(self.elementsPointLayer)
            QgsProject.instance().addMapLayer(self.elementsPointLayer, False)
            self.layerGroup.addChildNode(self.elementsPointLayerTree)

            #Line Layer
            current_path = os.path.dirname(os.path.abspath(__file__))
            pathSymbology = os.path.join(current_path, "symbology", "Outflows.qml")
            self.line_layer.loadNamedStyle(pathSymbology)
            self.line_layer.triggerRepaint()

            self.line_layer.editingStarted.connect(self.block_editing) #editing this layer should not be possible

            QgsProject.instance().addMapLayer(self.line_layer, False)
            line_layer_tree = QgsLayerTreeLayer(self.line_layer)
            self.layerGroup.addChildNode(line_layer_tree)
            
            self.addPolygonsSubBasins() #Add SubBasins-Polygons-Layer
            self.addLinesTransportReach() #Add TransportReach-Line-Layer

            #Get the column names of SystemElement Table
            sql_query = 'SELECT * FROM SystemElement'
            self.cur.execute(sql_query)
            self.columnsSystemElement = [description[0] for description in self.cur.description]

            #Track editing status
            #SystemElements
            self.elementsPointLayer.editingStarted.connect(lambda: self.on_editing_started(self.elementsPointLayer))
            self.elementsPointLayer.featureAdded.connect(self.on_change_made)
            self.elementsPointLayer.featureDeleted.connect(self.on_change_made)
            self.elementsPointLayer.attributeValueChanged.connect(self.on_change_made)
            self.elementsPointLayer.geometryChanged.connect(self.on_change_made)
            self.elementsPointLayer.beforeCommitChanges.connect(lambda: self.on_changes_committed(self.elementsPointLayer))
            self.elementsPointLayer.afterCommitChanges.connect(self.reloadLayersAfterCommit)

            #Sub-basins 
            self.subBasinsLayer.editingStarted.connect(lambda: self.on_editing_started(self.subBasinsLayer))
            self.subBasinsLayer.featureAdded.connect(self.on_change_made)
            self.subBasinsLayer.featureDeleted.connect(self.on_change_made)
            self.subBasinsLayer.attributeValueChanged.connect(self.on_change_made)
            self.subBasinsLayer.geometryChanged.connect(self.on_change_made)
            self.subBasinsLayer.beforeCommitChanges.connect(lambda: self.on_changes_committed(self.subBasinsLayer))
            self.subBasinsLayer.afterCommitChanges.connect(self.reloadLayersAfterCommit)

            #TransportReach
            self.transportReachLayer.editingStarted.connect(lambda: self.on_editing_started(self.transportReachLayer))
            self.transportReachLayer.featureAdded.connect(self.on_change_made)
            self.transportReachLayer.featureDeleted.connect(self.on_change_made)
            self.transportReachLayer.attributeValueChanged.connect(self.on_change_made)
            self.transportReachLayer.geometryChanged.connect(self.on_change_made)
            self.transportReachLayer.beforeCommitChanges.connect(lambda: self.on_changes_committed(self.transportReachLayer))
            self.transportReachLayer.afterCommitChanges.connect(self.reloadLayersAfterCommit)

            self.log_to_qtalsim_tab(f"SystemElements, Outflows and Sub-basins are now available in the project. You can now edit the Sub-basins and SystemElements.", Qgis.Info)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Warning)

    def reloadLayersAfterCommit(self):
        # QTimer.singleShot(delay in milliseconds, function to call)
        QTimer.singleShot(100, self.reconnectTriggeredByButton)

    def addPolygonsSubBasins(self):
        '''
            Add the Sub-basins
        '''
        sql_query = f'''SELECT SystemElementId
                        ,ElementTypeCharacter || ElementIdentifier AS Identifier
                        ,Name
                        ,Area
                        ,Imperviousness
                        ,MaxHeight
                        ,MinHeight
                        ,FlowLength
                        ,Geometry
                        
                        FROM SystemElement se

                        JOIN SubBasin sb ON se.Id = sb.SystemElementId

                        WHERE scenarioId = {self.scenarioId} 
                        AND Geometry IS NOT NULL
                    '''
        
        self.cur.execute(sql_query)

        self.subBasinData = self.cur.fetchall()
        self.subBasinsLayer = QgsVectorLayer(f"MultiPolygon?crs={self.elementsPointLayer.crs().authid()}", "WKT Polygons", "memory")
        dp = self.subBasinsLayer.dataProvider()

        columns = [description[0] for description in self.cur.description]
        fields = QgsFields()
        for i, column in enumerate(columns):
            fields.append(QgsField(column, QVariant.String))
        dp.addAttributes(fields)
        self.subBasinsLayer.updateFields()

        geometry_index = columns.index(self.geometryFieldName)
        #Start editing the point layer
        self.subBasinsLayer.startEditing()
        for row in self.subBasinData:
            fet = QgsFeature()
            fet.setAttributes(list(row))
            if str(row[geometry_index]).strip().upper() != 'NULL':
                wkt_string = str(row[geometry_index])    
                geom = QgsGeometry.fromWkt(wkt_string)
                fet.setGeometry(geom)
                dp.addFeatures([fet]) 
        
        self.subBasinsLayer.updateExtents()
        self.subBasinsLayer.commitChanges()
        
        current_path = os.path.dirname(os.path.abspath(__file__))
        pathSymbology = os.path.join(current_path, "symbology", "SubBasins.qml")
        self.subBasinsLayer.loadNamedStyle(pathSymbology) #if it does not work add flag True
        self.subBasinsLayer.triggerRepaint()
        
        self.subBasinsLayer.setName(f"Sub-basins")
        self.elementsPolygonLayerTree = QgsLayerTreeLayer(self.subBasinsLayer)
        QgsProject.instance().addMapLayer(self.subBasinsLayer, False)
        self.layerGroup.addChildNode(self.elementsPolygonLayerTree)

    def addLinesTransportReach(self):
        sql_query = f'''SELECT SystemElementId
                        ,ElementTypeCharacter || ElementIdentifier AS Identifier
                        ,Name
                        ,Length
                        ,Geometry
                        
                        FROM SystemElement se

                        JOIN TransportReach tr ON se.Id = tr.SystemElementId

                        WHERE scenarioId = {self.scenarioId} 
                        AND Geometry IS NOT NULL
                    '''
        self.cur.execute(sql_query)

        self.transportReachData = self.cur.fetchall()
        self.transportReachLayer = QgsVectorLayer(f"MultiLineString?crs=epsg:{self.epsg}", "TransportReach", "memory")
        
        dp = self.transportReachLayer.dataProvider()

        columns = [description[0] for description in self.cur.description]
        fields = QgsFields()
        for i, column in enumerate(columns):
            fields.append(QgsField(column, QVariant.String))
        dp.addAttributes(fields)
        self.transportReachLayer.updateFields()

        geometry_index = columns.index(self.geometryFieldName)
        #Start editing the point layer
        self.transportReachLayer.startEditing()
        for row in self.transportReachData:
            fet = QgsFeature()
            fet.setAttributes(list(row))
            if str(row[geometry_index]).strip().upper() != 'NULL':
                wkt_string = str(row[geometry_index])    
                geom = QgsGeometry.fromWkt(wkt_string)
                fet.setGeometry(geom)
                dp.addFeatures([fet]) 
        
        self.transportReachLayer.updateExtents()
        self.transportReachLayer.commitChanges()
        
        
        current_path = os.path.dirname(os.path.abspath(__file__))
        pathSymbology = os.path.join(current_path, "symbology", "TransportReach.qml")
        self.transportReachLayer.loadNamedStyle(pathSymbology)
        self.transportReachLayer.triggerRepaint()
        
        self.transportReachLayer.setName(f"TransportReach")
        self.elementsTransportReachLayerTree = QgsLayerTreeLayer(self.transportReachLayer)
        QgsProject.instance().addMapLayer(self.transportReachLayer, False)
        self.layerGroup.addChildNode(self.elementsTransportReachLayerTree)

    def on_editing_started(self, layer):
        self.reconnectDatabase()
        self.initialState = {}
        self.initialState = {feature.id(): (feature.geometry(), feature.attributes()) for feature in layer.getFeatures()}
        self.initialColumns = [field.name() for field in layer.fields()]

        self.changes_made = False
        self.log_to_qtalsim_tab(f"{layer.name()} is now in editing mode.", Qgis.Info)

    def on_changes_committed(self, layer):
        '''
            If editing-session of a layer was stopped.
        '''
        if self.changes_made:
            self.log_to_qtalsim_tab("Updating the edited features in DB.", Qgis.Info)
            self.compareStates(layer)
        else:
            self.log_to_qtalsim_tab("No changes were made.", Qgis.Info)

    def on_change_made(self):
        '''
            If change was made set the flag to True.
        '''
        self.changes_made = True

    def compareStates(self, layer):
        '''
            Compare the initial (before editing session) and current state (after editing session) to detect changes made in editing session.        
        '''
        #Get the current state
        currentState = {feature.id(): (feature.geometry(), feature.attributes()) for feature in layer.getFeatures()}
        
        #Get inserted and deleted features
        insertedFeaturesIds = set(currentState.keys()) - set(self.initialState.keys())
        deletedFeaturesIds = set(self.initialState) - set(currentState)
        modifiedFeatures = {}
        
        #Get modified Features by comparing initial with current state
        for featureId, (currentGeom, currentAttrs) in currentState.items():
            if featureId in self.initialState:
                initialGeom, initialAttrs = self.initialState[featureId]
                geomChanged = False
                if not currentGeom.equals(initialGeom) and not(currentGeom.isNull() and initialGeom.isNull()):
                    geomChanged = True
                changedAttributes = []
                for attrIndex, (currAttr, initAttr) in enumerate(zip(currentAttrs, initialAttrs)):
                    if currAttr != initAttr:
                        # If an attribute has changed, append its name to the list
                        fieldName = layer.fields()[attrIndex].name()
                        
                        #The user cannot update the 
                        if fieldName == 'Identifier':
                            if currAttr[0] != initAttr[0]:
                                currAttr = initAttr[0] + currAttr[1:]
                                if not layer.isEditable():
                                    layer.startEditing()
                                feature = layer.getFeature(featureId)
                                feature.setAttribute(feature.fieldNameIndex('Identifier'), currAttr)
                                layer.updateFeature(feature)
                                #layer.commitChanges()
                                self.log_to_qtalsim_tab(f"Changing the elementtype of feature {currAttr} is not possible. The elementtype of this feature remains {initAttr[0]}.", Qgis.Warning)

                            if currAttr != initAttr: #If current identifier and initial identifier are still not the same
                                changedAttributes.append(fieldName)
                        else:
                            changedAttributes.append(fieldName)
            
                # If geometry or any attributes have changed, record the changes
                if geomChanged or changedAttributes:
                    modifiedFeatures[featureId] = {
                        'geomChanged': geomChanged,
                        'changedAttributes': changedAttributes
                    }
            
        
        #Update modified features
        if modifiedFeatures:
            self.updateFeatures(layer, modifiedFeatures)
        sql_query = "SELECT ElementTypeCharacter || ElementIdentifier AS Identifier FROM SystemElement"
        self.cur.execute(sql_query)
        identifiersTuple = self.cur.fetchall()
        existingIdentifiers = [item[0] for item in identifiersTuple]

        #Inserted Features
        modifiedFeatures = {} #for features that were inserted
        if insertedFeaturesIds: #handle new features
            insertedFeatures = [layer.getFeature(fid) for fid in insertedFeaturesIds] #get the inserted features with all information
            for feature in insertedFeatures: #loop over inserted features
                if feature['Identifier'] in existingIdentifiers: #check if the feature already exists in DB (and has no Geometry)
                    changedAttributes = [column for column in feature.fields().names() if str(feature[column]).strip().upper() != 'NULL' and str(feature[column]) is not None]
                    modifiedFeatures[feature.id()] = {
                        'geomChanged': True,
                        'changedAttributes': changedAttributes}
                else: #if the feature does not exist, insert it in DB
                    self.insertNewElements(feature)
                    
        if modifiedFeatures:
            self.updateFeatures(layer, modifiedFeatures)
        
        if deletedFeaturesIds:
            for featureId in deletedFeaturesIds:
                _, featureData = self.initialState[featureId]

                if 'SystemElementId' in self.initialColumns:
                    systemElementIdIndex = self.initialColumns.index('SystemElementId')
                else:
                    systemElementIdIndex = self.initialColumns.index('Id')
                systemElementId = featureData[systemElementIdIndex]
                systemElementIdentifierIndex = self.initialColumns.index('Identifier')
                elementTypeCharacter = featureData[systemElementIdentifierIndex][0]
                self.deleteFeatures(elementTypeCharacter, systemElementId)

        #self.reconnectTriggeredByButton()
    
    def updateCoordinatesSystemElements(self):
        try:
            self.reconnectDatabase()
            updated_coordinates = []
            for feature in self.elementsPointLayer.getFeatures():
                wkt = str(feature[self.geometryFieldName])
                geometry = QgsGeometry.fromWkt(wkt)
                if geometry: #str(feature[self.geometryFieldName]).strip().upper()
                    centroid = geometry.centroid().asPoint() 
                    epsilon = 0.0000001 #Check if there is a difference between the centroid of the geometry(line, polygon) and the point object
                    if abs(float(feature['Latitude']) - centroid.y()) > epsilon or abs(float(feature['Longitude']) - centroid.x()) > epsilon:
                        updated_coordinates.append(feature['Id'])
                        self.updateCoordinates(feature, centroid.y(), centroid.x())
            if len(updated_coordinates) == 0:
                self.log_to_qtalsim_tab("No coordinates were updated.", Qgis.Info)
            self.reconnectTriggeredByButton()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    '''
        Edit DB by external layers    
    '''     
    def on_polygon_layer_changed(self):
        '''
            If user changes the external sub-basins layer, get the field names.
        '''
        selected_layer_name = self.comboboxPolygonLayer.currentText()
        if selected_layer_name != self.noLayerSelected and selected_layer_name is not None:
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            if layers:
                self.polygonLayer = layers[0]

                self.comboboxUIFieldPolygon.clear()
                self.fieldsPolygonLayer = [field.name() for field in self.polygonLayer.fields()]
                self.comboboxUIFieldPolygon.addItems([str(field) for field in self.fieldsPolygonLayer])

                
                self.fieldsPolygonLayer = [field.name() for field in self.polygonLayer.fields()]

                for field in self.comboboxesSubBasins:  
                    field.clear()
                    field.addItems(['No Field selected'])
                    field.addItems([str(field) for field in self.fieldsPolygonLayer])
        else:
            self.polygonLayer = None

    def on_transport_reach_layer_changed(self):
        '''
            If user changes the external transport-reach layer, get the field names.
        '''
        selected_layer_name = self.comboboxTransportReachLayer.currentText()
        if selected_layer_name != self.noLayerSelected and selected_layer_name is not None:
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            if layers:
                self.externalTransportReachLayer = layers[0]
                self.comboboxUIFieldTransportReach.clear()
                self.fieldsExternalTransportReachLayer = [field.name() for field in self.externalTransportReachLayer.fields()]
                self.comboboxUIFieldTransportReach.addItems([str(field) for field in self.fieldsExternalTransportReachLayer])

                self.fieldsExternalTransportReachLayer = [field.name() for field in self.externalTransportReachLayer.fields()]
                for field in self.comboboxesTransportReaches:  
                    field.clear()
                    field.addItems(['No Field selected'])
                    field.addItems([str(field) for field in self.fieldsExternalTransportReachLayer])        
        else:
            self.externalTransportReachLayer = None

    def on_system_logic_layer_changed(self):
        '''
            If user changes the external system-logic layer, get the field names.
        '''
        self.externalSystemLogicLayer = self.maplayerComboboxSystemLogic.currentLayer()
        if self.externalSystemLogicLayer and self.externalSystemLogicLayer.name() != self.noLayerSelected:
            self.comboboxUISystemLogic.clear()
            self.fieldsExternalSystemLogicLayer = [field.name() for field in self.externalSystemLogicLayer.fields()]
            for box in self.comboboxesSystemLogic:  
                if box != self.comboboxUISystemLogic:
                    box.setAllowEmptyFieldName(True)
                box.setLayer(self.maplayerComboboxSystemLogic.currentLayer())     
        else:
            self.externalSystemLogicLayer = None

    def updateFromExternalSubBasinsLayer(self):
        
        try:
            desiredEPSG = f"EPSG:{self.epsg}"
            
            #If the input layer does not have the required crs - reproject the layer
            if self.polygonLayer.crs().authid() != self.elementsPointLayer.crs().authid():
                self.log_to_qtalsim_tab(f"Input Layer has {self.polygonLayer.crs().authid()} while it should have {desiredEPSG}. Layer is reprojected to {desiredEPSG}. View results here: {self.polygonLayer.name()}_reprojected", Qgis.Info)
                params = {
                    'INPUT': self.polygonLayer,
                    'TARGET_CRS': desiredEPSG,
                    'OUTPUT': 'memory:'
                } 
                #Reproject the layer
                reprojectedLayerResult = processing.run("native:reprojectlayer", params, feedback=self.feedback)
                reprojectedLayer = reprojectedLayerResult['OUTPUT']
                reprojectedLayer.setName(f"{self.polygonLayer.name()}_reprojected")

                #QgsProject.instance().addMapLayer(reprojectedLayer, False)

                #Add the reprojected layer to the current project
                QgsProject.instance().addMapLayer(reprojectedLayer)

                #Update self.polygonLayer to reference the newly reprojected layer
                self.polygonLayer = reprojectedLayer
            self.uniqueIdentifierElements = None
            self.optionalFields = {}
            self.uniqueIdentifierElements = self.comboboxUIFieldPolygon.currentText()
            for combobox in self.comboboxesSubBasins:
                keyName = combobox.objectName().replace("comboboxField", "")
                currentText = combobox.currentText()
                self.optionalFields[keyName] = currentText
            self.elementTypeCharacter = 'A'
            checkbox = self.checkboxUpdateCoordinates.isChecked()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
            
        self.createUpdateLayer(self.polygonLayer,checkbox)

        self.reconnectTriggeredByButton()
    
    def updateFromExternalTransportReachLayer(self):

        #If the input layer does not have the required crs - reproject the layer
        try:
            desiredEPSG = f"EPSG:{self.epsg}"
            if self.externalTransportReachLayer.crs().authid() != self.elementsPointLayer.crs().authid():
                self.log_to_qtalsim_tab(f"Input Layer has {self.externalTransportReachLayer.crs().authid()} while it should have {desiredEPSG}. Layer is reprojected to {desiredEPSG}.", Qgis.Info)
                params = {
                    'INPUT': self.externalTransportReachLayer,
                    'TARGET_CRS': desiredEPSG,
                    'OUTPUT': 'memory:'
                } 
                #Reproject the layer
                reprojectedLayerResult = processing.run("native:reprojectlayer", params, feedback=self.feedback)
                reprojectedLayer = reprojectedLayerResult['OUTPUT']
                reprojectedLayer.setName(f"{self.externalTransportReachLayer.name()}_reprojected")
                #Add the reprojected layer to the current project
                QgsProject.instance().addMapLayer(reprojectedLayer)

                #Update the self.externalTransportReachLayer to reference the newly reprojected layer
                self.externalTransportReachLayer = reprojectedLayer
            self.uniqueIdentifierElements = None
            self.optionalFields = {}
            self.uniqueIdentifierElements = self.comboboxUIFieldTransportReach.currentText()
            self.elementTypeCharacter = 'S'

            for combobox in self.comboboxesTransportReaches:
                keyName = combobox.objectName().replace("comboboxFieldTR", "")
                self.optionalFields[keyName] = combobox.currentText()
            checkbox = self.checkboxUpdateCoordinatesTransportReach.isChecked()
            self.createUpdateLayer(self.externalTransportReachLayer, checkbox)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        

        self.reconnectTriggeredByButton()

    def updateOutflowsFromExternalLayer(self):
        #If the input layer does not have the required crs - reproject the layer
        try:
            #desiredEPSG = f"EPSG:{self.epsg}"
            self.externalSystemLogicLayer = self.maplayerComboboxSystemLogic.currentLayer()
            self.cur.execute("""
                SELECT Id, ElementIdentifier, ElementTypeCharacter FROM SystemElement 
                WHERE ScenarioId = ? AND (Outflow1 IS NOT NULL OR Outflow2 IS NOT NULL OR Outflow3 IS NOT NULL)
                
                UNION
                
                SELECT se.Id, se.ElementIdentifier, se.ElementTypeCharacter FROM SystemElement se 
                JOIN SubBasin sb ON se.Id = sb.SystemElementId
                WHERE se.ScenarioId = ? AND (
                    sb.QBaseflowOutletSystemElementId IS NOT NULL OR 
                    sb.QDeepBaseflowOutletSystemElementId IS NOT NULL OR 
                    sb.QDeepInterflowOutletSystemElementId IS NOT NULL OR 
                    sb.QInterflowOutletSystemElementId IS NOT NULL OR 
                    sb.QNaturalOutletSystemElementId IS NOT NULL OR 
                    sb.QUrbanOutletSystemElementId IS NOT NULL
                )
            """, (self.scenarioId, self.scenarioId, )) # Wichtig: scenarioId muss zweimal übergeben werden

            existing_outflows = self.cur.fetchall()
            if existing_outflows:
                #Ask user for confirmation to delete table entries
                outflow_strings = [f"{row[1]} ({row[2]})" for row in existing_outflows]
                display_list = outflow_strings[:20]
                outflow_summary = ", ".join(display_list)
                if len(outflow_strings) > 20:
                    outflow_summary += " ..."
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Existing Data Found")
                msg.setText(f"There are existing outflows for the following elements in scenario {self.scenarioId}:\n\n" +
                            outflow_summary +
                            "\n\nYou can only continue if all outflows are deleted.")
                msg.setInformativeText(f"Would you like to delete all outflows and reload the outflows from layer {self.externalSystemLogicLayer.name()}?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                response = msg.exec_()
                if response == QMessageBox.No:
                    self.log_to_qtalsim_tab("Operation cancelled by user.", Qgis.Info)
                    return
                else:
                    #Delete existing outflows
                    self.cur.execute("""
                        UPDATE SystemElement
                        SET Outflow1 = NULL, Outflow2 = NULL, Outflow3 = NULL
                        WHERE ScenarioId = ?
                    """, (self.scenarioId,))

                    self.cur.execute("""
                        UPDATE SubBasin
                        SET QBaseflowOutletSystemElementId = NULL,
                            QDeepBaseflowOutletSystemElementId = NULL,
                            QDeepInterflowOutletSystemElementId = NULL,
                            QInterflowOutletSystemElementId = NULL,
                            QNaturalOutletSystemElementId = NULL,
                            QUrbanOutletSystemElementId = NULL
                        WHERE SystemElementId IN (
                            SELECT Id FROM SystemElement WHERE ScenarioId = ?
                        )
                    """, (self.scenarioId,))

                    self.conn.commit()
                    self.log_to_qtalsim_tab(f"Existing outflows for scenario {self.scenarioId} have been deleted.", Qgis.Info)
                    self.reconnectDatabase()
            # Insert the outflows
            subbasin_system_logic_ui_field = self.comboboxUISystemLogic.currentField()
            idx1 = self.externalSystemLogicLayer.fields().indexOf(self.comboboxDS1.currentField())
            idx2 = self.externalSystemLogicLayer.fields().indexOf(self.comboboxDS2.currentField())
            idx3 = self.externalSystemLogicLayer.fields().indexOf(self.comboboxDS3.currentField())

            def get_se_id(outflow_val, scenario_id, cur):
                if not isinstance(outflow_val, str) or not outflow_val:
                    return None
                uiSystemLogic = outflow_val if isinstance(outflow_val, str) and outflow_val else None
                element_identifier = outflow_val[1:] if isinstance(outflow_val, str) and outflow_val else None # ElementIdentifier & Name
                key = outflow_val[0] if isinstance(outflow_val, str) and outflow_val else None
                cur.execute("""
                    SELECT Id FROM SystemElement 
                    WHERE ElementIdentifier = ? and ElementTypeCharacter = ? and ScenarioId = ?
                """, (element_identifier, key, scenario_id,))
                result = cur.fetchone()
                return result[0] if result else None 
            
            #self.conn = sqlite3.connect(self.file_path_db) # noch kontrollieren
            #self.cursor = self.conn.cursor()
            updates_to_run = []
            for feature in self.externalSystemLogicLayer.getFeatures():
                uiSystemLogic = feature[subbasin_system_logic_ui_field] if isinstance(feature[subbasin_system_logic_ui_field], str) and feature[subbasin_system_logic_ui_field] else None
                element_identifier = feature[subbasin_system_logic_ui_field][1:] if isinstance(feature[subbasin_system_logic_ui_field], str) and feature[subbasin_system_logic_ui_field] else None # ElementIdentifier & Name
                key = feature[subbasin_system_logic_ui_field][0] if isinstance(feature[subbasin_system_logic_ui_field], str) and feature[subbasin_system_logic_ui_field] else None
                self.cur.execute("""
                    SELECT Id FROM SystemElement 
                    WHERE ElementIdentifier = ? and ElementTypeCharacter = ? and ScenarioId = ?
                """, (element_identifier, key, self.scenarioId,))
                system_element_result = self.cur.fetchone()
                if not system_element_result: #if this systemelement does not exist
                    self.log_to_qtalsim_tab(f"Warning: No matching SystemElement found for SystemLogic ElementIdentifier: {uiSystemLogic}", Qgis.Warning)
                    continue
                system_element_id = system_element_result[0]
                outflow1 = feature[idx1] if idx1 != -1 else None
                outflow2 = feature[idx2] if idx2 != -1 else None
                outflow3 = feature[idx3] if idx3 != -1 else None
                id1 = get_se_id(outflow1, self.scenarioId, self.cur)
                id2 = get_se_id(outflow2, self.scenarioId, self.cur)
                id3 = get_se_id(outflow3, self.scenarioId, self.cur)
                updates_to_run.append((id1, id2, id3, system_element_id))
                
                self.cur.execute("""
                        UPDATE SystemElement
                        SET Outflow1 = ?, Outflow2 = ?, Outflow3 = ?
                        WHERE Id = ?
                    """, (id1, id2, id3, system_element_id,))
            if not updates_to_run:
                self.conn.commit()
                self.cur.executemany("""
                    UPDATE SystemElement
                    SET Outflow1 = ?, Outflow2 = ?, Outflow3 = ?
                    WHERE Id = ?
                """, updates_to_run)
            
            self.conn.commit()
            #self.reconnectDatabase()
            self.reconnectTriggeredByButton()
        except Exception as e:
            self.log_to_qtalsim_tab(f"An error occurred while updating Outflows from external SystemLogic layer: {e}", Qgis.Critical)
            
    def createUpdateLayer(self, layer, checkbox):
        '''
            Creates a layer that holds all features that will be edited/inserted in DB by a new external layer.
                (triggered in functions updateFromExternalTransportReachLayer and updateFromExternalSubBasinsLayer)
        '''
        #Create new layer to store updated features
        self.updatedElementsLayer = QgsVectorLayer(f"Point?crs={self.elementsPointLayer.crs().authid()}", "Updated Elements", "memory")

        fieldsPointLayer = self.elementsPointLayer.fields()
        fieldNames = ['Id', 'Identifier', self.geometryFieldName, 'Latitude', 'Longitude'] #Only add these fields from the systemelement-layer to the updated features
        fields_to_add = [field for field in fieldsPointLayer if field.name() in fieldNames]
        self.updatedElementsLayer.dataProvider().addAttributes(fields_to_add)
        self.updatedElementsLayer.updateFields()

        #Add fields from the Geometry-layer (Sub-basins or TransportReaches) if the user selected the specific field names
        fieldsExternalLayer = layer.fields()

        fields_to_add_geometry_layer = []
        for new_field_name, external_field_name in self.optionalFields.items():
            for field in fieldsExternalLayer:
                if field.name() == external_field_name:
                    # Create a new QgsField object with the new name but same type and properties
                    new_field = QgsField(new_field_name, field.type(), field.typeName(), field.length(), field.precision())
                    fields_to_add_geometry_layer.append(new_field)
                    break 
        
        if fields_to_add_geometry_layer:
            self.updatedElementsLayer.dataProvider().addAttributes(fields_to_add_geometry_layer)
            self.updatedElementsLayer.updateFields()

        dp = self.updatedElementsLayer.dataProvider()
        fieldNamesPointLayer = [field.name() for field in fields_to_add]
        if self.geometryFieldName not in fieldNamesPointLayer:
            dp.addAttributes([QgsField(self.geometryFieldName, QVariant.String)])

        fieldNamesUpdateLayer = [field.name() for field in self.updatedElementsLayer.fields()]
        if self.updateFieldName not in fieldNamesUpdateLayer:
            dp.addAttributes([QgsField(self.updateFieldName, QVariant.String)])
        self.updatedElementsLayer.updateFields()

        self.updatedElementsLayer.startEditing()
        point_index = {str(feature['Identifier']): feature for feature in self.elementsPointLayer.getFeatures()}
        
        '''
            Store Elements of external Polygons
        '''  
        try:
            #Index Geometry
            geometry_index = {feature[self.uniqueIdentifierElements]: feature.geometry().asWkt() for feature in layer.getFeatures()}
            self.updatedElements = {1: [], 2: [], 3: []}

            editedFeatures = []
            for point_feature in self.elementsPointLayer.getFeatures():
                if point_feature['Identifier'][0] == self.elementTypeCharacter:
                    join_value = str(point_feature['Identifier'])
                   
                    #Insert Polygons to SystemElements, where no polygon exists
                    if join_value in geometry_index and (self.geometryFieldName not in fieldNamesPointLayer or str(point_feature[self.geometryFieldName]).strip().upper() == 'NULL' or point_feature[self.geometryFieldName] is None):
                        update_feature = QgsFeature(self.updatedElementsLayer.fields())
                        update_feature.setAttributes(point_feature.attributes())
                        update_feature.setGeometry(point_feature.geometry())
                        self.updatedElementsLayer.dataProvider().addFeatures([update_feature])
                        update_feature[self.geometryFieldName] = str(geometry_index[join_value])
                        self.updatedElementsLayer.updateFeature(update_feature)
                        geometry = QgsGeometry.fromWkt(geometry_index[join_value])
                        if geometry.type() == QgsWkbTypes.PolygonGeometry and not geometry.contains(point_feature.geometry()):
                            self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {join_value} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning) 
                    
                    #Update existing polygons with external polygons
                    
                    elif join_value in geometry_index and point_feature[self.geometryFieldName] != geometry_index[join_value] and str(point_feature[self.geometryFieldName]).strip().upper() != 'NULL' and point_feature[self.geometryFieldName] is not None:
                        update_feature = QgsFeature(self.updatedElementsLayer.fields())
                        update_feature.setAttributes(point_feature.attributes())
                        update_feature.setGeometry(point_feature.geometry())

                        geom_field_index = self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName)

                        if geom_field_index != -1:
                            update_feature.setAttribute(geom_field_index, geometry_index[join_value])
                        self.updatedElementsLayer.dataProvider().addFeatures([update_feature])
                        editedFeatures.append(update_feature['Id'])
                        geometry = QgsGeometry.fromWkt(geometry_index[join_value])
                        if geometry.type() == QgsWkbTypes.PolygonGeometry and not geometry.contains(point_feature.geometry()):
                            self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {join_value} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning) 
                                            #Add the optional field's values
                            
            self.updatedElementsLayer.commitChanges()
            
            '''
                Edit Update-Layer
            '''
            self.updatedElementsLayer.startEditing()
            for update_feature in self.updatedElementsLayer.getFeatures():
                join_value = str(update_feature['Identifier'])
                field_index = self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName)
                self.updatedElementsLayer.changeAttributeValue(update_feature.id(), field_index, geometry_index[join_value])
                geometry = QgsGeometry.fromWkt(geometry_index[join_value])
                if checkbox:
                    #Change the coordinates of SystemElement
                    centroid = geometry.centroid().asPoint()
                    self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName('Longitude'), centroid.x())    
                    self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName('Latitude'), centroid.y())  
                    centroid_geometry = QgsGeometry.fromPointXY(centroid)
                    self.updatedElementsLayer.dataProvider().changeGeometryValues({update_feature.id(): centroid_geometry}) #Change the geometry of SystemElement
                    #self.updatedElements[2].append(join_value)
                    if update_feature['Id'] in editedFeatures:
                        self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption5)  
                    else:
                        self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption2)  
                else:
                    #Don't change coordinates, only insert new polygon/line
                    self.updatedElements[1].append(join_value)
                    self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption1)  
                
            self.updatedElementsLayer.commitChanges()
            
            #Adding new Polygons/System Elements
            self.updatedElementsLayer.startEditing()
            
            for geometry_feature in layer.getFeatures():
                join_value = geometry_feature[self.uniqueIdentifierElements]
                if join_value not in point_index:
                    new_feature = QgsFeature(self.updatedElementsLayer.fields())
                    centroid = geometry_feature.geometry().centroid().asPoint() 
                    centroid_geometry = QgsGeometry.fromPointXY(centroid)
                    new_feature.setGeometry(centroid_geometry)

                    new_feature[self.geometryFieldName] = geometry_feature.geometry().asWkt()
                    new_feature['Longitude'] = centroid.x()
                    new_feature['Latitude'] = centroid.y()
                    new_feature['Identifier'] = join_value
                    #new_feature['ElementTypeCharacter'] = join_value[0]

                    #Add optional field

                    new_feature[self.updateFieldName] = self.updateOption3

                    for talsimField, externalField in self.optionalFields.items():
                        if externalField != 'No Field selected': # and geometry_feature.geometry() == QgsWkbTypes.PolygonGeometry:
                            if talsimField in new_feature.fields().names() and externalField in geometry_feature.fields().names():
                                new_feature[talsimField] = geometry_feature[externalField]
                    self.updatedElementsLayer.dataProvider().addFeatures([new_feature])
                    self.updatedElements[3].append(join_value)
                else:
                    for talsimField, externalField in self.optionalFields.items():
                        if externalField != 'No Field selected': # and geometry_feature.geometry() == QgsWkbTypes.PolygonGeometry:
                            for update_feature in self.updatedElementsLayer.getFeatures('"Identifier" = \'{}\''.format(join_value)):
                                if talsimField in self.updatedElementsLayer.fields().names() and externalField in geometry_feature.fields().names():
                                    update_feature[talsimField] = geometry_feature[externalField]  
                                    self.updatedElementsLayer.updateFeature(update_feature)
            self.updatedElementsLayer.commitChanges()

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)


        self.loadUpdatedFeaturesinDB()

    def loadUpdateLayer(self):
        try:
            current_path = os.path.dirname(os.path.abspath(__file__))
            pathSymbology = os.path.join(current_path, "symbology", "UpdatedElements.qml")
            self.updatedElementsLayer.loadNamedStyle(pathSymbology)
            self.updatedElementsLayer.triggerRepaint()

            QgsProject.instance().addMapLayer(self.updatedElementsLayer, False)
            self.updatedElementsLayerTree = QgsLayerTreeLayer(self.updatedElementsLayer)
            self.layerGroup.addChildNode(self.updatedElementsLayerTree)
            self.log_to_qtalsim_tab(f"Added Layer with updated Features.", Qgis.Info)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    def reconnectTriggeredByButton(self):
        '''
            Reconnect to DB and reload Layers.
        '''
        self.reconnectDatabase()
        self.createLayers()
        self.log_to_qtalsim_tab("Reconnected with DB.", Qgis.Info)

    #Existing polygons überarbeiten
    def reconnectDatabase(self):
        try:
            self.conn.close()
            self.conn = sqlite3.connect(self.file_path_db)
            self.cur = self.conn.cursor()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    '''
        Functions to update elements in DB/insert new elements to DB
    '''

    def updateFeatures(self, layer, modifiedFeatures):
        self.reconnectDatabase()
        for featureId, changes in modifiedFeatures.items():
            feature = layer.getFeature(featureId)
            if 'SystemElementId' in feature.fields().names(): #get column where SystemElementId is stored
                id_field = 'SystemElementId'
            else:
                id_field = 'Id' 

            #First: If necessary update SystemElements Table
            update_params_systemelements = []
            sql_query = "UPDATE SystemElement SET "
            
            if changes['geomChanged'] and (feature.geometry().type() == QgsWkbTypes.PolygonGeometry or feature.geometry().type() == QgsWkbTypes.LineGeometry): #und feature ist polygon
                # Store this feature for later
                #Spatial containment check here?
                sql_query += f"{self.geometryFieldName} = ?, "
                wkt = feature.geometry().asWkt()
                update_params_systemelements.append(wkt)

            elif changes['geomChanged'] and feature.geometry().type() == QgsWkbTypes.PointGeometry: #und feature ist point
                sql_query += f"Latitude = ?, "
                lat = feature.geometry().asPoint().y()
                update_params_systemelements.append(lat)
                sql_query += f"Longitude = ?, "
                long = feature.geometry().asPoint().x()
                update_params_systemelements.append(long)
            
            for attrName in changes['changedAttributes']:
                if attrName in self.columnsSystemElement or attrName == 'Identifier':
                    if attrName == 'Identifier':
                            attr_value1 = str(feature[attrName])[0]
                            sql_query += f"ElementTypeCharacter = ?, "
                            update_params_systemelements.append(attr_value1)

                            attr_value2 = str(feature[attrName])[1:]
                            sql_query += f"ElementIdentifier = ?, "
                            update_params_systemelements.append(attr_value2)

                    else: #attrName == 'Name'
                        attr_value = feature[attrName]
                        sql_query += f"{attrName} = ?, "
                        update_params_systemelements.append(attr_value)
                    
            
            if len(update_params_systemelements) > 0:
                sql_query = sql_query.rstrip(", ") #Remove comma added above
                sql_query += " WHERE Id = ?;"
                if str(feature[id_field]).strip().upper() != 'NULL': #check if the systemelementid is null
                    update_params_systemelements.append(feature[id_field])
                else:
                    #SystemElementId is null (in the layer) for features where the feature exists in DB but does not have a polygon
                    # --> Get the SystemElementId from the DB
                    sql_get_systemelement_id = f'''
                                SELECT Id FROM SystemElement

                                WHERE ElementIdentifier = ?
                                AND ElementTypeCharacter = ?
                                AND ScenarioId = ?
                            '''
                    params = (feature['Identifier'][1:], feature['Identifier'][0], self.scenarioId)
                    self.cur.execute(sql_get_systemelement_id, params)
                    systemElementId = self.cur.fetchone()[0]
                    update_params_systemelements.append(systemElementId)
                self.cur.execute(sql_query, tuple(update_params_systemelements))
                self.conn.commit()
            #Identifier muss noch hinzugefügt werden, die Spalte gibt es so ja nicht (auch oben)
            #Edit features of other table (SubBasin)
            update_params = []
            
            elementTypeTableName = self.mappingElementTypeTableName.get(feature['Identifier'][0], "Unknown")
            sql_query = f'SELECT * FROM {elementTypeTableName}'
            self.cur.execute(sql_query)

            columns = [description[0] for description in self.cur.description]
            sql_query = f"UPDATE {elementTypeTableName} SET "
      
            #Loop over the changes and concatenate update-query
            for attrName in changes['changedAttributes']:
                if attrName in columns:
                    attr_value = feature[attrName]
                    sql_query += f"{attrName} = ?, "
                    update_params.append(attr_value)

            #Update the non-system-elements table (e.g. Sub-Basin)
            if len(update_params) > 0:
                sql_query = sql_query.rstrip(", ") #Remove comma added above
                sql_query += " WHERE SystemElementId = ?;"
                if str(feature[id_field]).strip().upper() != 'NULL': #check if the systemelementid is null
                    update_params.append(feature[id_field])
                else:
                    #SystemElementId is null (in the layer) for features where the feature exists in DB but does not have a polygon
                    # --> Get the SystemElementId from the DB
                    sql_get_systemelement_id = f'''
                                SELECT Id FROM SystemElement

                                WHERE ElementIdentifier = ?
                                AND ElementTypeCharacter = ?
                                AND ScenarioId = ?
                            '''
                    params = (feature['Identifier'][1:], feature['Identifier'][0], self.scenarioId)
                    self.cur.execute(sql_get_systemelement_id, params)
                    systemElementId = self.cur.fetchone()[0]
                    update_params.append(systemElementId)
                self.cur.execute(sql_query, tuple(update_params))
                self.conn.commit()
            self.log_to_qtalsim_tab(f"Feature {str(feature['Identifier'])} was updated in DB.",Qgis.Info)
            
    def insertNewElements(self, feature):
        '''
            Insert new Elements that haven't existed.
        '''
        try:
            self.reconnectDatabase()
            
            elementTypeTableName = self.mappingElementTypeTableName.get(feature['Identifier'][0], "Unknown")

            sql_query = f'SELECT * FROM {elementTypeTableName}'
            self.cur.execute(sql_query)
            columns = [description[0] for description in self.cur.description]

            #Get WKT of geometry
            if feature.geometry().type() == QgsWkbTypes.PolygonGeometry or feature.geometry().type() ==  QgsWkbTypes.LineGeometry: #Check geometry type
                wkt = feature.geometry().asWkt()
                centroid = feature.geometry().centroid().asPoint()
                lat = centroid.y()
                long = centroid.x()
            
            #If elements are added to SystemElements layer and the wkt is null 
            elif feature.geometry().type() == QgsWkbTypes.PointGeometry and str(feature[self.geometryFieldName]).strip().upper() == 'NULL': #if it is a point layer
                wkt = 'NULL'
                lat = feature.geometry().asPoint().y()
                long = feature.geometry().asPoint().x()
            
            #External layers (the UpdateLayer is a point layer)
            elif feature.geometry().type() == QgsWkbTypes.PointGeometry and str(feature[self.geometryFieldName]).strip().upper() != 'NULL':
                lat = feature['Latitude']
                long = feature['Longitude']
                wkt = feature[self.geometryFieldName]

            #Start SQL Query
            sql_query = "INSERT INTO SystemElement"
            sql_query += '('
            params = []
            additionalColumns = ['ScenarioId', 'ElementType', 'Latitude', 'Longitude', self.geometryFieldName]
            for column in feature.fields().names(): #loop over all columns of the feature to insert in DB
                if (column in self.columnsSystemElement or column == 'Identifier') and column not in additionalColumns and column != 'Id':
                    if column == 'Identifier': #Identifier has to split up in 2 columns
                        attr_value1 = str(feature[column])[0]
                        sql_query += f"ElementTypeCharacter, "
                        params.append(attr_value1)

                        attr_value2 = str(feature[column])[1:]
                        sql_query += "ElementIdentifier, "
                        params.append(attr_value2)
                    elif column == 'Rotation' and str(feature[column]).strip().upper() == 'NULL':
                        sql_query += f'{column}, '
                        params.append(0.0)
                    elif str(feature[column]).strip().upper() == 'NULL':
                        continue
                    else: #append all other columns, resp. their values
                        sql_query += f'{column}, '
                        params.append(feature[column])
            
            elementtype = self.mappingElementType.get(feature['Identifier'][0], "Unknown")
            #Add values to additional columns
            additionalValues = [self.scenarioId, elementtype, lat, long, wkt]
            sql_query += ", ".join(additionalColumns) + ") VALUES (" + ", ".join(["?"] * len(params + additionalValues)) + ")"
            params.extend(additionalValues)

            #Execute SQL statement
            self.cur.execute(sql_query, params)
            self.conn.commit()

            #Get SystemElementId
            self.reconnectDatabase()
            sql_query = f'''
                            SELECT Id FROM SystemElement

                            WHERE ElementIdentifier = '{feature['Identifier'][1:]}'
                            AND ElementTypeCharacter = '{feature['Identifier'][0]}'
                            AND ScenarioId = '{self.scenarioId}'
                        '''
            self.cur.execute(sql_query)
            feature_id_tuple = self.cur.fetchone()

            #Start Insert-Statement into SubBasin-Table
            paramsSubBasins = []

            sql_query = f'''
                            INSERT INTO {elementTypeTableName} 
                        '''
            sql_query += '(SystemElementId, '
            feature_id = feature_id_tuple[0]
            paramsSubBasins.append(feature_id)
            
            for column in feature.fields().names():
                #SystemElementId was added above, no null-features
                if column in columns and column != 'SystemElementId' and feature[column] is not None and str(feature[column]).strip().upper() != 'NULL':
                    sql_query += f"{column}, "
                    paramsSubBasins.append(feature[column])
            sql_query = sql_query.rstrip(', ') + ') VALUES (' + ', '.join(['?'] * len(paramsSubBasins)) + ')'

            self.cur.execute(sql_query, tuple(paramsSubBasins))
            self.conn.commit()
            self.log_to_qtalsim_tab(f"Feature {str(feature['Identifier'])} was inserted in DB.", Qgis.Info)
            self.reconnectDatabase()
            
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    def deleteFeatures(self, elementtypecharacter, systemElementId):
        '''
            Delete Features
        ''' 
        try:
            elementTypeTableName = self.mappingElementTypeTableName.get(elementtypecharacter, "Unknown")

            self.cur.execute("DELETE FROM SystemElement WHERE id = ?", (systemElementId,))
            self.conn.commit()
            if elementTypeTableName != "Unknown":
                self.cur.execute(f"DELETE FROM {elementTypeTableName} WHERE SystemElementId = ?", (systemElementId,))
                self.conn.commit()
            else:
                self.log_to_qtalsim_tab("Due to unknown ElementType, the element was only deleted from SystemElement Table.", Qgis.Warning)
            self.reconnectDatabase()
            self.log_to_qtalsim_tab(f"Feature with SystemElementId {systemElementId} was deleted", Qgis.Info)
        
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    def updateCoordinates(self, feature, y, x):
        '''
            Update only coordinates (lat, long) of features.
        '''
        self.reconnectDatabase()
        sql_query = f'''
                        UPDATE SystemElement
                        SET Longitude = ?, Latitude = ?
                        WHERE Id = ?;
                    '''
        params = (x, y, feature['Id'])
        self.cur.execute(sql_query, params)
        self.conn.commit()
        self.log_to_qtalsim_tab(f"Feature {str(feature['Identifier'])} was updated in DB.",Qgis.Info)
        self.reconnectDatabase()

    '''
        External Geometries
    '''
    def insertGeometriesToExistingFeatures(self, feature):
        '''
            Insert geometries to existing sub-basins/transportreaches.
        '''
        self.reconnectDatabase()

        update_params_systemelements = []
        sql_query = "UPDATE SystemElement SET "
        for attrName in feature.fields().names():
            if attrName in self.columnsSystemElement or attrName == 'Identifier':
                if attrName == 'Identifier':
                    attr_value1 = str(feature[attrName])[0]
                    sql_query += f"ElementTypeCharacter = ?, "
                    update_params_systemelements.append(attr_value1)

                    attr_value2 = str(feature[attrName])[1:]
                    sql_query += f"ElementIdentifier = ?, "
                    update_params_systemelements.append(attr_value2)

                elif attrName != 'Longitude' and attrName != 'Latitude': #attrName == 'Name'
                    attr_value = feature[attrName]
                    sql_query += f"{attrName} = ?, "
                    update_params_systemelements.append(attr_value)
        
        if len(update_params_systemelements) > 0:
            sql_query = sql_query.rstrip(", ") #Remove comma added above
            sql_query += " WHERE Id = ?;"
                #SystemElementId is null (in the layer) for features where the feature exists in DB but does not have a polygon
                # --> Get the SystemElementId from the DB
            
            #Get the SystemElementId
            sql_get_systemelement_id = f'''
                        SELECT Id FROM SystemElement

                        WHERE ElementIdentifier = ?
                        AND ElementTypeCharacter = ?
                        AND ScenarioId = ?
                    '''
            params = (feature['Identifier'][1:], feature['Identifier'][0], self.scenarioId)
            self.cur.execute(sql_get_systemelement_id, params)
            systemElementId = self.cur.fetchone()[0]
            update_params_systemelements.append(systemElementId)

            #Run the sql-query to update the SystemElement-Table
            self.cur.execute(sql_query, tuple(update_params_systemelements))
            self.conn.commit()

        #Update Geometry-table
        
        elementTypeTableName = self.mappingElementTypeTableName.get(feature['Identifier'][0], "Unknown") #Get table name (SubBasins or TransportReach)
        sql_query = f'SELECT * FROM {elementTypeTableName}'
        self.cur.execute(sql_query)
        columns = [description[0] for description in self.cur.description]
        sql_query = f"UPDATE {elementTypeTableName} SET "
        update_params = []
        #Loop over the changes and concatenate update-query
        for attrName in feature.fields().names():
            if attrName in columns:
                attr_value = feature[attrName]
                sql_query += f"{attrName} = ?, "
                update_params.append(attr_value)

        #Update the non-system-elements table (e.g. Sub-Basin)
        if len(update_params) > 0:
            sql_query = sql_query.rstrip(", ") #Remove comma added above
            sql_query += " WHERE SystemElementId = ?;"
            update_params.append(systemElementId)
            self.cur.execute(sql_query, tuple(update_params))
            self.conn.commit()

        self.log_to_qtalsim_tab(f"{sql_query}", Qgis.Info)
        self.log_to_qtalsim_tab(f"Feature {str(feature['Identifier'])} was updated in DB.", Qgis.Info)
        self.reconnectDatabase()

    def updatePolygonsAndCoordinates(self, feature):
        self.insertGeometriesToExistingFeatures(feature)
        self.reconnectDatabase()
        sql_query = f'''
            UPDATE SystemElement
            SET Longitude = ?, Latitude = ?
            WHERE Id = ?;
        '''
        params = (feature['Longitude'], feature['Latitude'], feature['Id'])
        self.cur.execute(sql_query, params)
        self.conn.commit()
        self.log_to_qtalsim_tab(f"Feature {str(feature['Identifier'])} was updated in DB.",Qgis.Info)
        self.reconnectDatabase()

    def loadUpdatedFeaturesinDB(self):
        '''
            Insert the features to connected DB or update features in DB.
        '''
        try:
            for feature in self.updatedElementsLayer.getFeatures():
                if feature[self.updateFieldName] == self.updateOption3:
                    self.insertNewElements(feature)

                elif feature[self.updateFieldName] == self.updateOption1 or feature[self.updateFieldName] == self.updateOption4:
                    self.insertGeometriesToExistingFeatures(feature)

                elif feature[self.updateFieldName] == self.updateOption2 or feature[self.updateFieldName] == self.updateOption5:
                    self.updatePolygonsAndCoordinates(feature)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        self.reconnectDatabase()
