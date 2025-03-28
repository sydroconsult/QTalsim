import os
from qgis.PyQt import uic, QtWidgets
import pandas as pd
from qgis.core import QgsVectorLayer, QgsProject, Qgis, QgsField, QgsVectorFileWriter
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog, QInputDialog
import processing

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qtalsim_landuse.ui'))

class LanduseAssignmentDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, mainPluginInstance, parent=None):
        """Constructor."""
        super(LanduseAssignmentDialog, self).__init__(parent)
        self.iface = iface
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.mainPlugin = mainPluginInstance
        self.initialize_parameters()
    
    def initialize_parameters(self):

        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.start_operation = self.mainPlugin.start_operation
        self.end_operation = self.mainPlugin.end_operation
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers

        self.fillClippingLayerCombobox()
        self.connectButtontoFunction(self.onInputFolder, self.selectInputFolder) 
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFile)
        self.connectButtontoFunction(self.onCreateLanduseLayer, self.landuseMapping)
        
        current_path = os.path.dirname(os.path.abspath(__file__))
        landuseAssignmentPath = os.path.join(current_path, "talsim_parameter", "atkis_talsim_zuordnung.csv")
        self.dfLanduseAssignmentTalsim = pd.read_csv(landuseAssignmentPath,delimiter = ';')

        self.landuseLayer = None
        self.merged_layer = None
        list_layers = ['sie02_f', 'ver01_f', 'ver03_f', 'ver04_f', 'ver05_f', 'gew01_f', 'veg01_f', 'veg02_f', 'veg03_f']
    
    def fillClippingLayerCombobox(self):
        '''
            Fills all comboboxes with layers
        '''

        self.polygonLayers, _ = self.getAllLayers(QgsProject.instance().layerTreeRoot())

        #Sub-basins layer
        self.comboboxClippingLayer.clear() #clear combobox EZG from previous runs
        self.comboboxClippingLayer.addItem("Select Clipping Layer")
        self.comboboxClippingLayer.addItems([layer.name() for layer in self.polygonLayers])

    def selectInputFolder(self):
        '''
            Function to select the output folder. 
        '''
        self.inputFolder = None
        self.inputFolder = QFileDialog.getExistingDirectory(self, "Select Folder","") #, options=options
        if self.inputFolder:
            self.inputPath.setText(self.inputFolder)

            self.log_to_qtalsim_tab(f"Selected input folder: {self.inputFolder}", Qgis.Info)

    def selectOutputFile(self):
        '''
            Function to select the output folder. 
        '''
        self.outputFolder = QFileDialog.getExistingDirectory(self, "Select Folder","")
        if self.outputFolder:
            #Prompt the user for the GeoPackage file name
            self.gpkg_name, ok = QInputDialog.getText(self, "GeoPackage Name", "Enter name for the GeoPackage (without .gpkg):")

            if ok and self.gpkg_name.strip():
                self.gpkg_name = self.gpkg_name.strip()
                if not self.gpkg_name.endswith(".gpkg"):
                    self.gpkg_name += ".gpkg"

                #Create the full output path
                full_path = os.path.join(self.outputFolder, self.gpkg_name)
                self.gpkgOutputPath = full_path
                self.outputPath.setText(full_path)

    def mergeAndClip(self):
        try:
            valid_layers = self.dfLanduseAssignmentTalsim[
                self.dfLanduseAssignmentTalsim["Talsim Landnutzung"].str.lower() != "löschen"
            ]["Layer"].unique()

            all_layers = self.dfLanduseAssignmentTalsim["Layer"].unique()

            #Keep all layers that have at least one valid entry
            self.relevantFiles = [layer for layer in all_layers if layer in valid_layers]

            shapefile_paths = []
            for root, _, files in os.walk(self.inputFolder):
                for file in files:
                    if file.endswith(".shp"):
                        file_name_without_ext = os.path.splitext(file)[0]
                        if file_name_without_ext in self.relevantFiles:
                            shapefile_paths.append(os.path.join(root, file))
            
            #Create layers from the shapefiles
            layersToMerge = []
            for shp_path in shapefile_paths:
                layer_name = os.path.splitext(os.path.basename(shp_path))[0]
                layer = QgsVectorLayer(shp_path, layer_name, "ogr")
                if layer.isValid():
                    layersToMerge.append(layer)
            
            #Merge the layers
            result_merge = processing.run("native:mergevectorlayers", {'LAYERS': layersToMerge,  'OUTPUT': 'TEMPORARY_OUTPUT'}, feedback=None)
            self.merged_layer = result_merge['OUTPUT']
            clipping_layer_name = self.comboboxClippingLayer.currentText()
            if clipping_layer_name == "Select Clipping Layer":
                clipping_layer = None
            else:
                clipping_layer = QgsProject.instance().mapLayersByName(clipping_layer_name)[0] #Get the clipping layer

                #Clip the merged ATKIS-layer
                try:
                    self.clippedLayer = processing.run("native:clip", {
                            'INPUT': self.merged_layer,
                            'OVERLAY': clipping_layer,
                            'OUTPUT': 'TEMPORARY_OUTPUT'
                    }, feedback=None)['OUTPUT']

                except: #Clipping often fails due to invalid geometries
                    has_multipart = False
                    for feature in self.merged_layer.getFeatures():
                        geom = feature.geometry()
                        if geom.isMultipart():
                            has_multipart = True
                            break
                        
                    if has_multipart:
                        self.merged_layer = processing.run("native:multiparttosingleparts", {'INPUT': self.merged_layer,'OUTPUT': 'TEMPORARY_OUTPUT'}, feedback=None)['OUTPUT']
                        self.merged_layer, _ = self.make_geometries_valid(self.merged_layer)

                    self.clippedLayer = processing.run("native:clip", {
                            'INPUT': self.merged_layer,
                            'OVERLAY': clipping_layer,
                            'OUTPUT': 'TEMPORARY_OUTPUT'
                    }, feedback=None)['OUTPUT']

                if self.clippedLayer:
                    self.landuseLayer = self.clippedLayer
                else:
                    self.landuseLayer = self.merged_layer
        except Exception as e:
            self.log_to_qtalsim_tab("Error during merging and clipping: " + str(e), Qgis.Critical)
        
        
    def landuseMapping(self):
        try:
            self.start_operation()
            self.mergeAndClip()
            self.atkisToTalsimMapping()
            self.exportGeopackage()
        except Exception as e:
            self.log_to_qtalsim_tab("Error during landuse mapping: " + str(e), Qgis.Critical)
        finally:
            self.end_operation()
            self.log_to_qtalsim_tab("Land use mapping finished", Qgis.Info)

    def atkisToTalsimMapping(self):
        '''
            Function to map the ATKIS landuse to Talsim land use
        '''

        #Mapping of ATKIS landuse to Talsim landuse
        if 'OBJART_NEU' not in [f.name() for f in self.landuseLayer.fields()]:
            self.landuseLayer.dataProvider().addAttributes([QgsField('OBJART_NEU', QVariant.String)])
            self.landuseLayer.updateFields()
        mapping = {}
        deleted_matches = []

        for _, row in self.dfLanduseAssignmentTalsim.iterrows():
            objart = row["ATKIS-Bezeichnung"]
            code_column = row["Code-Spalte"]
            code_value = row["Codes"]
            talsim_landuse = row["Talsim Landnutzung"]

            if talsim_landuse.lower() == "löschen":
                continue 

            key = (objart, code_column, code_value)
            mapping[key] = talsim_landuse

        # Start editing the layer
        self.landuseLayer.startEditing()

        for feature in self.landuseLayer.getFeatures():
            objart_txt = feature["OBJART_TXT"]

            #Try to find a match with code
            matched = False
            for key, landuse in mapping.items():
                objart, code_col, code_val = key

                if objart_txt != objart:
                    continue

                #Check if feature has the code column
                if pd.notna(code_col) and code_col not in feature.fields().names():
                    continue

                #If code is "-", ignore the code check
                if code_val == "-":
                    feature["OBJART_NEU"] = landuse
                    matched = True
                    break

                #Match by code value
                feature_code = feature[code_col]
                if pd.isna(feature_code):
                    continue

                if str(feature_code) == str(code_val):
                    feature["OBJART_NEU"] = landuse
                    matched = True
                    break

            #If not matched, optionally leave as is or assign fallback
            if not matched:
                feature["OBJART_NEU"] = objart_txt
                self.log_to_qtalsim_tab(f"Could not find a match for {objart_txt}", Qgis.Warning)

            self.landuseLayer.updateFeature(feature)
        
        self.landuseLayer.commitChanges()

    def exportGeopackage(self):

        #gpkgOutputPath = os.path.join(self.outputFolder, self.gpkg_name)
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        layer_name_in_gpkg = "Landuse"
        options.layerName = layer_name_in_gpkg  #Name of the layer inside the GeoPackage
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

        result, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
            self.landuseLayer,
            self.gpkgOutputPath,
            QgsProject.instance().transformContext(),
            options
        )

        if result == QgsVectorFileWriter.NoError:
            self.log_to_qtalsim_tab(f"Exported to {self.gpkgOutputPath}", Qgis.Info)

        exported_layer = QgsVectorLayer(f"{self.gpkgOutputPath}|layername={layer_name_in_gpkg}", layer_name_in_gpkg, "ogr")
        if exported_layer.isValid():
            QgsProject.instance().addMapLayer(exported_layer)

        #Dissolve Landuse Layer
        landuseLayerDissolved = processing.run("native:dissolve", {
            'INPUT': self.landuseLayer,
            'FIELD': ['OBJART_NEU'],
            'SEPARATE_DISJOINT': False,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        #Delete all fields except 'OBJART_NEU'
        fields = landuseLayerDissolved.fields()
        fields_to_delete = [i for i, f in enumerate(fields) if f.name() != 'OBJART_NEU']

        if landuseLayerDissolved.dataProvider().deleteAttributes(fields_to_delete):
            landuseLayerDissolved.updateFields()

        #Export dissolved layer to same GeoPackage under a new name
        layer_name_dissolved = "LanduseDissolved"
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer_name_dissolved
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer  # Add as new layer

        result, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
            landuseLayerDissolved,
            self.gpkgOutputPath,
            QgsProject.instance().transformContext(),
            options
        )

        if result == QgsVectorFileWriter.NoError:
            uri = f"{self.gpkgOutputPath}|layername={layer_name_dissolved}"
            dissolved_layer = QgsVectorLayer(uri, layer_name_dissolved, "ogr")

            if dissolved_layer.isValid():
                QgsProject.instance().addMapLayer(dissolved_layer)

                self.log_to_qtalsim_tab(f"Exported dissolved layer with layer name {layer_name_dissolved} to {self.gpkgOutputPath}", Qgis.Info)       

        
