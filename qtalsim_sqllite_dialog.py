from qgis.PyQt import QtCore, QtGui, QtWidgets
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem, QComboBox, QFileDialog
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis, QgsPointXY, QgsPoint, QgsFields
from qgis.PyQt.QtCore import QVariant
import sqlite3
import sys

'''
import sys


import subprocess
plugin_dir = os.path.dirname(__file__)
get_pip_path = os.path.join(plugin_dir, 'get_pip.py')

try:
    import pip
except:
    with open(get_pip_path, "r") as file:
        exec(file.read())
    import pip
    # just in case the included version is old
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
try:
    import sqlalchemy
    from sqlalchemy import create_engine
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'SQLAlchemy'])
    import sqlalchemy
    from sqlalchemy import create_engine
'''

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
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab
        #self.onSelectDB.clicked.connect(self.selectDB)
        self.connectButtontoFunction(self.onSelectDB, self.selectDB)
        self.comboxDBScenarios.currentIndexChanged.connect(self.on_scenario_change)
        
        self.connectButtontoFunction(self.onCreateSubBasinsLayer, self.createSubBasinsLayerInputDB)
        self.connectButtontoFunction(self.onAddSystemElementPolygons, self.addPolygonsSubBasins)
        self.connectButtontoFunction(self.onConfirmPolygonLayer, self.confirmPolygonLayer)

        self.connectButtontoFunction(self.onFinishedEditingSystemPolygons, self.finishedEditingSystemPolygons)
        root = QgsProject.instance().layerTreeRoot()
        self.getAllLayers = self.mainPlugin.getAllLayers
        layers = self.getAllLayers(root)
        self.comboboxElementType.currentIndexChanged.connect(self.on_elementType_change)
        self.comboboxPolygonLayer.currentIndexChanged.connect(self.on_polygon_layer_changed)
        self.comboboxPolygonLayer.clear() #clear combobox EZG from previous runs
        self.noLayerSelected = 'No Layer selected'
        self.comboboxPolygonLayer.addItems([self.noLayerSelected])
        self.comboboxPolygonLayer.addItems([layer.name() for layer in layers])
        
        
        self.connectButtontoFunction(self.onLoadFeaturesinDB, self.loadUpdatedFeaturesinDB)

        #Parameter initialization
        self.geometryFieldName = 'Geometry' #muss evtl. noch angepasst werden
        self.updateFieldName = 'Updated'
        self.elementIdentifier = 'ElementIdentifier'
        
        #Options for inserting/updating polygons
        self.updateOption1 = 'Insert Polygons'
        self.updateOption2 = 'Insert Polygons & Update Coordinates'
        self.updateOption3 = 'Insert new Features'
        self.updateOption4 = 'Update existing Polygon'
        self.updateOption5 = 'Update existing Polygons and Coordinates'
        self.updatedPolygonFeatures = []

    def selectDB(self):
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
        try:
            #scenarioCombo = self.comboxDBScenarios.currentText()
            scenarioComboId = self.comboxDBScenarios.currentIndex()
            scenarioName = self.scenariosAvailable[scenarioComboId][0]
            #scenarioName = scenarioCombo.split(" (", 1)[0]
            self.scenarioId = self.scenariosAvailable[scenarioComboId][1]
            sql_query = f"SELECT Distinct ElementTypeCharacter FROM SystemElement WHERE scenarioId = {self.scenarioId}"
            self.cur.execute(sql_query)
            self.elementTypes = self.cur.fetchall()
            self.comboboxElementType.addItems([elementType[0] for elementType in self.elementTypes])

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
    
    def on_elementType_change(self):
        self.elementTypeCharacter = self.comboboxElementType.currentText()

    def createSubBasinsLayerInputDB(self):
        sql_query = f"SELECT * FROM SystemElement WHERE scenarioId = {self.scenarioId}" #AND ElementTypeCharacter = '{self.elementTypeCharacter}'
        self.cur.execute(sql_query)
        columns = [description[0] for description in self.cur.description]
        lat_index = columns.index('Latitude')
        lon_index = columns.index('Longitude')
        self.systemElementData = self.cur.fetchall()

        #CHANGE TO 4326!!!!
        epsg = 25832
        self.elementsPointLayer = QgsVectorLayer(f"Point?crs=epsg:{epsg}", "SubBasins Talsim DB", "memory") #Qgis Layer with sub basin points

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
        line_layer = QgsVectorLayer(f"LineString?crs=epsg:{epsg}", "Outflows", "memory")
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
        
        self.elementsPointLayer.setName("SystemElement")
        QgsProject.instance().addMapLayer(line_layer)
        QgsProject.instance().addMapLayer(self.elementsPointLayer)

        self.elementsPointLayer.editingStopped.connect(self.on_editing_stopped)

        self.log_to_qtalsim_tab(f"Layers with SystemElements and Outflows were added to the project.", Qgis.Info)
    
    def on_editing_stopped(self):
        print("Stopped editing.")

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

        self.polygonSystemElementsLayer.setName(f"Polygons of ElementType {self.elementTypeCharacter}")
        QgsProject.instance().addMapLayer(self.polygonSystemElementsLayer)
        self.polygonSystemElementsLayer.startEditing()
        self.log_to_qtalsim_tab("Polygon Layer (SystemElements) was added. You can now edit the polygons.", Qgis.Info)

    def on_polygon_layer_changed(self):
        selected_layer_name = self.comboboxPolygonLayer.currentText()
        if selected_layer_name != self.noLayerSelected:
            self.polygonLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
            self.comboboxUIFieldPolygon.clear()
            self.fieldsPolygonLayer = [field.name() for field in self.polygonLayer.fields()]
            self.comboboxUIFieldPolygon.addItems([str(field) for field in self.fieldsPolygonLayer])
        else:
            self.polygonLayer = None

    def finishedEditingSystemPolygons(self):
        self.updatedPolygonFeatures = []
        storedWKT = {feat['Id']: feat[self.geometryFieldName] for feat in self.elementsPointLayer.getFeatures()}

        for feature in self.polygonSystemElementsLayer.getFeatures():
            elementId = feature['Id']
            if elementId in storedWKT:
                current_wkt = storedWKT[elementId]
                new_wkt = feature.geometry().asWkt() 
                if new_wkt != current_wkt:
                    field_index = feature.fields().indexFromName(self.geometryFieldName)
                    # Ensure the field index is found
                    if field_index != -1:
                        feature.setAttribute(field_index, new_wkt)
                        self.polygonSystemElementsLayer.updateFeature(feature)
                        # Store this feature for later
                        self.updatedPolygonFeatures.append(feature)
            else:
                new_wkt = feature.geometry().asWkt()
                field_index = feature.fields().indexFromName(self.geometryFieldName)
                # Ensure the field index is found
                if field_index != -1:
                    feature.setAttribute(field_index, new_wkt)
                    self.polygonSystemElementsLayer.updateFeature(feature)
                    # Store this feature for later
                    self.updatedPolygonFeatures.append(feature)
        self.log_to_qtalsim_tab(f"Finished editing Polygon Layer (SystemElements).", Qgis.Info)

    def confirmPolygonLayer(self):
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
        point_index = {feature[self.elementIdentifier]: feature for feature in self.elementsPointLayer.getFeatures()}
        '''
            Store Elements of external Polygons
        '''  
        if self.checkboxImportExternalPolygons.isChecked():
            try:
                #Polygon index
                polygon_index = {feature[self.uniqueIdentifierElements]: feature.geometry().asWkt() for feature in self.polygonLayer.getFeatures()}
                self.updatedElements = {1: [], 2: [], 3: []}

                editedFeatures = []
                for point_feature in self.elementsPointLayer.getFeatures():
                    if point_feature['ElementTypeCharacter'] == self.elementTypeCharacter:
                        join_value = point_feature[self.elementIdentifier]
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
                        elif self.checkboxUpdateExistingPolygons.isChecked() and join_value in polygon_index and point_feature[self.geometryFieldName] != polygon_index[join_value] and str(point_feature[self.geometryFieldName]).strip().upper() != 'NULL' and point_feature[self.geometryFieldName] is not None:
                            update_feature = QgsFeature(self.updatedElementsLayer.fields())
                            update_feature.setAttributes(point_feature.attributes())
                            update_feature.setGeometry(point_feature.geometry())
                            
                            #self.updatedElementsLayer.changeAttributeValue(update_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName), polygon_index[join_value]) 
                            #self.updatedElementsLayer.updateFeature(update_feature)
                            geom_field_index = self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName)
                            if geom_field_index != -1:
                                update_feature.setAttribute(geom_field_index, polygon_index[join_value])
                            self.updatedElementsLayer.dataProvider().addFeatures([update_feature])
                            editedFeatures.append(update_feature['Id'])
                            polygon_geometry = QgsGeometry.fromWkt(polygon_index[join_value])
                            if not polygon_geometry.contains(point_feature.geometry()):
                                self.log_to_qtalsim_tab(f"Spatial containment check failed: Element {join_value} is not within the target polygon. Despite this, the element was updated. ", Qgis.Warning) 
                            
                            
                self.updatedElementsLayer.commitChanges()

                self.updatedElementsLayer.startEditing()
                for update_feature in self.updatedElementsLayer.getFeatures():
                    join_value = update_feature[self.elementIdentifier]
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
                        new_feature[self.elementIdentifier] = join_value
                        new_feature[self.geometryFieldName] = polygon_feature.geometry().asWkt()
                        new_feature['Longitude'] = centroid.x()
                        new_feature['Latitude'] = centroid.y()
                        new_feature['ElementType'] = 2 #nur für SubBasins!!
                        new_feature['ElementTypeCharacter'] = self.elementTypeCharacter
                        new_feature[self.updateFieldName] = self.updateOption3
                        self.updatedElementsLayer.dataProvider().addFeatures([new_feature])
                        self.updatedElements[3].append(join_value)

                self.updatedElementsLayer.commitChanges()

            except Exception as e:
                self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

        #Update existing polygons
        if len(self.updatedPolygonFeatures) >= 0 and self.checkboxUpdateExistingPolygons.isChecked():
            self.updatedElementsLayer.startEditing()
            #self.updatedPolygonFeatures are features that were manually edited by the user
            for updated_feat in self.updatedPolygonFeatures:
                # Create a new feature for self.updatedElementsLayer
                new_feature = QgsFeature(self.updatedElementsLayer.fields())
                centroid = updated_feat.geometry().centroid().asPoint()
                centroid_geometry = QgsGeometry.fromPointXY(centroid)
                new_feature.setGeometry(centroid_geometry)
                #Necessary to add None value to the attributes, as the layer self.updatedElementsLayer holds an additional column (updatetype)
                adjusted_attributes = [None] * len(self.updatedElementsLayer.fields())
                for i, field in enumerate(self.updatedElementsLayer.fields()):
                    if updated_feat.fields().indexFromName(field.name()) != -1:
                        source_index = updated_feat.fields().indexFromName(field.name())
                        adjusted_attributes[i] = updated_feat.attributes()[source_index]
                new_feature.setAttributes(adjusted_attributes)

                # Add the new feature
                self.updatedElementsLayer.addFeature(new_feature)

                if self.checkboxUpdateCoordinates.isChecked() and new_feature[self.elementIdentifier] in point_index:
                    centroid = new_feature.geometry().centroid().asPoint() 
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName('Longitude'), centroid.x())    
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName('Latitude'), centroid.y())  
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption5)  
                    #if str(new_feature[self.geometryFieldName]).strip().upper() == 'NULL':
                    #    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName), new_feature.geometry().asWkt())                   
                
                elif new_feature[self.elementIdentifier] in point_index and not self.checkboxUpdateCoordinates.isChecked():
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption4)  
                
                elif new_feature[self.elementIdentifier] not in point_index:
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName('Longitude'), centroid.x())    
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName('Latitude'), centroid.y())
                    #if str(new_feature[self.geometryFieldName]).strip().upper() == 'NULL':
                    #    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.geometryFieldName), new_feature.geometry().asWkt())
                    self.updatedElementsLayer.changeAttributeValue(new_feature.id(), self.updatedElementsLayer.fields().indexFromName(self.updateFieldName), self.updateOption3)  

            self.updatedElementsLayer.commitChanges()

        current_path = os.path.dirname(os.path.abspath(__file__))
        pathSymbology = os.path.join(current_path, "symbology", "UpdatedElements.qml")
        self.updatedElementsLayer.loadNamedStyle(pathSymbology)
        self.updatedElementsLayer.triggerRepaint()

        QgsProject.instance().addMapLayer(self.updatedElementsLayer)
        self.log_to_qtalsim_tab(f"Created Layer with all Features to be updated when confirmed.", Qgis.Info)

        #Existing polygons überarbeiten
    def reconnectDatabase(self):
        try:
            self.conn = sqlite3.connect(self.file_path_db)
            self.cur = self.conn.cursor()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}",Qgis.Critical)

    def loadUpdatedFeaturesinDB(self):
        try:
            for feature in self.updatedElementsLayer.getFeatures():
                if feature[self.updateFieldName] == self.updateOption3:
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
                    self.log_to_qtalsim_tab(f"Feature {feature[self.elementIdentifier]} was inserted in DB.", Qgis.Info)
                    
                elif feature[self.updateFieldName] == self.updateOption1 or feature[self.updateFieldName] == self.updateOption4:
                    sql_query = f'''
                        UPDATE SystemElement
                        SET {self.geometryFieldName} = ?
                        WHERE Id = ?;
                    '''
                    #muss man hier auch das Szenario definieren?
                    params = (feature[self.geometryFieldName], feature['Id'])
                    self.cur.execute(sql_query, params)
                    self.conn.commit()
                    self.log_to_qtalsim_tab(f"Feature {feature[self.elementIdentifier]} was updated in DB.", Qgis.Info)

                elif feature[self.updateFieldName] == self.updateOption2 or feature[self.updateFieldName] == self.updateOption5:
                    sql_query = f'''
                        UPDATE SystemElement
                        SET {self.geometryFieldName} = ?, Longitude = ?, Latitude = ?
                        WHERE Id = ?;
                    '''
                    params = (feature[self.geometryFieldName], feature['Longitude'], feature['Latitude'], feature['Id'])
                    self.cur.execute(sql_query, params)
                    self.conn.commit()
                    self.log_to_qtalsim_tab(f"Feature {feature[self.elementIdentifier]} was updated in DB.",Qgis.Info)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        self.conn.close()
        #Über Unique Identifier (muss man über ComboBox aller Felder?) dann an Unique Identifier der SubBasins automatisch joinen
        #Option, dass man über 
        
    #def 
    #    comboboxPolygonLayer
        #finally:
        #    self.conn.close()