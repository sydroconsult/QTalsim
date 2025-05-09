import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog, QDialogButtonBox, QInputDialog
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer, QgsMapLayer, QgsWkbTypes, QgsRasterLayer, QgsVectorLayer, QgsRasterBandStats, QgsField, QgsVectorFileWriter, edit, Qgis, QgsProcessingFeedback, QgsProcessingException, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRaster
from qgis.PyQt.QtCore import pyqtSignal, QVariant
import processing
import webbrowser
import gc #Garbage collection
import time
import sys
import shutil
import sqlite3
import math

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qtalsim_subbasin.ui'))

class SubBasinPreprocessingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, mainPluginInstance, parent=None):
        """Constructor."""
        super(SubBasinPreprocessingDialog, self).__init__(parent)
        self.iface = iface
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.mainPlugin = mainPluginInstance
        self.initialize_parameters()
        self.finalButtonBox.button(QDialogButtonBox.StandardButton.Help).setText('Help')

    def initialize_parameters(self):
        #Initialize variables
        self.subBasinLayer = None
        self.DEMLayer = None
        self.polygonLayers = None
        self.rasterLayers = None
        self.lfpFinalLayer = None
        self.noLayerSelected = "No Layer selected"
        self.outputFolder = None
        self.outputPath.clear()
        self.asciiFilename = None #ASCII-Filename
        self.basinIDField = 'BASINID'
        self.lengthFieldName = 'Length'
        self.imperviousFieldName = 'Imp_mean'
        self.areaFieldName = 'Area'
        self.no_feedback = NoFeedback()
        self.subbasinUIField = None

        #Main Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers
        self.start_operation = self.mainPlugin.start_operation
        self.end_operation = self.mainPlugin.end_operation
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab

        #Connect Buttons to Functions 
        self.connectButtontoFunction(self.onLongestFlowPath, self.performLFP) #Calculate LongestFlowPath
        self.connectButtontoFunction(self.onRun, self.runSubBasinPreprocessing) 
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFolder) 
        self.connectButtontoFunction(self.finalButtonBox.button(QDialogButtonBox.StandardButton.Help), self.openDocumentation)
        self.log_to_qtalsim_tab(
            "This feature processes a sub-basins layer. It calculates the highest and lowest points within the sub-basins, the area and average impermeable area (optional) per sub-basin, and the longest flow path for each sub-basin. "
            "Please ensure that WhiteboxTools is installed and properly configured. "
            "For detailed instructions, click the Help button.", 
            Qgis.MessageLevel.Info
        )        
        #Fill Comboboxes
        self.comboboxUISubBasin.clear()
        self.comboboxNameField.clear()
        self.fillLayerComboboxes()

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

    def getAllLineLayers(self, root):
        '''
            Load all line-layers
        '''
        layers = []
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                # If the child is a group, recursively get layers from this group
                layers.extend(self.getAllLineLayers(child))
            elif isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if layer and layer.type() == QgsMapLayer.LayerType.VectorLayer:
                    # If the child is a layer, add it to the list
                    if layer.geometryType() == QgsWkbTypes.GeometryType.LineGeometry:
                        layers.append(layer)
        return layers
    
    def openDocumentation(self):
        '''
            Connected with help-button.
        '''
        webbrowser.open('https://sydroconsult.github.io/QTalsim/doc_subbasin_preprocessing')

    def selectOutputFolder(self):
        '''
            Function to select the output folder. 
        '''
        self.outputFolder = None
        self.outputFolder = QFileDialog.getExistingDirectory(self, "Select Folder","") #, options=options
        if self.outputFolder:
            self.outputPath.setText(self.outputFolder)

    def fillLayerComboboxes(self):
        '''
            Fills all comboboxes with layers
        '''

        self.polygonLayers, self.rasterLayers = self.getAllLayers(QgsProject.instance().layerTreeRoot())
        self.lineLayers = self.getAllLineLayers(QgsProject.instance().layerTreeRoot())

        #Output Format
        #self.comboboxOutputFormat.clear() #clear combobox from previous runs
        #self.comboboxOutputFormat.addItems(["SQLite-Export (Talsim NG5)","ASCII-Export (Talsim NG4)"])

        #Sub-basins layer
        self.comboboxSubBasinLayer.clear() #clear combobox EZG from previous runs
        self.comboboxSubBasinLayer.addItem(self.noLayerSelected)
        self.comboboxSubBasinLayer.addItems([layer.name() for layer in self.polygonLayers])
        self.safeConnect(self.comboboxSubBasinLayer.currentIndexChanged, self.on_subbasin_layer_changed) #Refill the sub-basin combobox whenever user selects different layer

        #DEM layer
        self.comboboxDEMLayer.clear() #clear combobox from previous runs
        self.comboboxDEMLayer.addItem(self.noLayerSelected)
        self.comboboxDEMLayer.addItems([layer.name() for layer in self.rasterLayers])

        #Water network layer
        self.comboboxWaterNetwork.clear() #clear combobox from previous runs
        self.comboboxWaterNetwork.addItem(self.noLayerSelected)
        self.comboboxWaterNetwork.addItems([layer.name() for layer in self.lineLayers])

        #Imperviousness layer
        self.comboboxImperviousness.clear()
        self.comboboxImperviousness.addItem(self.noLayerSelected)
        self.comboboxImperviousness.addItems([layer.name() for layer in self.rasterLayers])

    def on_subbasin_layer_changed(self):
        '''
            Fill the sub-basin-UI-combobox.
        '''
        selected_layer_name = self.comboboxSubBasinLayer.currentText()
        if selected_layer_name != self.noLayerSelected and selected_layer_name is not None:
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            if layers:
                self.subBasinLayer = layers[0]

                self.comboboxUISubBasin.clear()
                self.fieldsSubbasinLayer = [field.name() for field in self.subBasinLayer.fields()]
                self.comboboxUISubBasin.addItems([str(field) for field in self.fieldsSubbasinLayer])

                self.comboboxNameField.clear()
                self.comboboxNameField.addItems(["Select Name-Field"])
                self.comboboxNameField.addItems([str(field) for field in self.fieldsSubbasinLayer])

    def runSubBasinPreprocessing(self):
        '''
            Core function to run all processing-steps of the sub-basins layer.
                - max/min height in sub-basin
                - area of sub-basin in hectares
                - mean impervious area per sub-basin (optional)
                - longest flow path per sub-basin
        '''
        try:
            self.start_operation()
            self.log_to_qtalsim_tab(f"Processing the sub-basins layer.", Qgis.MessageLevel.Info)
            #Select DEM Layer
            if self.DEMLayer is None:
                selected_layer_name = self.comboboxDEMLayer.currentText()
                if selected_layer_name != self.noLayerSelected:
                    self.DEMLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
                else:
                    self.log_to_qtalsim_tab("Please select a DEM layer to process the sub-basins.", Qgis.MessageLevel.Critical)

            self.log_to_qtalsim_tab(f"Calculating the max- and min-height and area of each sub-basin...", Qgis.MessageLevel.Info)
            self.calculateHeightandAreaSubBasins()
            
            #Convert the subbasinUIField to string (needed for join to LFP)
            self.subBasinLayerProcessed.startEditing()

            #Get the original field index
            if not self.subbasinUIField:
                self.subbasinUIField = self.comboboxUISubBasin.currentText()

            original_field_name = self.subbasinUIField
            original_field_index = self.subBasinLayerProcessed.fields().indexOf(original_field_name)
      
            #Add a new string field
            new_field_name = f"{original_field_name}_temp"
            self.subBasinLayerProcessed.dataProvider().addAttributes([QgsField(new_field_name, QVariant.String)])
            self.subBasinLayerProcessed.updateFields()

            #Get the new field index
            new_field_index = self.subBasinLayerProcessed.fields().indexOf(new_field_name)

            #Copy values from the original field to the new field as strings
            for feature in self.subBasinLayerProcessed.getFeatures():
                original_value = feature[original_field_name]
                string_value = str(original_value) if original_value is not None else None
                feature.setAttribute(new_field_index, string_value)
                self.subBasinLayerProcessed.updateFeature(feature)

            #Delete the original field
            self.subBasinLayerProcessed.deleteAttribute(original_field_index)

            self.subBasinLayerProcessed.updateFields()

            #Rename the new field to match the original field name
            new_field_index = self.subBasinLayerProcessed.fields().indexOf(new_field_name)  #Re-check the index
            self.subBasinLayerProcessed.renameAttribute(new_field_index, original_field_name)

            #Commit the changes
            self.subBasinLayerProcessed.commitChanges()


            #Calculate mean imperviousness for each sub-basin
            selected_layer_name = self.comboboxImperviousness.currentText() #Get the selected layer name
            
            if selected_layer_name is not None and selected_layer_name != self.noLayerSelected: #imperviousness is optional
                self.log_to_qtalsim_tab(f"Calculating mean imperviousness for each sub-basin...", Qgis.MessageLevel.Info)
                self.imperviousnessLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
                self.subBasinLayerProcessed = self.calculateImperviousness(self.subBasinLayerProcessed, self.imperviousnessLayer)
            else: #add the field with null-values
                if self.imperviousFieldName not in [field.name() for field in self.subBasinLayerProcessed.fields()]:
                    imp_field = QgsField(self.imperviousFieldName, QVariant.Double)
                    self.subBasinLayerProcessed.dataProvider().addAttributes([imp_field])
                    self.subBasinLayerProcessed.updateFields()            

            #Recalculate the lengths, in case the user edited the longest flow path layer
            if self.lfpFinalLayer is not None:
                self.lfpFinalLayer.startEditing()  # Start editing
                for feature in self.lfpFinalLayer.getFeatures():
                    geom = feature.geometry()
                    length = geom.length()
                    feature[self.lengthFieldName] = length
                    self.lfpFinalLayer.updateFeature(feature)
                self.lfpFinalLayer.commitChanges()  # Commit changes

                #Join the LFP length to sub-basin layer
                self.subBasinLayerProcessed = processing.run("native:joinattributestable", {'INPUT': self.subBasinLayerProcessed,'FIELD': self.subbasinUIField,'INPUT_2': self.lfpFinalLayer,'FIELD_2':'BASINID','FIELDS_TO_COPY':[self.lengthFieldName, "Rotation"],'METHOD':1,'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
            
            self.log_to_qtalsim_tab(f"Exporting the layer...", Qgis.MessageLevel.Info)
            self.geopackage_path = os.path.join(self.outputFolder, f"Sub_basins_processed.gpkg") #Output-path

            #Check if feature starts with A and delete feature if it does not
            self.subBasinLayerProcessed.startEditing()
            deleted_feature_ui = []
            for feature in self.subBasinLayerProcessed.getFeatures():
                if feature[self.subbasinUIField].startswith("A") == False:
                    deleted_feature_ui.append(feature[self.subbasinUIField])
                    self.subBasinLayerProcessed.deleteFeature(feature.id())

            self.subBasinLayerProcessed.commitChanges()
            if deleted_feature_ui:
                self.log_to_qtalsim_tab(f"Deleted following features because they do not start with A: {deleted_feature_ui}", Qgis.MessageLevel.Info)

            if self.groupboxDBExport.isChecked():
                if self.textDBName.text() is not None:
                    self.dbName = self.textDBName.text()
                    self.DBExport()
                else:
                    self.log_to_qtalsim_tab("Please enter a database name.", Qgis.MessageLevel.Critical)

            if self.groupboxASCIIExport.isChecked():
                if self.textAsciiFileName.text() is not None:
                    self.asciiFilename = self.textAsciiFileName.text()
                    self.asciiExport()
                else:
                    self.log_to_qtalsim_tab("Please enter a filename for the ASCII-export.", Qgis.MessageLevel.Critical)
            

            #Export sub-basins-layer to geopackage
            params = {
                'INPUT': self.subBasinLayerProcessed,
                'OUTPUT': self.geopackage_path,
                'LAYER_NAME': 'Sub-basins Processed',
                'OVERWRITE': True,
            }
            processing.run("native:savefeatures", params)
            self.log_to_qtalsim_tab(f"Processed sub-basins layer was saved to: {self.geopackage_path}", Qgis.MessageLevel.Info)

            finalSubBasinsLayer = QgsVectorLayer(f"{self.geopackage_path}|layername=Sub-basins Processed", "Sub-basins Processed", "ogr")
            QgsProject.instance().addMapLayer(finalSubBasinsLayer)

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.MessageLevel.Critical)

        finally:
            self.end_operation()

    def calculateHeightandAreaSubBasins(self):
        '''
            Calculates the min/max height and the area for every sub-basin
        '''
        if self.subBasinLayer == None:
            self.log_to_qtalsim_tab("Please select a sub-basin layer to process the sub-basins..", Qgis.MessageLevel.Critical)
        #Get the max and min height for every sub-basin by using the input DEM-layer
        self.subBasinLayerProcessed = processing.run("native:zonalstatisticsfb", {'INPUT':self.subBasinLayer,'INPUT_RASTER':self.DEMLayer,'RASTER_BAND':1,'COLUMN_PREFIX':'Height_','STATISTICS':[5,6],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']            

        #Add field to store area
        if self.areaFieldName not in [field.name() for field in self.subBasinLayerProcessed.fields()]:
            area_field = QgsField(self.areaFieldName, QVariant.Double)
            self.subBasinLayerProcessed.dataProvider().addAttributes([area_field])
            self.subBasinLayerProcessed.updateFields()
        
        #Calculate the area of every sub-basin
        with edit(self.subBasinLayerProcessed):
            for feature in self.subBasinLayerProcessed.getFeatures():
                #Calculate the area for each feature and update the 'Area' field with the calculated value
                area_sqm = feature.geometry().area() #area in squaremeter
                area_hectares = area_sqm / 10000 #calculate area in hectares (.EZG-file needs hectares as input)
                feature[self.areaFieldName] = area_hectares
                
                #Update the feature in the layer
                self.subBasinLayerProcessed.updateFeature(feature)

    def calculateImperviousness(self, sub_basins_layer, imperviousness_layer):
        '''
            Calculates average impervious area per sub-basin.
        '''
        self.subBasinLayerProcessed = processing.run("native:zonalstatisticsfb", {'INPUT': sub_basins_layer,'INPUT_RASTER': imperviousness_layer,'RASTER_BAND':1,'COLUMN_PREFIX':'Imp_','STATISTICS':[2],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']            

        return self.subBasinLayerProcessed
    
    def performLFP(self):
        '''
            Calculates the LongestFlowPath for each sub-basin.
        '''
        try:
            self.start_operation()
            self.log_to_qtalsim_tab(f"Calculating the longest flowpath for each sub-basin.", Qgis.MessageLevel.Info) 

            if self.outputFolder is None:
                self.log_to_qtalsim_tab("Please select an output folder.", Qgis.MessageLevel.Critical)
                return
                
            if self.DEMLayer is None:
                selected_layer_name = self.comboboxDEMLayer.currentText()
                if selected_layer_name != self.noLayerSelected:
                    self.DEMLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
                else:
                    self.log_to_qtalsim_tab("Please select a DEM layer to process the sub-basins.", Qgis.MessageLevel.Critical)

            #Water Network Layer
            selected_layer_name = self.comboboxWaterNetwork.currentText()
            if selected_layer_name != self.noLayerSelected:
                self.waterNetworkLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
            else:
                self.log_to_qtalsim_tab("Please select a water-network layer to calculate LFP.", Qgis.MessageLevel.Critical)
            
            #Check if the layers are in same CRS
            dem_crs = self.DEMLayer.crs()
            water_network_crs = self.waterNetworkLayer.crs()
            sub_basin_crs = self.subBasinLayer.crs()

            # Check if all CRS are the same
            if dem_crs == water_network_crs == sub_basin_crs:
                pass
            else:
                self.log_to_qtalsim_tab("Layers have different CRS.", Qgis.MessageLevel.Critical)
                return
                
            #UI Sub-basin
            self.subbasinUIField = self.comboboxUISubBasin.currentText()

            #Burn and Fill DEM-Layer
            self.DEMLayerBurnFill = self.createFilledDEM(self.subBasinLayer, self.DEMLayer, self.waterNetworkLayer, self.outputFolder)
            
            #Get the raw output of LFP
            lfpOutputs = self.create_longestflowpath_raw(self.subBasinLayer, self.DEMLayerBurnFill)   

            #Create final LFPs
            self.create_final_lfp(lfpOutputs)

            #Delete temporary raw files of lfps
            #Does not work correctly yet:
            gc.collect()  # Collect garbage before attempting to remove files

            try:
                for path in self.path_lfp_outputs_raw:
                    # Find layers that correspond to the current path
                    layers_to_remove = [layer for layer in lfpOutputs if layer.dataProvider().dataSourceUri().split('|')[0] == path]

                    # Explicitly delete these layers from memory
                    for layer in layers_to_remove:
                        lfpOutputs.remove(layer)  #Remove from the list first
                        del layer  #Delete the layer reference
                    
                    #Force another garbage collection to ensure the layers are released
                    gc.collect()

                    # Attempt to remove the file
                    if os.path.exists(path):
                        os.remove(path)

            except Exception as first_exception:
                time.sleep(1)  # Wait a bit before trying again

                try:
                    for path in self.path_lfp_outputs_raw:
                        if os.path.exists(path):
                            os.remove(path)
                except Exception as e:
                    self.log_to_qtalsim_tab(f"Error removing {path}: {e}", Qgis.MessageLevel.Info)

            # Delete the file
            if os.path.exists(self.dem_burn_output):
                try:
                    os.remove(self.dem_burn_output)
                except:
                    pass
            
            #Calculate rotation
            try:   
                self.calculateRotation()
            except Exception as e:
                self.log_to_qtalsim_tab(f"Error calculating rotation: {e}. Continuing without calculating rotation.", Qgis.MessageLevel.Warning)
            finally:
                self.lfpFinalLayer.commitChanges()

            self.log_to_qtalsim_tab(f"Finished the calculation of the longest flowpaths. Please check the longest flowpaths and edit the geometries, if necessary. The lengths will be recalculated when saving the sub-basins-layer (Button: Run).", Qgis.MessageLevel.Info)
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.MessageLevel.Critical)
        finally:
            self.end_operation()

    def calculateRotation(self):
        '''
            Calculates the flow direction of the longest flow path and saves it in rotation field.
        '''

        def sample_elevation(point):
            ident = self.DEMLayer.dataProvider().identify(point, QgsRaster.IdentifyFormat.IdentifyFormatValue)
            if ident.isValid():
                return ident.results()[1]
            return None

        self.lfpFinalLayer.startEditing()

        if 'Rotation' not in [f.name() for f in self.lfpFinalLayer.fields()]:
            self.lfpFinalLayer.dataProvider().addAttributes([QgsField('Rotation', QVariant.Double)])
            self.lfpFinalLayer.updateFields()

        rotation_field_index = self.lfpFinalLayer.fields().indexFromName('Rotation')

        # Calculate rotation for each LFP
        for feat in self.lfpFinalLayer.getFeatures():
            geom = feat.geometry()
            if geom.isMultipart():
                lines = geom.asMultiPolyline()
                if not lines or len(lines[0]) < 2:
                    continue  # <-- was return None
                line = lines[0]
            else:
                line = geom.asPolyline()
                if len(line) < 2:
                    continue  # <-- was return None

            pt1 = line[0]
            pt2 = line[-1]
            dz1 = sample_elevation(pt1)
            dz2 = sample_elevation(pt2)

            if dz1 is None or dz2 is None:
                continue

            #Always treat higher point as start (flow goes downhill)
            if dz1 >= dz2:
                start_point, end_point = pt1, pt2
            else:
                start_point, end_point = pt2, pt1

            dx = end_point.x() - start_point.x()
            dy = end_point.y() - start_point.y()

            #Standard compass-style bearing (0° = North, clockwise)
            rotation = (math.degrees(math.atan2(dx, dy)) + 360) % 360

            #Flip to custom convention: 0° = South
            rotation = (rotation + 180) % 360

            if rotation is not None:
                feat.setAttribute(rotation_field_index, rotation)
                self.lfpFinalLayer.updateFeature(feat)

        #self.lfpFinalLayer.commitChanges()

    def createFilledDEM(self, sub_basins_layer, dem_layer, water_network_layer, output_path):
        '''
            Pre-processing step of LFPs
                Burns and fills the DEM
        '''

        #resultDissolve = processing.run("native:dissolve", {'INPUT':sub_basins_layer,'FIELD':[],'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})

        result = processing.run("qgis:deleteholes", {
                'INPUT': sub_basins_layer,
                'OUTPUT': 'TEMPORARY_OUTPUT'
        }, feedback=self.no_feedback)

        sub_basins_layer = result['OUTPUT']
        result = processing.run("gdal:cliprasterbymasklayer", {'INPUT':dem_layer,'MASK':sub_basins_layer,'SOURCE_CRS':None,'TARGET_CRS':None,'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':True,'KEEP_RESOLUTION':False,'SET_RESOLUTION':False,'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':False,'OPTIONS':'','DATA_TYPE':0,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'}, feedback=self.no_feedback)
        dem_layer = QgsRasterLayer(result['OUTPUT'], 'Clipped DEM')
        
        #Get extent and resolution of DEM
        self.dem_extent = dem_layer.extent()
        self.dem_pixel_size_x = dem_layer.rasterUnitsPerPixelX()
        self.dem_pixel_size_y = dem_layer.rasterUnitsPerPixelY()
        self.dem_crs = dem_layer.crs().authid()
        crs_water_network = water_network_layer.crs().authid()
        self.extent = f"{self.dem_extent.xMinimum()},{self.dem_extent.xMaximum()},{self.dem_extent.yMinimum()},{self.dem_extent.yMaximum()}"

        #Rasterize Water Network
        result = processing.run("gdal:rasterize", {'INPUT':water_network_layer,'FIELD':'','BURN':1,'USE_Z':False,'UNITS':1,'WIDTH':self.dem_pixel_size_x,'HEIGHT':self.dem_pixel_size_y,'EXTENT': f"{self.extent}[{crs_water_network}]",'NODATA':0,'OPTIONS':'','DATA_TYPE':5,'INIT':2,'INVERT':False,'EXTRA':'','OUTPUT': 'TEMPORARY_OUTPUT'})
        water_network_rasterized_temp = QgsRasterLayer(result['OUTPUT'],'WaterNetworkRasterized')

        cleaned = processing.run("native:rastercalc", {'LAYERS':[water_network_rasterized_temp],'EXPRESSION':f'if("{water_network_rasterized_temp.name()}@1"= 1, 1, 0)','EXTENT':None,'CELL_SIZE':None,'CRS':None,'OUTPUT':'TEMPORARY_OUTPUT'})
        water_network_rasterized = QgsRasterLayer(cleaned['OUTPUT'],'WaterNetworkRasterized_cleaned')
        QgsProject.instance().addMapLayer(water_network_rasterized)

        #Standardize Raster Layer
        band = 1
        stats = dem_layer.dataProvider().bandStatistics(band, QgsRasterBandStats.Stats.All)
        min_value_dem = stats.minimumValue
        max_value_dem = stats.maximumValue

        dem_std_output = os.path.join(output_path, f'DEMStd1.tif')
        os.makedirs(os.path.dirname(dem_std_output), exist_ok=True)
        processing.run("native:rastercalc", {'LAYERS':[dem_layer],'EXPRESSION':f'("{dem_layer.name()}@1" - {min_value_dem}) / ({max_value_dem} - {min_value_dem})','EXTENT':None,'CELL_SIZE':None,'CRS':None,'OUTPUT':dem_std_output}, feedback=self.no_feedback)

        dem_std_layer = QgsRasterLayer(dem_std_output,'DEMStd')
        QgsProject.instance().addMapLayer(dem_std_layer)

        #Burn Gewässernetz into standardized DEM
        dem_std_burn_output = os.path.join(output_path, f'DEMStdBurn1.tif')
        os.makedirs(os.path.dirname(dem_std_burn_output), exist_ok=True)
        processing.run("native:rastercalc", {'LAYERS':[dem_std_layer, water_network_rasterized],'EXPRESSION':f'"{dem_std_layer.name()}@1" - "{water_network_rasterized.name()}@1"','EXTENT':self.extent,'CELL_SIZE':None,'CRS':None,'OUTPUT':dem_std_burn_output}, feedback=self.no_feedback)

        dem_std_burn_layer = QgsRasterLayer(dem_std_burn_output,'DEMStdBurn')
        QgsProject.instance().addMapLayer(dem_std_burn_layer)

        #Remove layer not needed 
        QgsProject.instance().removeMapLayer(dem_std_layer.id()) #Remove layer

        # Delete the file
        if os.path.exists(dem_std_output):
            try:
                os.remove(dem_std_output)
            except:
                pass

        #Recalculate DEM (from standardized, burned DEM)
        self.dem_burn_output = os.path.join(output_path, 'DEMBurn.tif')
        os.makedirs(os.path.dirname(self.dem_burn_output), exist_ok=True)
        processing.run("native:rastercalc", {'LAYERS':[dem_std_burn_layer,dem_layer],'EXPRESSION':f'"{dem_std_burn_layer.name()}@1"  * "{dem_layer.name()}@1"','EXTENT':None,'CELL_SIZE':None,'CRS':None,'OUTPUT': self.dem_burn_output}, feedback=self.no_feedback)

        dem_burn_layer = QgsRasterLayer(self.dem_burn_output,'DEMBurn')
        QgsProject.instance().addMapLayer(dem_burn_layer)

        #Remove layer not needed 
        QgsProject.instance().removeMapLayer(dem_std_burn_layer.id()) #Remove layer

        # Delete the file
        if os.path.exists(dem_std_burn_output):
            try:
                os.remove(dem_std_burn_output)
            except:
                pass

        #Fill Sinks
        dem_burn_fill_output = os.path.join(output_path, 'DEMBurnFill.tif')
        os.makedirs(os.path.dirname(dem_burn_fill_output), exist_ok=True)
        
        #fillsinkswangliu or fillsinksxxlwangliu
        try:
            #processing.run("sagang:fillsinkswangliu", {'ELEV':dem_burn_layer,'FILLED': dem_burn_fill_output,'FDIR':'TEMPORARY_OUTPUT','WSHED':'TEMPORARY_OUTPUT','MINSLOPE':0.1}, feedback=self.no_feedback)
            processing.run("wbt:FillDepressionsWangAndLiu", {'dem':self.dem_burn_output,'fix_flats':True,'flat_increment':None,'output':dem_burn_fill_output})
        except Exception as e:
            # Catch the specific exception for processing errors
            self.log_to_qtalsim_tab(f"{e}", Qgis.MessageLevel.Critical)
            return
        
        dem_burn_fill_layer = QgsRasterLayer(dem_burn_fill_output,'DEMBurnFill')
        QgsProject.instance().addMapLayer(dem_burn_fill_layer)
        #QgsProject.instance().removeMapLayer(dem_burn_layer.id())
        
        #Remove DEM-burn-layer
        QgsProject.instance().removeMapLayer(water_network_rasterized.id()) #Remove layer
        QgsProject.instance().removeMapLayer(dem_burn_layer.id()) #Remove layer

        return dem_burn_fill_layer

    def create_longestflowpath_raw(self, sub_basins_layer, dem_burn_fill_layer):
        '''
            Utilizes Whitebox' LongestFlowPath to calculate the LFP for every sub-basin.
                LFP is calculated for each sub-basin separately and the LFPs are then merged to one layer later on.        
        '''
        #Start calculation of LongestFlowPath
        lfpOutputs = []
        self.path_lfp_outputs_raw = []

        #Loop over all sub-basins
        for feature in sub_basins_layer.getFeatures():
            subbasin_id = feature[self.subbasinUIField] #get the sub-basin id (= unique identifer) as specified by user
            
            # Create a temporary vector layer for the current sub-basin
            #Create a layer from this sub-basin feature
            subbasin_layer = QgsVectorLayer('Polygon?crs=' + sub_basins_layer.crs().authid(), f'subbasin_{subbasin_id}', 'memory')
            subbasin_provider = subbasin_layer.dataProvider()
            subbasin_provider.addFeatures([feature])
            
            #Delete holes of layer
            result = processing.run("qgis:deleteholes", {
                'INPUT': subbasin_layer,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }, feedback=self.no_feedback)

            subbasin_layer = result['OUTPUT']

            # Clip to the extent of the sub-basin 
            result = processing.run("gdal:cliprasterbymasklayer", {'INPUT':dem_burn_fill_layer,'MASK':subbasin_layer,'SOURCE_CRS':None,'TARGET_CRS':None,'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':True,'KEEP_RESOLUTION':False,'SET_RESOLUTION':False,'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':False,'OPTIONS':'','DATA_TYPE':0,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'}, feedback=self.no_feedback)
            dem_burnfill_clip_layer_path = result['OUTPUT']

            # Load the clipped raster layer into QGIS
            dem_burnfill_clip_layer = QgsRasterLayer(dem_burnfill_clip_layer_path, 'Clipped DEM Burn Fill')
            
            #Get extent and size of clipped DEM layer
            dem_extent_clipped = dem_burnfill_clip_layer.extent()
            dem_pixel_size_x_clipped = dem_burnfill_clip_layer.rasterUnitsPerPixelX()
            dem_pixel_size_y_clipped = dem_burnfill_clip_layer.rasterUnitsPerPixelY()
            dem_crs = dem_burnfill_clip_layer.crs().authid()
            extent_clipped = f"{dem_extent_clipped.xMinimum()},{dem_extent_clipped.xMaximum()},{dem_extent_clipped.yMinimum()},{dem_extent_clipped.yMaximum()}"
            
            # Rasterize the sub-basin using the gdal:rasterize tool            
            result = processing.run("gdal:rasterize", {
                'INPUT': subbasin_layer,
                'FIELD':'',  # Ensure you have a field to use for rasterizing
                'BURN': 1,      # This will burn a value of 1 into the raster
                'UNITS': 1,     # Pixel size units (1 for Georeferenced units)
                'USE_Z':False,
                'WIDTH': dem_pixel_size_x_clipped,
                'HEIGHT': dem_pixel_size_y_clipped,
                'EXTENT': extent_clipped,
                'NODATA': 0,    # Value for no data cells
                'OPTIONS': 'COMPRESS=LZW',
                'DATA_TYPE': 5, # Data type (5 corresponds to GDT_Int32)
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }, feedback=self.no_feedback)

            sub_basin_raster_layer = QgsRasterLayer(result['OUTPUT'],'SubBasinRaster')        
            lfp_output = os.path.join(self.outputFolder, f'TEMPORARY_{subbasin_id}.shp')

            # Ensure the output directory exists
            os.makedirs(os.path.dirname(lfp_output), exist_ok=True)
            try:
                processing.run("wbt:LongestFlowpath", {'dem':dem_burnfill_clip_layer,'basins': sub_basin_raster_layer,'output':lfp_output}, feedback=self.no_feedback)
            except QgsProcessingException as e:
                # Catch the specific exception for processing errors
                self.log_to_qtalsim_tab(
                    "Error: Whitebox might not be installed or configured properly. "
                    "Please ensure Whitebox is available and try again.", 
                    Qgis.MessageLevel.Critical
                )
                return
            #new_layer = QgsVectorLayer(lfp_output,'LFP')

            #Store files to delete them later
            self.path_lfp_outputs_raw.append(lfp_output)
            new_layer = QgsVectorLayer(lfp_output, 'Temporary Layer', 'ogr')

            #Check if the 'BASINID' (= self.basinIDField) field exists, if not, create it
            if not new_layer.fields().indexOf(self.basinIDField) >= 0:
                basin_field = QgsField(self.basinIDField, QVariant.String)
                new_layer.dataProvider().addAttributes([basin_field])
                new_layer.updateFields()

            #Update the 'BASINID' field with the subbasin_id for each feature
            new_layer.startEditing()
            for feature in new_layer.getFeatures():
                feature[self.basinIDField] = subbasin_id
                new_layer.updateFeature(feature)
            new_layer.commitChanges()
            lfpOutputs.append(new_layer)

        return lfpOutputs

    def create_final_lfp(self, lfpOutputs):
        '''
            Takes the LFP of every sub-basin and merges these lines to one layer
        '''
        # Check and filter layers by geometry type
        expected_geom_type = QgsWkbTypes.GeometryType.LineGeometry  # Set the expected geometry type (e.g., LineGeometry)
        filtered_lfpOutputs = []

        for layer in lfpOutputs:
            geom_type = layer.geometryType()
            if geom_type == expected_geom_type:
                filtered_lfpOutputs.append(layer)

        if len(filtered_lfpOutputs) < 1:
            self.log_to_qtalsim_tab("Not enough layers with the expected geometry type to merge.", Qgis.MessageLevel.Warning)
            return
        else:
            # Merge the filtered layers
            lfpLayerTotal = processing.run("native:mergevectorlayers", {
                'LAYERS': filtered_lfpOutputs,
                'OUTPUT': 'memory:'
            }, feedback=self.no_feedback)['OUTPUT']

        #Remove the FID field
        fid_field_index = lfpLayerTotal.fields().indexOf('FID')
        if fid_field_index != -1:
            lfpLayerTotal.dataProvider().deleteAttributes([fid_field_index])
            lfpLayerTotal.updateFields()
            
        # Add a new field for storing the lengths
        length_field = QgsField('length2', QVariant.Double)
        lfpLayerTotal.dataProvider().addAttributes([length_field])
        lfpLayerTotal.updateFields()

        # Calculate the length for each feature
        with edit(lfpLayerTotal):
            for feature in lfpLayerTotal.getFeatures():
                geom = feature.geometry()
                length = geom.length()
                feature['length2'] = length
                lfpLayerTotal.updateFeature(feature)
                #Remove the FID field
        
        fid_field_index = lfpLayerTotal.fields().indexOf('LENGTH')
        if fid_field_index != -1:
            lfpLayerTotal.dataProvider().deleteAttributes([fid_field_index])
            lfpLayerTotal.updateFields()

        # Create a dictionary to store the longest line for each sub-basin
        longest_lines = {}

        # Iterate through each feature and find the longest line for each sub-basin
        for feature in lfpLayerTotal.getFeatures():
            basin_id = feature[self.basinIDField]
            length = feature['length2']
            
            if basin_id not in longest_lines or longest_lines[basin_id]['length2'] < length:
                longest_lines[basin_id] = feature

        #Rename the field 'length2' to 'LENGTH'
        if 'length2' in [field.name() for field in lfpLayerTotal.fields()]:
            with edit(lfpLayerTotal):
                lfpLayerTotal.renameAttribute(lfpLayerTotal.fields().indexFromName('length2'), self.lengthFieldName)

        # Create a new layer to store the longest lines
        crs = lfpLayerTotal.crs().toWkt()
        self.lfpFinalLayer = QgsVectorLayer('LineString?crs=' + crs, 'LFP Final', 'memory')
        provider = self.lfpFinalLayer.dataProvider()

        # Add fields from the original layer to the new layer
        provider.addAttributes(lfpLayerTotal.fields())
        self.lfpFinalLayer.updateFields()
        
        # Add the longest lines to the new layer
        with edit(self.lfpFinalLayer):
            for feature in longest_lines.values():
                try:
                    provider.addFeature(feature)
                except Exception as e:
                    continue
        
        lfp_output_final = os.path.join(self.outputFolder, f'LongestFlowPath.gpkg')
        os.makedirs(os.path.dirname(lfp_output_final), exist_ok=True)
        QgsVectorFileWriter.writeAsVectorFormat(self.lfpFinalLayer, lfp_output_final, "UTF-8", self.lfpFinalLayer.crs(), "GPKG")

        self.log_to_qtalsim_tab(f"LongestFlowPath-layer was saved to: {self.outputFolder}", Qgis.MessageLevel.Info)

        # Add the layer to the QGIS project
        self.lfpFinalLayer = QgsVectorLayer(lfp_output_final, 'LFP Final', 'ogr')
        QgsProject.instance().addMapLayer(self.lfpFinalLayer)


    def DBExport(self):
        try:
            self.subbasinUIField = self.comboboxUISubBasin.currentText()
            if self.textScenarioName.text() is None:
                self.log_to_qtalsim_tab("Please specify a scenario name.", Qgis.MessageLevel.Critical)
            else:
                self.scenarioName = self.textScenarioName.text()

            if self.comboboxNameField.currentText() != 'Select Name-Field':
                self.nameField = self.comboboxNameField.currentText()
            else:
                self.nameField = None
            self.log_to_qtalsim_tab(f"Name-field: {self.nameField}", Qgis.MessageLevel.Info)

            self.DBPath = os.path.join(self.outputFolder, self.dbName + ".db")
            current_path = os.path.dirname(os.path.abspath(__file__))
            source_db = os.path.join(current_path, "DB", "QTalsim.db") 
            shutil.copy(source_db, self.DBPath)

            #Insert new scenario
            conn = sqlite3.connect(self.DBPath)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO Scenario (ScenarioGroupId, DateCreated, Name, Description, ActiveSimulationId, IsUpdateActive, OperationalInfo)
                VALUES (?, datetime('now'), ?, ?, ?, ?, ?)
            """, (1, str(self.scenarioName), "Output of QTalsim", None, 0, None))

            conn.commit()
            conn.close()

            conn = sqlite3.connect(self.DBPath)
            cursor = conn.cursor()
            #Insert ScenarioGroup
            cursor.execute("""
                SELECT ScenarioGroupId, Description, Name FROM Scenario 
                ORDER BY DateCreated DESC LIMIT 1
            """)
            scenario_group_id, description, name = cursor.fetchone()

            # Insert data into ScenarioGroup with current date
            cursor.execute("""
                INSERT INTO ScenarioGroup (Id, Description, Name, DateCreated)
                VALUES (?, ?, ?, datetime('now'))
            """, (scenario_group_id, description, name))

            conn.commit()
            conn.close()
            #Insert SystemElement table
            conn = sqlite3.connect(self.DBPath)
            cursor = conn.cursor()

            #Retrieve the last inserted ScenarioId
            cursor.execute("SELECT Id FROM Scenario ORDER BY DateCreated DESC LIMIT 1")
            scenario = cursor.fetchone()
            
            target_crs = QgsCoordinateReferenceSystem("EPSG:4326") #Transform sub-basin's geometry to WGS84 for Talsim
            source_crs = self.subBasinLayerProcessed.crs()

            #Set up the transformation
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

            scenario_id = scenario[0]  #ScenarioId for new records
            fields = [field.name() for field in self.subBasinLayerProcessed.fields()]
            for feature in self.subBasinLayerProcessed.getFeatures():
                element_identifier = feature[self.subbasinUIField][1:] if isinstance(feature[self.subbasinUIField], str) and feature[self.subbasinUIField] else None # ElementIdentifier & Name
                name = feature[self.nameField] if isinstance(feature[self.nameField], str) and feature[self.nameField] else None
                geometry = feature.geometry()
                
                #Transform geometry to EPSG:4326
                geometry.transform(transform)
                
                #Calculate the centroid (Latitude & Longitude)
                centroid = geometry.centroid().asPoint()
                latitude, longitude = centroid.y(), centroid.x()
                
                #Convert to WKT MultiPolygon
                wkt_multipolygon = geometry.asWkt()

                rotation = feature['Rotation'] if 'Rotation' in fields else 0

                #Insert into SystemElement table
                cursor.execute("""
                    INSERT INTO SystemElement (
                        ScenarioId, ElementIdentifier, Name, ElementType, ElementTypeCharacter,
                        Latitude, Longitude, Geometry, Rotation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (scenario_id, element_identifier, name, 2, "A", 
                    latitude, longitude, wkt_multipolygon, rotation))

                #Get the created SystemElementId
                system_element_id = cursor.lastrowid

                #Extract SubBasin fields (only those explicitly mentioned)
                area = feature[self.areaFieldName] if self.areaFieldName in fields else None
                raw_value_imp = feature[self.imperviousFieldName] if self.imperviousFieldName in fields else None
                imperviousness = raw_value_imp / 100 if raw_value_imp is not None else None
                max_height = feature['Height_max'] if 'Height_max' in fields else None
                min_height = feature['Height_min'] if 'Height_min' in fields else None

                # Flow Length check
                length = feature[self.lengthFieldName] if self.lengthFieldName in fields else None

                # Insert into SubBasin table
                cursor.execute("""
                    INSERT INTO SubBasin (
                        SystemElementId, Area, FlowLength, Imperviousness, MaxHeight, MinHeight, CalculationMethod
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (system_element_id, area, length, imperviousness, max_height, min_height, 3))
            conn.commit()
            conn.close()
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.MessageLevel.Critical)
            
    def asciiExport(self):
        '''
            If the user selects asciiExport, an EZG-file is exported to the output-folder and the specified filename
        '''
        try:
            #UI Sub-basin
            self.subbasinUIField = self.comboboxUISubBasin.currentText()

            #The template file of EZG-file holds a line that defines the field lengths and spaces between lengths
            def parse_definition_linev1(line):
                field_lengths = []
                inside_field = False
                current_length = 0

                for char in line:
                    if char == '<': #new field
                        inside_field = True
                        current_length = 0 
                        current_length += 1
                    
                    elif char == '>': #field closed
                        inside_field = False
                        current_length += 1
                        field_lengths.append(current_length)  # Append length after closing '>'
                    
                    elif inside_field and char == '-':
                        current_length += 1
                    
                    elif char == '+': #fields with only one character
                        field_lengths.append(1)
                        
                return field_lengths

            #Define the characters between the fields 
            def parse_inter_field_charactersv1(definition_line):
                inter_field_characters = []
                temp_str = ""
                collecting = True

                for char in definition_line:
                    if char == '>':
                        collecting = True  # Start collecting characters after '>'
                    elif char == '<':
                        if collecting:
                            # Add the collected characters to the list
                            inter_field_characters.append(temp_str)
                            temp_str = ""
                        collecting = False  # Stop collecting characters
                    elif char == '+' and collecting:
                        inter_field_characters.append(temp_str)
                        temp_str = ""
                        collecting = True
                    elif collecting:
                        if char == '*':
                            char = " "  # Replace '*' with space
                        if char == '-':
                            char = " "  # Replace '-' with space
                        temp_str += char
                return inter_field_characters

            #Defines the length of the fields
            def format_field(value, length):
                if isinstance(value, float):
                    # Round the float to a maximum of 3 decimal places
                    # Adjust the precision to ensure the total length fits within 'length'
                    precision = min(3, length - 2)  # Subtract 2 for the digit and decimal point
                    value_str = f"{value:.{precision}f}"
                elif value is None or str(value).strip().upper() == 'NULL':
                    value_str = ""
                else:
                    value_str = str(value)
                return value_str[:length].rjust(length)

            if self.asciiFilename:
                self.log_to_qtalsim_tab("Exporting ASCII-files.", Qgis.MessageLevel.Info)

                current_path = os.path.dirname(os.path.abspath(__file__))
                ezgPath = os.path.join(current_path, "talsim_parameter", "template.EZG")
                
                with open(ezgPath, 'r', encoding='iso-8859-1') as ezgFile:
                    templateEzgContent = ezgFile.readlines()
                    definition_line = templateEzgContent[-1].strip()
                field_lengths = parse_definition_linev1(definition_line)

                outputPathEzg = os.path.join(self.outputFolder, f"QTalsim.EZG")

                data = []                    

                fields = [field.name() for field in self.subBasinLayerProcessed.fields()]

                for feature in self.subBasinLayerProcessed.getFeatures():
                    if self.lengthFieldName not in fields:
                        length = None
                    else:
                        length = feature[self.lengthFieldName]
                    #A: Fläche
                    #VG: Versiegelungsgrad / Anteil der undurchlässigen Fläche [%]
                    layer_data = {'Bez' : feature[self.subbasinUIField], 'KNG': None,
                                  'A' : feature[self.areaFieldName], 'VG' : feature[self.imperviousFieldName], 'Ho' : feature['Height_max'],
                                    'Hu': feature['Height_min'], 'L' : length, #Gebietskenngrößen
                                  'Datei': None, #N
                                  'Kng' : None, 'Sum': None, 'Datei': None, 'HYO': None, #Verdunstung
                                  'Kng': None, 'Tem' : None, 'JGG': None, 'TGG': None, 'Datei': None, #Temperatur
                                  'qB': None, 'JGG' : None, #QBASIS
                                  'PSI' : None, #PSI (1)
                                  'CN': None, 'VorRg': None, #SCS (2)
                                  'BF0' : None, #BF0 (3)
                                  'R': None, 'K(VG)': None, 'K1': None, 'K2': None, 'Int': None, 'Bas': None, #Retentionskonstanten
                                  'con': None, 'Expo': None, #SCS
                                  'Beta1': None, 'Beta2': None,  #Aufteilung
                                   'Muld': None, 'SCS': None, 'SCH': None, 'Int2_J/N': None, 'Int2_h': None, 
                                   'QUrb': None, 'QNat': None, 'QInt': None, 'QIn2': None, 'QBas': None, 'QGWt': None, #Ablaufzuordnung: Gibt nach Objekt
                                   'Bas2_J/N': None, 'Bas2_h': None, 'Beta': None, #Grundwasser-Tief
                                   'KNG': None, 'Datei_Abgabe': None, 'Datei_WaEquiva': None, #Schnee
                                   'Precip': None #Scale
                                   }
                    data.append(layer_data)

                formatted_data = []
                inter_field_characters = parse_inter_field_charactersv1(definition_line)  
                for row in data:
                    formatted_row = ""
                    for i, (length, inter_char) in enumerate(zip(field_lengths, inter_field_characters + [''])):
                        field_name = list(row.keys())[i] if i < len(row) else ""
                        field_value = row.get(field_name,"")
                        formatted_row += inter_char  # Add inter-field characters
                        formatted_row += format_field(field_value, length)
                    formatted_row += "|"
                    formatted_row += "\n"
                    formatted_data.append(formatted_row)

                completeContentEzg = templateEzgContent + ['\n'] + formatted_data + [definition_line]

                with open(outputPathEzg, 'w', encoding='iso-8859-1', errors='replace') as outputEzg:
                    outputEzg.writelines(completeContentEzg)

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.MessageLevel.Critical)

#To be improved:
class NoFeedback(QgsProcessingFeedback):
    def reportError(self, error, fatalError=False):
        pass  # Override to do nothing

    def pushFormattedMessage(self, info, level=Qgis.MessageLevel.Info):
        pass  # Override to do nothing

    def pushInfo(self, info):
        pass  # Override to do nothing

    def pushCommandInfo(self, command):
        pass  # Override to do nothing

    def setProgressText(self, text):
        pass  # Override to do nothing

    def setProgress(self, progress):
        pass  # Override to do nothing
        




        
                    

