import os
from qgis.PyQt import uic, QtWidgets
import pandas as pd
from qgis.core import QgsVectorLayer, QgsProject, Qgis, QgsField, QgsVectorFileWriter
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog, QInputDialog, QDialogButtonBox
import processing
import webbrowser
import textwrap

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
        self.make_geometries_valid = self.mainPlugin.make_geometries_valid #Function to make geometries valid

        self.atkisLanduse = "ATKIS Landnutzung"
        self.lbmLandcover = "Digitales Landbedeckungsmodell"
        self.comboboxLanduseSource.clear()
        self.comboboxLanduseSource.addItem(self.lbmLandcover)
        self.comboboxLanduseSource.addItem(self.atkisLanduse)
        self.comboboxLanduseSource.currentIndexChanged.connect(self.updateInputWidget)
        
        self.textHelp.setOpenExternalLinks(True)
        self.textAtkis = textwrap.dedent('''
                        This plugin feature maps ATKIS land use data to Talsim land use categories. 
                        You must provide a folder containing all relevant ATKIS layers (e.g., veg01_f, sie01_f, etc.). 
                        The plugin automatically detects the necessary files and merges them into a single land use layer. 
                        Optionally, you can specify a clipping layer to limit the extent of the merged result.
                        ''').strip()
        
        self.textLBM = textwrap.dedent('''
                        This plugin feature maps <a href="http://bit.ly/46K4sfd">LBM-DE2021 land cover data</a> to Talsim land use categories. 
                        You must provide a layer containing the LBM land cover data. 
                        Optionally, you can specify a clipping layer to limit the extent of the output Talsim land use layer.
                        ''').strip()
        self.textHelp.clear()
        self.textHelp.setHtml(self.textLBM)
        self.fillLayerCombobox()
        self.connectButtontoFunction(self.onInputFolder, self.selectInputFolder) 
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFile)
        self.connectButtontoFunction(self.onCreateLanduseLayer, self.landuseMapping)
        self.connectButtontoFunction(self.onHelp.button(QDialogButtonBox.Help), self.openDocumentation)
        
        current_path = os.path.dirname(os.path.abspath(__file__))
        landuseAssignmentPathAtkis = os.path.join(current_path, "talsim_parameter", "atkis_talsim_zuordnung.csv")
        self.dfLanduseAssignmentTalsim = pd.read_csv(landuseAssignmentPathAtkis,delimiter = ';')

        landuseAssignmentPathLBM = os.path.join(current_path, "talsim_parameter", "lbm_talsim_zuordnung.csv")
        self.dfLanduseAssignmentTalsimLBM = pd.read_csv(landuseAssignmentPathLBM,delimiter = ';')

        self.landuseLayer = None
        self.merged_layer = None
        list_layers = ['sie02_f', 'ver01_f', 'ver03_f', 'ver04_f', 'ver05_f', 'gew01_f', 'veg01_f', 'veg02_f', 'veg03_f']
    
    def openDocumentation(self):
        '''
            Connected with help-button.
        '''
        webbrowser.open('https://sydroconsult.github.io/QTalsim/doc_landuse.html')

    def fillLayerCombobox(self):
        '''
            Fills all comboboxes with layers
        '''

        self.polygonLayers, _ = self.getAllLayers(QgsProject.instance().layerTreeRoot())

        #Sub-basins layer
        self.comboboxClippingLayer.clear() #clear combobox EZG from previous runs
        self.comboboxClippingLayer.addItem("Select Clipping Layer")
        self.comboboxClippingLayer.addItems([layer.name() for layer in self.polygonLayers])

        #Landbedeckung layer
        self.comboboxLayerLandbedeckung.clear() #clear combobox EZG from previous runs
        self.comboboxLayerLandbedeckung.addItem("Select Layer")
        self.comboboxLayerLandbedeckung.addItems([layer.name() for layer in self.polygonLayers])

    def updateInputWidget(self):
        selected_index = self.comboboxLanduseSource.currentIndex()
        self.stackedWidget.setCurrentIndex(selected_index)
        self.textHelp.clear()
        self.textHelp.document().clear()
        if self.comboboxLanduseSource.currentText() == self.atkisLanduse:
            self.textHelp.setText(self.textAtkis)
        elif self.comboboxLanduseSource.currentText() == self.lbmLandcover:
            self.textHelp.setHtml(self.textLBM)
            

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

    def mergeAndClipATKIS(self):
        '''
            Function to merge the shapefiles in the input folder and optionally clip them with the selected layer.
        '''
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
            QgsProject.instance().addMapLayer(self.merged_layer)
            clipped_layer = None
            clipped_layer = self.clipLanduseLayer(self.merged_layer)
            
            if clipped_layer:
                self.landuseLayer = clipped_layer
            else:
                self.landuseLayer = self.merged_layer

        except Exception as e:
            self.log_to_qtalsim_tab("Error during merging and clipping: " + str(e), Qgis.Critical)

    def clipLanduseLayer(self, layer_to_clip):
        '''
            Function to clip the input land use layer with the selected clipping layer.
        '''
        clipping_layer_name = self.comboboxClippingLayer.currentText()
        if clipping_layer_name == "Select Clipping Layer":
            clipping_layer = None
            self.log_to_qtalsim_tab("No clipping layer selected.", Qgis.Critical)
        else:
            clipping_layer = QgsProject.instance().mapLayersByName(clipping_layer_name)[0] #Get the clipping layer

            #Clip the merged ATKIS-layer
            try:
                clippedLayer = processing.run("native:clip", {
                        'INPUT': layer_to_clip,
                        'OVERLAY': clipping_layer,
                        'OUTPUT': 'TEMPORARY_OUTPUT'
                }, feedback=None)['OUTPUT']

            except: #Clipping often fails due to invalid geometries
                has_multipart = False
                for feature in layer_to_clip.getFeatures():
                    geom = feature.geometry()
                    if geom.isMultipart():
                        has_multipart = True
                        break
                    
                if has_multipart:
                    layer_to_clip_singlepart = processing.run("native:multiparttosingleparts", {'INPUT': layer_to_clip,'OUTPUT': 'TEMPORARY_OUTPUT'}, feedback=None)['OUTPUT']
                    layer_to_clip_singlepart, _ = self.make_geometries_valid(layer_to_clip_singlepart)

                clippedLayer = processing.run("native:clip", {
                        'INPUT': layer_to_clip_singlepart,
                        'OVERLAY': clipping_layer,
                        'OUTPUT': 'TEMPORARY_OUTPUT'
                }, feedback=None)['OUTPUT']
            
        return clippedLayer
        
    def landuseMapping(self):
        '''
            Function to perform the land use mapping process.
        '''
        try:
            self.start_operation()
            self.log_to_qtalsim_tab("Starting land use mapping", Qgis.Info)
            self.landuseLayer = None

            #If user selects ATKIS land use as input
            if self.comboboxLanduseSource.currentText() == self.atkisLanduse:
                self.mergeAndClipATKIS()
                self.atkisToTalsimMapping()

            #If user selects LBM land cover as input
            elif self.comboboxLanduseSource.currentText() == self.lbmLandcover:
                selected_layer_lbm = self.comboboxLayerLandbedeckung.currentText()
                self.lbmLayer = QgsProject.instance().mapLayersByName(selected_layer_lbm)[0]
                
                self.landuseLayer = self.clipLanduseLayer(self.lbmLayer)
                self.landbedeckungToTalsimMapping()

            self.exportGeopackage()
            self.log_to_qtalsim_tab("Land use mapping finished", Qgis.Info)

        except Exception as e:
            self.log_to_qtalsim_tab("Error during land use mapping: " + str(e), Qgis.Critical)

        finally:
            self.end_operation()

    def landbedeckungToTalsimMapping(self):
        '''
            Function to map the LBM land cover to Talsim land use.
            (https://gdz.bkg.bund.de/index.php/default/digitales-landbedeckungsmodell-deutschland-stand-2021-lbm-de.html) 
        '''

        mapping = {}
        for _, row in self.dfLanduseAssignmentTalsimLBM.iterrows():
            objart = row["Code"]
            name = row["Name"] #not needed for mapping
            lower_limit_imp = row["SIE untere Grenze"]
            upper_limit_imp = row["SIE obere Grenze"]
            talsim_landuse = row["Talsim Landnutzung"]

            key = (objart, lower_limit_imp, upper_limit_imp)
            mapping[key] = talsim_landuse
        
        if 'OBJART_NEU' not in [f.name() for f in self.landuseLayer.fields()]:
            self.landuseLayer.dataProvider().addAttributes([QgsField('OBJART_NEU', QVariant.String)])
            self.landuseLayer.updateFields()

        self.landuseLayer.startEditing()

        for feature in self.landuseLayer.getFeatures():
            code_landbedeckung = feature["LB_AKT"]

            #Try to find a match with code
            matched = False
            for key, landuse in mapping.items():
                print(key)
                print(code_landbedeckung)
                objart, lower_limit_imp, upper_limit_imp = key

                #check if the land cover of the feature matches the land cover code of the csv
                if code_landbedeckung != objart:
                    continue
                print(lower_limit_imp, upper_limit_imp)
                if lower_limit_imp is not None and not pd.isna(lower_limit_imp):
                    print("lower ?")
                    if feature["SIE_AKT"] < lower_limit_imp:
                        continue
                    elif feature["SIE_AKT"] >= lower_limit_imp:
                        feature["OBJART_NEU"] = landuse
                        matched = True
                        print("lower limit")
                        break

                elif upper_limit_imp is not None and not pd.isna(upper_limit_imp):
                    print("upper ?")
                    if feature["SIE_AKT"] > upper_limit_imp:
                        continue
                    elif feature["SIE_AKT"] < upper_limit_imp:
                        feature["OBJART_NEU"] = landuse
                        matched = True
                        print("upper limit")
                        break
                
                elif pd.isna(lower_limit_imp) and pd.isna(upper_limit_imp):
                    feature["OBJART_NEU"] = landuse
                    matched = True
                    print("no limits")
                    break
            
            #Features without corresponding code in the csv are assigned to the land use of the feature
            if not matched:
                feature["OBJART_NEU"] = code_landbedeckung
                self.log_to_qtalsim_tab(f"Could not find a match for {code_landbedeckung}", Qgis.Warning)

            self.landuseLayer.updateFeature(feature)
            
        self.landuseLayer.commitChanges()
            
      
    def atkisToTalsimMapping(self):
        '''
            Function to map the ATKIS landuse to Talsim land use
        '''
        mapping = {}
        deleted_matches = []
        objart_to_codevals = {}

        dissolve_fields = []
        
        #Store the data of the csv in a dictionary
        #Key: (ATKIS-Bezeichnung, Code-Spalte, Code) -> Value: Talsim Landnutzung
        for _, row in self.dfLanduseAssignmentTalsim.iterrows():
            objart = row["ATKIS-Bezeichnung"]
            code_column = row["Code-Spalte"]
            code_value = row["Codes"]
            talsim_landuse = row["Talsim Landnutzung"]

            if talsim_landuse.lower() == "löschen":
                continue 

            key = (objart, code_column, code_value)
            mapping[key] = talsim_landuse

            if objart not in objart_to_codevals:
                objart_to_codevals[objart] = set()
            objart_to_codevals[objart].add(code_value)

            if code_column not in dissolve_fields and pd.notna(code_column):
                dissolve_fields.append(code_column)
            
        dissolve_fields.append("OBJART_TXT")
        #Dissolve the merged layer to make the looping faster
        self.landuseLayer = processing.run("native:dissolve", {
            'INPUT': self.landuseLayer,
            'FIELD': dissolve_fields,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        if 'OBJART_NEU' not in [f.name() for f in self.landuseLayer.fields()]:
            self.landuseLayer.dataProvider().addAttributes([QgsField('OBJART_NEU', QVariant.String)])
            self.landuseLayer.updateFields()
        
        self.landuseLayer.startEditing()

        for feature in self.landuseLayer.getFeatures():
            objart_txt = feature["OBJART_TXT"]

            #Try to find a match with code
            matched = False
            for key, landuse in mapping.items():
                objart, code_col, code_val = key

                #Check if the land use of the feature matches the land use of the csv
                if objart_txt != objart:
                    continue

                #Check if feature has the code column
                if pd.notna(code_col) and code_col not in feature.fields().names():
                    continue
                
                #1. All land uses with code '-' are assigned to the land use in the csv, as they do not have subcategories
                if code_val == "-":
                    feature["OBJART_NEU"] = landuse
                    matched = True
                    break

                
                feature_code = feature[code_col]

                #2. If there is no code and the code in the csv is 'leer', assign this land use of the csv (where code_val = 'leer')
                    #e.g. relevant for AX_SportFreizeitUndErholungsflaeche which often has subcategories but it is also possible that code is empty
                if str(feature_code).strip().upper() == 'NULL' or feature_code is None or pd.isna(feature_code): #if there is no code 
                    if code_val == 'leer': #assign the value where this objart is "leer"
                        feature["OBJART_NEU"] = landuse
                        matched = True
                        break
                    else:
                        continue
                
                #3. If the code of the layer is not known, assign the land use where code = 'leer'
                if objart in objart_to_codevals:
                    if feature_code not in objart_to_codevals[objart]:
                        if code_val == 'leer':
                            feature["OBJART_NEU"] = landuse
                            matched = True
                            self.log_to_qtalsim_tab(f"Could not find the code {feature_code} and assigned ATKIS land use {objart_txt} with code {feature_code} to Talsim land use {landuse}.", Qgis.Warning)
                            break
                        else:
                            continue
                
                #4. If there is a known code and it matches with the code-value of the feature
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
        self.log_to_qtalsim_tab("ATKIS land use mapping completed", Qgis.Info)
    
    def exportGeopackage(self):
        '''
            Function to export the landuse layer to a GeoPackage.
        '''
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

        
