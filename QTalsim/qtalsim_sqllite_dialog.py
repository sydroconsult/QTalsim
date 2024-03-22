from qgis.PyQt import QtCore, QtGui, QtWidgets
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem, QComboBox, QFileDialog, QDialogButtonBox
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis, QgsPointXY, QgsPoint, QgsFields, QgsLayerTreeLayer
from qgis.PyQt.QtCore import QVariant
import sqlite3
import webbrowser
import sys


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
        #Parameter initialization
        self.elementTypeCharacter = 'A'
        self.noLayerSelected = 'No Layer selected'
        self.geometryFieldName = 'Geometry' 
        self.updateFieldName = 'Updated'
        self.elementIdentifier = 'ElementIdentifier'
        self.layerGroup = None

        #Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.connectButtontoFunction(self.finalButtonBox.button(QDialogButtonBox.Help), self.openDocumentation)
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab
        self.connectButtontoFunction(self.onSelectDB, self.selectDB)
        self.comboxDBScenarios.currentIndexChanged.connect(self.on_scenario_change)
        
        self.connectButtontoFunction(self.onCreateSubBasinsLayer, self.createSubBasinsLayerInputDB)
        self.connectButtontoFunction(self.onUpdateCoordinatesToCenter, self.updateCoordinatesSystemElements)
        self.connectButtontoFunction(self.onViewUpdatedFeatures, self.loadUpdateLayer)

        self.connectButtontoFunction(self.onLoadFeaturesinDB, self.createUpdateLayer) #self.loadUpdatedFeaturesinDB
        self.connectButtontoFunction(self.onReconnectToDB, self.reconnectTriggeredByButton)

        #Get layers
        self.root = QgsProject.instance().layerTreeRoot()
        self.getAllLayers = self.mainPlugin.getAllLayers
        layers = self.getAllLayers(self.root)
        self.comboboxPolygonLayer.currentIndexChanged.connect(self.on_polygon_layer_changed)
        self.comboboxPolygonLayer.clear() #clear combobox EZG from previous runs
        
        self.comboboxPolygonLayer.addItems([self.noLayerSelected])
        self.comboboxPolygonLayer.addItems([layer.name() for layer in layers])

        #Options for inserting/updating polygons
        #CHANGE TO 4326!!!!
        self.epsg = 4326 #25832
        self.updateOption1 = 'Insert Sub-basins only'
        self.updateOption2 = 'Insert Sub-basins & Update Coordinates'
        self.updateOption3 = 'Insert new Sub-basins'
        self.updateOption4 = 'Update existing Sub-basins'
        self.updateOption5 = 'Update existing Sub-basins and Coordinates'
        self.updatedPolygonFeatures = []

    def openDocumentation(self):
        webbrowser.open('https://sydroconsult.github.io/QTalsim/doc_connect_to_db.html')

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
            sql_query = "SELECT Name, Id FROM Scenario"
            self.cur.execute(sql_query)
            self.scenariosAvailable = self.cur.fetchall()
            self.comboxDBScenarios.clear() #clear combobox EZG from previous runs
            self.comboxDBScenarios.addItems([f"{scenario[0]} (Id: {scenario[1]})" for scenario in self.scenariosAvailable])
        except sqlite3.Error as e:
            self.log_to_qtalsim_tab(e,Qgis.Critical)

    def on_scenario_change(self):
        '''
            not used at the moment - Whenever the Scenario is changed by the user (in the corresponding combobox)
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

    def createSubBasinsLayerInputDB(self):
        self.createSystemElementsAndOutflows()
        self.log_to_qtalsim_tab(f"SystemElements, Outflows and Sub-basins are now available in the project.", Qgis.Info)
        self.log_to_qtalsim_tab("You can now edit the sub-basins polygons and save the edits to the DB.", Qgis.Info)

    def createSystemElementsAndOutflows(self):
        '''
            Creates all Input Layers
        '''
        if self.layerGroup:
            self.root.removeChildNode(self.layerGroup)
        self.reconnectDatabase()
        sql_query = f"SELECT * FROM SystemElement WHERE scenarioId = {self.scenarioId}" #AND ElementTypeCharacter = '{self.elementTypeCharacter}'
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
        self.elementsPointLayer.loadNamedStyle(pathSymbology)
        self.elementsPointLayer.triggerRepaint()

        #Create LineLayer for Outflows
        line_layer = QgsVectorLayer(f"LineString?crs=epsg:{self.epsg}", "Outflows", "memory")
        pr = line_layer.dataProvider()

        fields = QgsFields()
        fields.append(QgsField("start_id", QVariant.Int))
        fields.append(QgsField("end_id", QVariant.Int))
        pr.addAttributes(fields)
        line_layer.updateFields()

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
        line_layer.updateExtents()
        
        #Add Layer-Group
        group_name = f"{self.scenarioName}"
        self.layerGroup = self.root.insertGroup(0, group_name)

        #Point Layer
        self.elementsPointLayer.setName("SystemElement")
        self.elementsPointLayerTree = QgsLayerTreeLayer(self.elementsPointLayer)
        QgsProject.instance().addMapLayer(self.elementsPointLayer, False)
        self.layerGroup.addChildNode(self.elementsPointLayerTree)

        #Line Layer
        current_path = os.path.dirname(os.path.abspath(__file__))
        pathSymbology = os.path.join(current_path, "symbology", "Outflows.qml")
        line_layer.loadNamedStyle(pathSymbology)
        line_layer.triggerRepaint()

        QgsProject.instance().addMapLayer(line_layer, False)
        line_layer_tree = QgsLayerTreeLayer(line_layer)
        self.layerGroup.addChildNode(line_layer_tree)
        
        #Add polygons
        self.addPolygonsSubBasins()
        self.polygonSystemElementsLayer.editingStopped.connect(self.on_editing_stopped)
        

    def on_editing_stopped(self):
        self.log_to_qtalsim_tab("Updating the edited geometries in DB.", Qgis.Info)
        self.finishedEditingSystemPolygons()

    def addPolygonsSubBasins(self):
        self.polygonSystemElementsLayer = QgsVectorLayer(f"Polygon?crs={self.elementsPointLayer.crs().authid()}", "WKT Polygons", "memory")
        dp = self.polygonSystemElementsLayer.dataProvider()

        #Add fields & Columns only where ElementTypeCharacter == the chosen elementTypeCharacter
        feats = [feat for feat in self.elementsPointLayer.getFeatures() if feat['ElementTypeCharacter'] == self.elementTypeCharacter]
        attr = self.elementsPointLayer.dataProvider().fields().toList()
        dp.addAttributes(attr)
        self.polygonSystemElementsLayer.updateFields()
        dp.addFeatures(feats)
        
        self.polygonSystemElementsLayer.startEditing()
        
        for feature in self.elementsPointLayer.getFeatures():
            if str(feature[self.geometryFieldName]).strip().upper() != 'NULL' and feature['ElementTypeCharacter'] == self.elementTypeCharacter:
                new_feat = QgsFeature(dp.fields())  # Create a new feature with the destination layer's fields
                new_feat.setAttributes(feature.attributes())  # Copy attributes
                wkt_string = str(feature[self.geometryFieldName])    
                geom = QgsGeometry.fromWkt(wkt_string)
                new_feat.setGeometry(geom)
                dp.addFeature(new_feat)  # Add the new feature to the destination layer
            
        self.polygonSystemElementsLayer.commitChanges()

        self.polygonSystemElementsLayer.setName(f"Sub-basins")
        self.elementsPolygonLayerTree = QgsLayerTreeLayer(self.polygonSystemElementsLayer)
        QgsProject.instance().addMapLayer(self.polygonSystemElementsLayer, False)
        self.layerGroup.addChildNode(self.elementsPolygonLayerTree)
        #self.polygonSystemElementsLayer.startEditing()

    def finishedEditingSystemPolygons(self):
        '''
            Store the sub-basins that were updated by the user.
        '''
        try:
            self.updatedPolygonFeatures = []
            self.insertPolygonFeatures = []
            storedWKT = {feat['Id']: feat[self.geometryFieldName] for feat in self.elementsPointLayer.getFeatures()}

            for feature in self.polygonSystemElementsLayer.getFeatures():
                elementId = feature['Id']
                
                if elementId in storedWKT: #if the element exists in the DB
                    current_wkt = storedWKT[elementId]
                    new_wkt = feature.geometry().asWkt() 
                    if new_wkt != current_wkt: #if there is a difference between the geometry of the same element in QGIS and in the DB
                        field_index = feature.fields().indexFromName(self.geometryFieldName)
                        # Ensure the field index is found
                        if field_index != -1:
                            feature.setAttribute(field_index, new_wkt)
                            self.polygonSystemElementsLayer.updateFeature(feature)
                            # Store this feature for later
                            self.updatedPolygonFeatures.append(feature)
                            longitude = float(feature['Longitude'])
                            latitude = float(feature['Latitude'])
                            point_feature = QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude))
                            if not feature.geometry().contains(point_feature):
                                self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {feature} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning)            
                else: #if the element does not exist in the DB = new feature
                    new_wkt = feature.geometry().asWkt()
                    field_index = feature.fields().indexFromName(self.geometryFieldName)
                    # Ensure the field index is found
                    if field_index != -1:
                        feature.setAttribute(field_index, new_wkt)
                        centroid = feature.geometry().centroid().asPoint()
                        centroid_geometry = QgsGeometry.fromPointXY(centroid)
                        feature.setAttribute(feature.fields().indexFromName('Latitude'), centroid.y())
                        feature.setAttribute(feature.fields().indexFromName('Longitude'), centroid.x())
                        self.polygonSystemElementsLayer.updateFeature(feature)
                        # Store this feature for later
                        self.insertPolygonFeatures.append(feature)

            for feature in self.updatedPolygonFeatures:
                #new_feature = QgsFeature(self.updatedElementsLayer.fields())
                self.insertPolygonsToExistingFeatures(feature)
        
            for feature in self.insertPolygonFeatures:
                self.insertNewElements(feature)
            self.log_to_qtalsim_tab(f"Finished editing Sub-basins.", Qgis.Info)

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Info)
    
    def updateCoordinatesSystemElements(self):
        try:
            self.reconnectDatabase()
            updated_coordinates = []
            for feature in self.polygonSystemElementsLayer.getFeatures():
                if feature.geometry() != 'NULL' and feature.geometry() is not None: #str(feature[self.geometryFieldName]).strip().upper()
                    polygon_geometry = QgsGeometry.fromWkt(feature[self.geometryFieldName])
                    centroid = feature.geometry().centroid().asPoint() #polygon_geometry
                    epsilon = 0.0000001
                    if abs(float(feature['Latitude']) - centroid.y()) > epsilon or abs(float(feature['Longitude']) - centroid.x()) > epsilon:
                        updated_coordinates.append(feature['Id'])
                        self.updateCoordinates(feature, centroid.y(), centroid.x())
            if len(updated_coordinates) == 0:
                self.log_to_qtalsim_tab("No coordinates were updated.", Qgis.Info)
            self.reconnectTriggeredByButton()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
            
    def on_polygon_layer_changed(self):
        selected_layer_name = self.comboboxPolygonLayer.currentText()
        if selected_layer_name != self.noLayerSelected:
            self.polygonLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
            self.comboboxUIFieldPolygon.clear()
            self.fieldsPolygonLayer = [field.name() for field in self.polygonLayer.fields()]
            self.comboboxUIFieldPolygon.addItems([str(field) for field in self.fieldsPolygonLayer])

            self.comboboxFieldName.clear()
            self.fieldsPolygonLayer = [field.name() for field in self.polygonLayer.fields()]
            self.comboboxFieldName.addItems(['No Field selected'])
            self.comboboxFieldName.addItems([str(field) for field in self.fieldsPolygonLayer])
        else:
            self.polygonLayer = None

    def createUpdateLayer(self):
        '''
            Creates a layer that holds all features that will be edited/inserted by a new (external) sub-basins-layer.
        '''
        self.uniqueIdentifierElements = self.comboboxUIFieldPolygon.currentText()
        
        #Create new layer to store updated features
        self.updatedElementsLayer = QgsVectorLayer(f"Point?crs={self.elementsPointLayer.crs().authid()}", "Updated Elements", "memory")
        fieldsPointLayer = self.elementsPointLayer.fields()
        self.updatedElementsLayer.dataProvider().addAttributes(fieldsPointLayer.toList())
        self.updatedElementsLayer.updateFields()
        dp = self.updatedElementsLayer.dataProvider()
        fieldNamesPointLayer = [field.name() for field in fieldsPointLayer]
        if self.geometryFieldName not in fieldNamesPointLayer:
            dp.addAttributes([QgsField(self.geometryFieldName, QVariant.String)])
        
        fieldNamesUpdateLayer = [field.name() for field in self.updatedElementsLayer.fields()]
        if self.updateFieldName not in fieldNamesUpdateLayer:
            dp.addAttributes([QgsField(self.updateFieldName, QVariant.String)])
        self.updatedElementsLayer.updateFields()

        self.updatedElementsLayer.startEditing()
        point_index = {str(feature['ElementTypeCharacter']) + str(feature[self.elementIdentifier]): feature for feature in self.elementsPointLayer.getFeatures()}
        
        '''
            Store Elements of external Polygons
        '''  
        try:
            #Polygon index
            polygon_index = {feature[self.uniqueIdentifierElements]: feature.geometry().asWkt() for feature in self.polygonLayer.getFeatures()}
            self.updatedElements = {1: [], 2: [], 3: []}

            editedFeatures = []
            for point_feature in self.elementsPointLayer.getFeatures():
                if point_feature['ElementTypeCharacter'] == self.elementTypeCharacter:
                    join_value = str(point_feature['ElementTypeCharacter']) + str(point_feature[self.elementIdentifier])
                   
                    #Insert Polygons to SystemElements, where no polygon exists
                    if join_value in polygon_index and (self.geometryFieldName not in fieldNamesPointLayer or str(point_feature[self.geometryFieldName]).strip().upper() == 'NULL' or point_feature[self.geometryFieldName] is None):
                        update_feature = QgsFeature(self.updatedElementsLayer.fields())
                        update_feature.setAttributes(point_feature.attributes())
                        update_feature.setGeometry(point_feature.geometry())
                        self.updatedElementsLayer.dataProvider().addFeatures([update_feature])
                        update_feature[self.geometryFieldName] = str(polygon_index[join_value])
                        self.updatedElementsLayer.updateFeature(update_feature)
                        polygon_geometry = QgsGeometry.fromWkt(polygon_index[join_value])
                        if not polygon_geometry.contains(point_feature.geometry()):
                            self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {join_value} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning) 
                    
                    #Update existing polygons with external polygons (for polygons edited directly see below)
                    elif join_value in polygon_index and point_feature[self.geometryFieldName] != polygon_index[join_value] and str(point_feature[self.geometryFieldName]).strip().upper() != 'NULL' and point_feature[self.geometryFieldName] is not None:
                        update_feature = QgsFeature(self.updatedElementsLayer.fields())
                        update_feature.setAttributes(point_feature.attributes())
                        update_feature.setGeometry(point_feature.geometry())

                        geom_field_index = self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName)

                        if geom_field_index != -1:
                            update_feature.setAttribute(geom_field_index, polygon_index[join_value])
                        self.updatedElementsLayer.dataProvider().addFeatures([update_feature])
                        editedFeatures.append(update_feature['Id'])
                        polygon_geometry = QgsGeometry.fromWkt(polygon_index[join_value])
                        if not polygon_geometry.contains(point_feature.geometry()):
                            self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {join_value} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning) 
                                 
            self.updatedElementsLayer.commitChanges()
            
            '''
                Edit Update-Layer
            '''
            self.updatedElementsLayer.startEditing()
            for update_feature in self.updatedElementsLayer.getFeatures():
                join_value = str(update_feature['ElementTypeCharacter']) + str(update_feature[self.elementIdentifier])
                field_index = self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName)
                self.updatedElementsLayer.changeAttributeValue(update_feature.id(), field_index, polygon_index[join_value])
                polygon_geometry = QgsGeometry.fromWkt(polygon_index[join_value])
                if self.checkboxUpdateCoordinates.isChecked():
                    #Change the coordinates of SystemElement
                    centroid = polygon_geometry.centroid().asPoint()
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
                    #Don't change coordinates, only insert new polygon
                    self.updatedElements[1].append(join_value)
                    self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption1)  

            self.updatedElementsLayer.commitChanges()
            
            #Adding new Polygons/System Elements
            self.updatedElementsLayer.startEditing()
            
            for polygon_feature in self.polygonLayer.getFeatures():
                join_value = polygon_feature[self.uniqueIdentifierElements]
                if join_value not in point_index:
                    new_feature = QgsFeature(self.updatedElementsLayer.fields())
                    centroid = polygon_feature.geometry().centroid().asPoint() 
                    centroid_geometry = QgsGeometry.fromPointXY(centroid)
                    new_feature.setGeometry(centroid_geometry)
                    new_feature[self.elementIdentifier] = join_value[1:]
                    new_feature[self.geometryFieldName] = polygon_feature.geometry().asWkt()
                    new_feature['Longitude'] = centroid.x()
                    new_feature['Latitude'] = centroid.y()
                    new_feature['ElementType'] = 2 #nur für SubBasins!!
                    new_feature['ElementTypeCharacter'] = join_value[0]
                    if self.comboboxFieldName.currentText() != 'No Field selected':
                        new_feature['Name'] = polygon_feature[self.comboboxFieldName.currentText()]
                    new_feature[self.updateFieldName] = self.updateOption3
                    self.updatedElementsLayer.dataProvider().addFeatures([new_feature])
                    self.updatedElements[3].append(join_value)

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
        self.createSystemElementsAndOutflows()
        self.log_to_qtalsim_tab("Reconnected with DB.", Qgis.Info)

    #Existing polygons überarbeiten
    def reconnectDatabase(self):
        try:
            self.conn = sqlite3.connect(self.file_path_db)
            self.cur = self.conn.cursor()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

    '''
        Functions to update elements in DB/insert new elements to DB
    '''
    def insertNewElements(self, feature):
        '''
            Insert new sub-basins that haven't existed.
        '''
        self.reconnectDatabase()
        sql_query = f'''
            INSERT INTO SystemElement 
            (ScenarioId, ElementType, ElementTypeCharacter, ElementIdentifier, Name, Latitude, Longitude, {self.geometryFieldName}) 
            VALUES
            ('{self.scenarioId}', {feature['ElementType']}, '{feature['ElementTypeCharacter']}', '{feature[self.elementIdentifier]}', 
            '{feature['Name']}', {feature['Latitude']}, {feature['Longitude']}, '{feature[self.geometryFieldName]}')
        '''
        self.cur.execute(sql_query)
        self.conn.commit()
        self.conn.close()

        self.reconnectDatabase()
        sql_query = f'''
                        SELECT Id FROM SystemElement
                        WHERE ElementIdentifier = '{feature[self.elementIdentifier]}'
                        AND ElementTypeCharacter = '{feature['ElementTypeCharacter']}'
                        AND ScenarioId = '{self.scenarioId}'
                    '''
        self.cur.execute(sql_query)
        feature_id_tuple = self.cur.fetchone()
        
        feature_id = feature_id_tuple[0]
        sql_query = '''
                        INSERT INTO SubBasin 
                        (SystemElementId) 
                        VALUES 
                        (?)
                    '''
        self.cur.execute(sql_query, (feature_id,))
        self.conn.commit()
        self.log_to_qtalsim_tab(f"Feature {str(feature['ElementTypeCharacter']) + str(feature[self.elementIdentifier])} was inserted in DB.", Qgis.Info)
        self.conn.close()

    def insertPolygonsToExistingFeatures(self, feature):
        '''
            Insert only polygon-geometries to existing sub-basins.
        '''
        self.reconnectDatabase()
        sql_query = f'''
            UPDATE SystemElement
            SET {self.geometryFieldName} = ?
            WHERE Id = ?;
        '''
        #muss man hier auch das Szenario definieren?
        params = (feature[self.geometryFieldName], feature['Id'])
        self.cur.execute(sql_query, params)
        self.conn.commit()
        self.log_to_qtalsim_tab(f"Feature {str(feature['ElementTypeCharacter']) + str(feature[self.elementIdentifier])} was updated in DB.", Qgis.Info)
        self.conn.close()

    def updatePolygonsAndCoordinates(self, feature):

        self.reconnectDatabase()
        sql_query = f'''
            UPDATE SystemElement
            SET {self.geometryFieldName} = ?, Longitude = ?, Latitude = ?
            WHERE Id = ?;
        '''
        params = (feature[self.geometryFieldName], feature['Longitude'], feature['Latitude'], feature['Id'])
        self.cur.execute(sql_query, params)
        self.conn.commit()
        self.log_to_qtalsim_tab(f"Feature {str(feature['ElementTypeCharacter']) + str(feature[self.elementIdentifier])} was updated in DB.",Qgis.Info)
        self.conn.close()

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
        self.log_to_qtalsim_tab(f"Feature {str(feature['ElementTypeCharacter']) + str(feature[self.elementIdentifier])} was updated in DB.",Qgis.Info)
        self.conn.close()

    def loadUpdatedFeaturesinDB(self):
        '''
            Insert the features to connected DB or update features in DB.
        '''
        try:
            for feature in self.updatedElementsLayer.getFeatures():
                if feature[self.updateFieldName] == self.updateOption3:
                    self.insertNewElements(feature)

                elif feature[self.updateFieldName] == self.updateOption1 or feature[self.updateFieldName] == self.updateOption4:
                    self.insertPolygonsToExistingFeatures(feature)

                elif feature[self.updateFieldName] == self.updateOption2 or feature[self.updateFieldName] == self.updateOption5:
                    self.updatePolygonsAndCoordinates(feature)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        self.conn.close()
