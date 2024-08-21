import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog, QDialogButtonBox
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer, QgsMapLayer, QgsWkbTypes, QgsRasterLayer, QgsVectorLayer, QgsRasterBandStats, QgsField, QgsVectorFileWriter, edit, Qgis, QgsProcessingFeedback, QgsProcessingException
from qgis.PyQt.QtCore import pyqtSignal, QVariant
import processing
import webbrowser
import gc #Garbage collection
import time
import sys

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
        self.finalButtonBox.button(QDialogButtonBox.Help).setText('Help')

    def initialize_parameters(self):
        
        #Initialize variables
        self.polygonLayers = None
        self.rasterLayers = None
        self.noLayerSelected = "No Layer selected"
        self.outputFolder = None
        self.outputPath.clear()
        self.no_feedback = NoFeedback()

        #Main Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers
        self.start_operation = self.mainPlugin.start_operation
        self.end_operation = self.mainPlugin.end_operation
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab

        #Connect Buttons to Functions
        self.connectButtontoFunction(self.onRun, self.performLFP)
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFolder) 
        self.connectButtontoFunction(self.finalButtonBox.button(QDialogButtonBox.Help), self.openDocumentation)

        self.log_to_qtalsim_tab(
            "This feature calculates the longest flowpath for each sub-basin in the input layer. "
            "Please ensure that both SAGA GIS and WhiteboxTools are installed and properly configured. "
            "For detailed instructions, click the Help button.", 
            Qgis.Info
        )        
        #Fill Comboboxes
        self.comboboxUISubBasin.clear()
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
    
    def openDocumentation(self):
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

        #Sub-basins
        self.comboboxSubBasinLayer.clear() #clear combobox EZG from previous runs
        self.comboboxSubBasinLayer.addItem(self.noLayerSelected)
        self.comboboxSubBasinLayer.addItems([layer.name() for layer in self.polygonLayers])
        self.safeConnect(self.comboboxSubBasinLayer.currentIndexChanged, self.on_subbasin_layer_changed) #Refill the sub-basin combobox whenever user selects different layer

        #DEM Layer
        self.comboboxDEMLayer.clear() #clear combobox from previous runs
        self.comboboxDEMLayer.addItem(self.noLayerSelected)
        self.comboboxDEMLayer.addItems([layer.name() for layer in self.rasterLayers])

        #Water network
        self.comboboxWaterNetwork.clear() #clear combobox from previous runs
        self.comboboxWaterNetwork.addItem(self.noLayerSelected)
        self.comboboxWaterNetwork.addItems([layer.name() for layer in self.lineLayers])

    def on_subbasin_layer_changed(self):
        '''
            Fill the sub-basin-UI-combobox
        '''
        selected_layer_name = self.comboboxSubBasinLayer.currentText()
        if selected_layer_name != self.noLayerSelected and selected_layer_name is not None:
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            if layers:
                self.subBasinLayer = layers[0]

                self.comboboxUISubBasin.clear()
                self.fieldsSubbasinLayer = [field.name() for field in self.subBasinLayer.fields()]
                self.comboboxUISubBasin.addItems([str(field) for field in self.fieldsSubbasinLayer])

    def performLFP(self):
        '''
            Calculates the LongestFlowPath for each sub-basin.
        '''
        self.start_operation()
        try:
            self.log_to_qtalsim_tab(f"Calculating the longest flowpath for each sub-basin.", Qgis.Info) 
            #DEM Layer
            selected_layer_name = self.comboboxDEMLayer.currentText()
            self.DEMLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]

            #Water Network Layer
            selected_layer_name = self.comboboxWaterNetwork.currentText()
            self.waterNetworkLayer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
            
            #Check if the layers are in same CRS
            dem_crs = self.DEMLayer.crs()
            water_network_crs = self.waterNetworkLayer.crs()
            sub_basin_crs = self.subBasinLayer.crs()

            # Check if all CRS are the same
            if dem_crs == water_network_crs == sub_basin_crs:
                self.log_to_qtalsim_tab("All layers are in the same CRS.", Qgis.Info)
            else:
                self.log_to_qtalsim_tab("Layers have different CRS.", Qgis.Error)
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
            #Does not work yet:

            gc.collect()  # Collect garbage before attempting to remove files

            try:
                for path in self.path_lfp_outputs_raw:
                    # Find layers that correspond to the current path
                    layers_to_remove = [layer for layer in lfpOutputs if layer.dataProvider().dataSourceUri().split('|')[0] == path]

                    # Explicitly delete these layers from memory
                    for layer in layers_to_remove:
                        lfpOutputs.remove(layer)  # Remove from the list first
                        del layer  # Delete the layer reference
                    
                    # Force another garbage collection to ensure the layers are released
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
                    self.log_to_qtalsim_tab(f"Error removing {path}: {e}", Qgis.Info)

            # Delete the file
            if os.path.exists(self.dem_burn_output):
                try:
                    os.remove(self.dem_burn_output)
                except:
                    pass


            self.log_to_qtalsim_tab(f"Finished the calculation of the longest flowpaths. The output-files were saved to {self.outputFolder}.", Qgis.Info)
        
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        
        finally:
            self.end_operation()

    def createFilledDEM(self, sub_basins_layer, dem_layer, water_network_layer, output_path):
        '''
            Burns and fills the DEM
        '''

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
        result = processing.run("gdal:rasterize", {'INPUT':water_network_layer,'FIELD':'','BURN':1,'USE_Z':False,'UNITS':1,'WIDTH':self.dem_pixel_size_x,'HEIGHT':self.dem_pixel_size_y,'EXTENT': f"{self.extent}[{crs_water_network}]",'NODATA':None,'OPTIONS':'','DATA_TYPE':0,'INIT':None,'INVERT':False,'EXTRA':'','OUTPUT': 'TEMPORARY_OUTPUT'}, feedback=self.no_feedback)
        water_network_rasterized = QgsRasterLayer(result['OUTPUT'],'WaterNetworkRasterized')
        QgsProject.instance().addMapLayer(water_network_rasterized)

        #Standardize Raster Layer
        band = 1
        stats = dem_layer.dataProvider().bandStatistics(band, QgsRasterBandStats.All)
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
            processing.run("sagang:fillsinkswangliu", {'ELEV':dem_burn_layer,'FILLED': dem_burn_fill_output,'FDIR':'TEMPORARY_OUTPUT','WSHED':'TEMPORARY_OUTPUT','MINSLOPE':0.1}, feedback=self.no_feedback)
        except QgsProcessingException as e:
            # Catch the specific exception for processing errors
            self.log_to_qtalsim_tab(
                "Error: SAGA GIS might not be installed or configured properly. "
                "Please ensure SAGA is available and try again.", 
                Qgis.Critical
            )
            return
        
        dem_burn_fill_layer = QgsRasterLayer(dem_burn_fill_output,'DEMBurnFill')
        QgsProject.instance().addMapLayer(dem_burn_fill_layer)
        #QgsProject.instance().removeMapLayer(dem_burn_layer.id())
        
        #Remove DEM-burn-layer
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
                    Qgis.Critical
                )
                return
            #new_layer = QgsVectorLayer(lfp_output,'LFP')

            #Store files to delete them later
            self.path_lfp_outputs_raw.append(lfp_output)
            new_layer = QgsVectorLayer(lfp_output, 'Temporary Layer', 'ogr')

            # Check if the 'BASIN' field exists, if not, create it
            if not new_layer.fields().indexOf('BASINID') >= 0:
                basin_field = QgsField('BASINID', QVariant.String)
                new_layer.dataProvider().addAttributes([basin_field])
                new_layer.updateFields()

            # Update the 'BASIN' field with the subbasin_id for each feature
            new_layer.startEditing()
            for feature in new_layer.getFeatures():
                feature['BASINID'] = subbasin_id
                new_layer.updateFeature(feature)
            new_layer.commitChanges()
            lfpOutputs.append(new_layer)

        return lfpOutputs

    def create_final_lfp(self, lfpOutputs):
        '''
            Takes the LFP of every sub-basin and merges these lines to one layer
        '''
        # Check and filter layers by geometry type
        expected_geom_type = QgsWkbTypes.LineGeometry  # Set the expected geometry type (e.g., LineGeometry)
        filtered_lfpOutputs = []

        for layer in lfpOutputs:
            geom_type = layer.geometryType()
            if geom_type == expected_geom_type:
                filtered_lfpOutputs.append(layer)

        if len(filtered_lfpOutputs) < 1:
            self.log_to_qtalsim_tab("Not enough layers with the expected geometry type to merge.", Qgis.Warning)
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
            basin_id = feature['BASINID']
            length = feature['length2']
            
            if basin_id not in longest_lines or longest_lines[basin_id]['length2'] < length:
                longest_lines[basin_id] = feature

        #Rename the field 'length2' to 'LENGTH'
        if 'length2' in [field.name() for field in lfpLayerTotal.fields()]:
            with edit(lfpLayerTotal):
                lfpLayerTotal.renameAttribute(lfpLayerTotal.fields().indexFromName('length2'), 'LENGTH')

        # Create a new layer to store the longest lines
        crs = lfpLayerTotal.crs().toWkt()
        lfpFinalLayer = QgsVectorLayer('LineString?crs=' + crs, 'LFP Final', 'memory')
        provider = lfpFinalLayer.dataProvider()

        # Add fields from the original layer to the new layer
        provider.addAttributes(lfpLayerTotal.fields())
        lfpFinalLayer.updateFields()
        
        # Add the longest lines to the new layer
        with edit(lfpFinalLayer):
            for feature in longest_lines.values():
                try:
                    provider.addFeature(feature)
                except Exception as e:
                    continue
        
        lfp_output_final = os.path.join(self.outputFolder, f'LongestFlowPath.gpkg')
        os.makedirs(os.path.dirname(lfp_output_final), exist_ok=True)
        QgsVectorFileWriter.writeAsVectorFormat(lfpFinalLayer, lfp_output_final, "UTF-8", lfpFinalLayer.crs(), "GPKG")

        # Add the layer to the QGIS project
        permanent_layer = QgsVectorLayer(lfp_output_final, 'LFP Final', 'ogr')
        QgsProject.instance().addMapLayer(permanent_layer)

#To be improved:
class NoFeedback(QgsProcessingFeedback):
    def reportError(self, error, fatalError=False):
        pass  # Override to do nothing

    def pushFormattedMessage(self, info, level=Qgis.Info):
        pass  # Override to do nothing

    def pushInfo(self, info):
        pass  # Override to do nothing

    def pushCommandInfo(self, command):
        pass  # Override to do nothing

    def setProgressText(self, text):
        pass  # Override to do nothing

    def setProgress(self, progress):
        pass  # Override to do nothing
        




        
                    

