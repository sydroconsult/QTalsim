
import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog, QDialog, QDialogButtonBox,QMessageBox
from qgis.PyQt.QtCore import QVariant, QTimer
from qgis.core import QgsProject, Qgis, QgsCoordinateReferenceSystem, QgsRasterLayer, QgsVectorLayer, QgsField, edit, QgsLayerTreeLayer, QgsCategorizedSymbolRenderer, QgsVectorFileWriter,QgsWkbTypes, QgsGeometry, QgsFeature, QgsDataSourceUri, QgsFeatureRequest
from qgis.gui import QgsProjectionSelectionDialog
from osgeo import gdal, osr, ogr
import processing
import numpy as np
import webbrowser
import re
import shutil

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qtalsim_soil.ui'))

class SoilPreprocessingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, mainPluginInstance, parent=None):
        """Constructor."""
        super(SoilPreprocessingDialog, self).__init__(parent)
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
        
        #Variables
        self.noLayerSelected = "No Layer selected"
        self.fieldNameSoilType = 'soil_type'
        self.fieldNameBdod = 'bdod'
        self.fieldNameBdodClass = 'bdod_class'
        self.layerBoundingBox = None
        self.path_proj = None
        self.destinationCRS = None
        self.outputPath.clear()
        self.outputCRS.clear()
        self.combinedSoilTypeLayer = None
        self.layer_data = {} #Stores the data of clay, silt and sand share
        self.bdod_data = {} #Stores the data of bulk density
        self.soilTypeLayers = []
        self.bdod_layers_to_combine = []

        #Main Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers
        self.start_operation = self.mainPlugin.start_operation
        self.end_operation = self.mainPlugin.end_operation
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab

        #Connect functions
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFolder) 
        self.connectButtontoFunction(self.onDownloadData, self.downloadData)
        self.connectButtontoFunction(self.onCalculateSoilTypes, self.calculateSoilTypes)
        self.connectButtontoFunction(self.onSelectCRS, self.selectCrs)
        self.connectButtontoFunction(self.finalButtonBox.button(QDialogButtonBox.Help), self.openDocumentation)
        self.checkboxResample.toggled.connect(self.on_resample_toggled)        

        self.fillLayerComboboxes()

        self.talsim_soilids = {
            "Ss":  1,
            "Sl2": 2,
            "Sl3": 3,
            "Sl4": 4,
            "Slu": 5,
            "St2": 6,
            "St3": 7,
            "Su2": 8,
            "Su3": 9,
            "Su4": 10,
            "Ls2": 11,
            "Ls3": 12,
            "Ls4": 13,
            "Lt2": 14,
            "Lt3": 15,
            "Lts": 16,
            "Lu": 17,
            "Uu": 18,
            "Uls": 19,
            "Us": 20,
            "Ut2": 21,
            "Ut3": 22,
            "Ut4": 23,
            "Tt": 24,
            "Tl": 25,
            "Tu2": 26,
            "Tu3": 27,
            "Tu4": 28,
            "Ts2": 29,
            "Ts3": 30,
            "Ts4": 31,
            "fS": 32,
            "mS": 33,
            "gS": 34,
        }

        self.boa = {} # {ID: (Kürzel, %Ton, %Schluff, %Sand, Bezeichnung), ...}
        self.boa[  0] = ("Ss",    0, 10, 90, "Sand")
        self.boa[  1] = ("Ss",    5, 10, 85, "Sand")
        self.boa[  2] = ("Ss",    5,  0, 95, "Sand")
        self.boa[  3] = ("Ss",    0,  0,100, "Sand")
        self.boa[  4] = ("Su2",   0, 25, 75, "schwach schluffiger Sand")
        self.boa[  5] = ("Su2",   5, 25, 70, "schwach schluffiger Sand")
        self.boa[  6] = ("Su2",   5, 10, 85, "schwach schluffiger Sand")
        self.boa[  7] = ("Su2",   0, 10, 90, "schwach schluffiger Sand")
        self.boa[  8] = ("Sl2",   5, 25, 70, "schwach lehmiger Sand")
        self.boa[  9] = ("Sl2",   8, 25, 67, "schwach lehmiger Sand")
        self.boa[ 10] = ("Sl2",   8, 10, 82, "schwach lehmiger Sand")
        self.boa[ 11] = ("Sl2",   5, 10, 85, "schwach lehmiger Sand")
        self.boa[ 12] = ("Sl3",   8, 25, 67, "mittel lehmiger Sand")
        self.boa[ 13] = ("Sl3",   8, 40, 52, "mittel lehmiger Sand")
        self.boa[ 14] = ("Sl3",  12, 40, 48, "mittel lehmiger Sand")
        self.boa[ 15] = ("Sl3",  12, 10, 78, "mittel lehmiger Sand")
        self.boa[ 16] = ("Sl3",   8, 10, 82, "mittel lehmiger Sand")
        self.boa[ 17] = ("St2",   8, 10, 82, "schwach toniger Sand")
        self.boa[ 18] = ("St2",  12, 10, 78, "schwach toniger Sand")
        self.boa[ 19] = ("St2",  17, 10, 73, "schwach toniger Sand")
        self.boa[ 20] = ("St2",  17,  0, 83, "schwach toniger Sand")
        self.boa[ 21] = ("St2",   5,  0, 95, "schwach toniger Sand")
        self.boa[ 22] = ("St2",   5, 10, 85, "schwach toniger Sand")
        self.boa[ 23] = ("Su3",   0, 40, 60, "mittel schluffiger Sand")
        self.boa[ 24] = ("Su3",   8, 40, 52, "mittel schluffiger Sand")
        self.boa[ 25] = ("Su3",   8, 25, 67, "mittel schluffiger Sand")
        self.boa[ 26] = ("Su3",   5, 25, 70, "mittel schluffiger Sand")
        self.boa[ 27] = ("Su3",   0, 25, 75, "mittel schluffiger Sand")
        self.boa[ 28] = ("Su4",   0, 50, 50, "stark schluffiger Sand")
        self.boa[ 29] = ("Su4",   8, 50, 42, "stark schluffiger Sand")
        self.boa[ 30] = ("Su4",   8, 40, 52, "stark schluffiger Sand")
        self.boa[ 31] = ("Su4",   0, 40, 60, "stark schluffiger Sand")
        self.boa[ 32] = ("Slu",   8, 50, 42, "schluffig-lehmiger Sand")
        self.boa[ 33] = ("Slu",  17, 50, 33, "schluffig-lehmiger Sand")
        self.boa[ 34] = ("Slu",  17, 40, 43, "schluffig-lehmiger Sand")
        self.boa[ 35] = ("Slu",  12, 40, 48, "schluffig-lehmiger Sand")
        self.boa[ 36] = ("Slu",   8, 40, 52, "schluffig-lehmiger Sand")
        self.boa[ 37] = ("Sl4",  17, 30, 53, "stark lehmiger Sand")
        self.boa[ 38] = ("Sl4",  17, 15, 68, "stark lehmiger Sand")
        self.boa[ 39] = ("Sl4",  17, 10, 73, "stark lehmiger Sand")
        self.boa[ 40] = ("Sl4",  12, 10, 78, "stark lehmiger Sand")
        self.boa[ 41] = ("Sl4",  12, 40, 48, "stark lehmiger Sand")
        self.boa[ 42] = ("Sl4",  17, 40, 43, "stark lehmiger Sand")
        self.boa[ 43] = ("St3",  17, 10, 73, "mittel toniger Sand")
        self.boa[ 44] = ("St3",  17, 15, 68, "mittel toniger Sand")
        self.boa[ 45] = ("St3",  25, 15, 60, "mittel toniger Sand")
        self.boa[ 46] = ("St3",  25,  0, 75, "mittel toniger Sand")
        self.boa[ 47] = ("St3",  17,  0, 83, "mittel toniger Sand")
        self.boa[ 48] = ("Ls2",  25, 50, 25, "schwach sandiger Lehm")
        self.boa[ 49] = ("Ls2",  25, 40, 35, "schwach sandiger Lehm")
        self.boa[ 50] = ("Ls2",  17, 40, 43, "schwach sandiger Lehm")
        self.boa[ 51] = ("Ls2",  17, 50, 33, "schwach sandiger Lehm")
        self.boa[ 52] = ("Ls3",  17, 40, 43, "mittel sandiger Lehm")
        self.boa[ 53] = ("Ls3",  25, 40, 35, "mittel sandiger Lehm")
        self.boa[ 54] = ("Ls3",  25, 30, 45, "mittel sandiger Lehm")
        self.boa[ 55] = ("Ls3",  17, 30, 53, "mittel sandiger Lehm")
        self.boa[ 56] = ("Ls4",  25, 15, 60, "stark sandiger Lehm")
        self.boa[ 57] = ("Ls4",  17, 15, 68, "stark sandiger Lehm")
        self.boa[ 58] = ("Ls4",  17, 30, 53, "stark sandiger Lehm")
        self.boa[ 59] = ("Ls4",  25, 30, 45, "stark sandiger Lehm")
        self.boa[ 60] = ("Lts",  45, 15, 40, "sandig-toniger Lehm")
        self.boa[ 61] = ("Lts",  35, 15, 50, "sandig-toniger Lehm")
        self.boa[ 62] = ("Lts",  25, 15, 60, "sandig-toniger Lehm")
        self.boa[ 63] = ("Lts",  25, 30, 45, "sandig-toniger Lehm")
        self.boa[ 64] = ("Lts",  35, 30, 35, "sandig-toniger Lehm")
        self.boa[ 65] = ("Lts",  45, 30, 25, "sandig-toniger Lehm")
        self.boa[ 66] = ("Ts4",  35,  0, 65, "stark sandiger Ton")
        self.boa[ 67] = ("Ts4",  25,  0, 75, "stark sandiger Ton")
        self.boa[ 68] = ("Ts4",  25, 15, 60, "stark sandiger Ton")
        self.boa[ 69] = ("Ts4",  35, 15, 50, "stark sandiger Ton")
        self.boa[ 70] = ("Ts3",  45, 15, 40, "mittel sandiger Ton")
        self.boa[ 71] = ("Ts3",  45,  0, 55, "mittel sandiger Ton")
        self.boa[ 72] = ("Ts3",  35,  0, 65, "mittel sandiger Ton")
        self.boa[ 73] = ("Ts3",  35, 15, 50, "mittel sandiger Ton")
        self.boa[ 74] = ("Uu",    0,100,  0, "Schluff")
        self.boa[ 75] = ("Uu",    8, 92,  0, "Schluff")
        self.boa[ 76] = ("Uu",    8, 80, 12, "Schluff")
        self.boa[ 77] = ("Uu",    0, 80, 20, "Schluff")
        self.boa[ 78] = ("Us",    0, 80, 20, "sandiger Schluff")
        self.boa[ 79] = ("Us",    8, 80, 12, "sandiger Schluff")
        self.boa[ 80] = ("Us",    8, 65, 27, "sandiger Schluff")
        self.boa[ 81] = ("Us",    8, 50, 42, "sandiger Schluff")
        self.boa[ 82] = ("Us",    0, 50, 50, "sandiger Schluff")
        self.boa[ 83] = ("Ut2",   8, 80, 12, "schwach toniger Schluff")
        self.boa[ 84] = ("Ut2",   8, 92,  0, "schwach toniger Schluff")
        self.boa[ 85] = ("Ut2",  12, 88,  0, "schwach toniger Schluff")
        self.boa[ 86] = ("Ut2",  12, 65, 23, "schwach toniger Schluff")
        self.boa[ 87] = ("Ut2",   8, 65, 27, "schwach toniger Schluff")
        self.boa[ 88] = ("Ut3",  12, 88,  0, "mittel toniger Schluff")
        self.boa[ 89] = ("Ut3",  17, 83,  0, "mittel toniger Schluff")
        self.boa[ 90] = ("Ut3",  17, 65, 18, "mittel toniger Schluff")
        self.boa[ 91] = ("Ut3",  12, 65, 23, "mittel toniger Schluff")
        self.boa[ 92] = ("Uls",  12, 65, 23, "sandig-lehmiger Schluff")
        self.boa[ 93] = ("Uls",  17, 65, 18, "sandig-lehmiger Schluff")
        self.boa[ 94] = ("Uls",  17, 50, 33, "sandig-lehmiger Schluff")
        self.boa[ 95] = ("Uls",   8, 50, 42, "sandig-lehmiger Schluff")
        self.boa[ 96] = ("Uls",   8, 65, 27, "sandig-lehmiger Schluff")
        self.boa[ 97] = ("Lu",   17, 65, 18, "schluffiger Lehm")
        self.boa[ 98] = ("Lu",   25, 65, 10, "schluffiger Lehm")
        self.boa[ 99] = ("Lu",   30, 65,  5, "schluffiger Lehm")
        self.boa[100] = ("Lu",   30, 50, 20, "schluffiger Lehm")
        self.boa[101] = ("Lu",   25, 50, 25, "schluffiger Lehm")
        self.boa[102] = ("Lu",   17, 50, 33, "schluffiger Lehm")
        self.boa[103] = ("Ut4",  17, 83,  0, "stark toniger Schluff")
        self.boa[104] = ("Ut4",  25, 75,  0, "stark toniger Schluff")
        self.boa[105] = ("Ut4",  25, 65, 10, "stark toniger Schluff")
        self.boa[106] = ("Ut4",  17, 65, 18, "stark toniger Schluff")
        self.boa[107] = ("Tu4",  25, 65, 10, "stark schluffiger Ton")
        self.boa[108] = ("Tu4",  25, 75,  0, "stark schluffiger Ton")
        self.boa[109] = ("Tu4",  35, 65,  0, "stark schluffiger Ton")
        self.boa[110] = ("Tu4",  30, 65,  5, "stark schluffiger Ton")
        self.boa[111] = ("Tu3",  30, 65,  5, "mittel schluffiger Ton")
        self.boa[112] = ("Tu3",  35, 65,  0, "mittel schluffiger Ton")
        self.boa[113] = ("Tu3",  45, 55,  0, "mittel schluffiger Ton")
        self.boa[114] = ("Tu3",  45, 50,  5, "mittel schluffiger Ton")
        self.boa[115] = ("Tu3",  35, 50, 15, "mittel schluffiger Ton")
        self.boa[116] = ("Tu3",  30, 50, 20, "mittel schluffiger Ton")
        self.boa[117] = ("Lt2",  35, 50, 15, "schwach toniger Lehm")
        self.boa[118] = ("Lt2",  35, 30, 35, "schwach toniger Lehm")
        self.boa[119] = ("Lt2",  25, 30, 45, "schwach toniger Lehm")
        self.boa[120] = ("Lt2",  25, 40, 35, "schwach toniger Lehm")
        self.boa[121] = ("Lt2",  25, 50, 25, "schwach toniger Lehm")
        self.boa[122] = ("Lt2",  30, 50, 20, "schwach toniger Lehm")
        self.boa[123] = ("Lt3",  45, 50,  5, "toniger Lehm")
        self.boa[124] = ("Lt3",  45, 30, 25, "toniger Lehm")
        self.boa[125] = ("Lt3",  35, 30, 35, "toniger Lehm")
        self.boa[126] = ("Lt3",  35, 50, 15, "toniger Lehm")
        self.boa[127] = ("Tu2",  45, 30, 25, "schwach schluffiger Ton")
        self.boa[128] = ("Tu2",  45, 50,  5, "schwach schluffiger Ton")
        self.boa[129] = ("Tu2",  45, 55,  0, "schwach schluffiger Ton")
        self.boa[130] = ("Tu2",  65, 35,  0, "schwach schluffiger Ton")
        self.boa[131] = ("Tu2",  65, 30,  5, "schwach schluffiger Ton")
        self.boa[132] = ("Tl",   65, 30,  5, "lehmiger Ton")
        self.boa[133] = ("Tl",   65, 15, 20, "lehmiger Ton")
        self.boa[134] = ("Tl",   45, 15, 40, "lehmiger Ton")
        self.boa[135] = ("Tl",   45, 30, 25, "lehmiger Ton")
        self.boa[136] = ("Ts2",  45, 15, 40, "schwach sandiger Ton")
        self.boa[137] = ("Ts2",  65, 15, 20, "schwach sandiger Ton")
        self.boa[138] = ("Ts2",  65,  0, 35, "schwach sandiger Ton")
        self.boa[139] = ("Ts2",  45,  0, 55, "schwach sandiger Ton")
        self.boa[140] = ("Tt",   65, 15, 20, "Ton")
        self.boa[141] = ("Tt",   65, 30,  5, "Ton")
        self.boa[142] = ("Tt",   65, 35,  0, "Ton")
        self.boa[143] = ("Tt",  100,  0,  0, "Ton")
        self.boa[144] = ("Tt",   65,  0, 35, "Ton")

    def openDocumentation(self):
        '''
            Connected with help-button.
        '''
        webbrowser.open('https://sydroconsult.github.io/QTalsim/doc_soil')

    def make_geometries_valid(self, layer):
        '''
            Checks for invalid geometries in an input layer and updates those geometries.
                Also deletes features with empty geometries.
        '''
        invalid_features = False
        layer.startEditing() 
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom.isGeosValid():
                fixed_geom = geom.makeValid()
                #Check if the fixed geometry is valid and of the correct type
                if fixed_geom.isGeosValid() and fixed_geom.wkbType() == QgsWkbTypes.MultiPolygon:
                    feature.setGeometry(fixed_geom)
                    layer.updateFeature(feature)
                else:
                    #Attempt to fix the geometry to be a MultiPolygon
                    if fixed_geom.wkbType() == QgsWkbTypes.Polygon:
                        fixed_geom = QgsGeometry.fromMultiPolygonXY([fixed_geom.asPolygon()])
                    elif fixed_geom.wkbType() == QgsWkbTypes.LineString or fixed_geom.wkbType() == QgsWkbTypes.MultiLineString:
                        fixed_geom = QgsGeometry.fromPolygonXY([fixed_geom.asPolyline()])
                    #Set the fixed geometry if it's valid
                    if fixed_geom.isGeosValid() and fixed_geom.wkbType() == QgsWkbTypes.MultiPolygon:
                        feature.setGeometry(fixed_geom)
                        layer.updateFeature(feature)
                    else:
                        invalid_features = True
            if geom.isEmpty() or geom.area() == 0:
                layer.deleteFeature(feature.id())
        layer.commitChanges()
        return layer, invalid_features
    
    def fillLayerComboboxes(self):
        '''
            Fills all comboboxes with layers
        '''

        self.polygonLayers, self.rasterLayers = self.getAllLayers(QgsProject.instance().layerTreeRoot())

        #Sub-basins layer
        self.comboboxExtentLayer.clear() #clear combobox EZG from previous runs
        self.comboboxExtentLayer.addItem(self.noLayerSelected)
        self.comboboxExtentLayer.addItems([layer.name() for layer in self.polygonLayers])
        self.comboboxExtentLayer.addItems([layer.name() for layer in self.rasterLayers])

    def selectOutputFolder(self):
        '''
            Function to select the output folder. 
        '''
        self.outputFolder = None
        self.outputFolder = QFileDialog.getExistingDirectory(self, "Select Folder","") #, options=options
        if self.outputFolder:
            self.outputPath.setText(self.outputFolder)

            #Expected folders and files
            expected_subfolders = ["proj", "orig"]
            expected_files = ["soil_types.gpkg", "bdod.gpkg"]

            subfolders_present = all(os.path.isdir(os.path.join(self.outputFolder, subfolder)) for subfolder in expected_subfolders)
            files_present = all(os.path.isfile(os.path.join(self.outputFolder, file)) for file in expected_files)
            self.onDownloadData.setVisible(True)

            if subfolders_present or files_present: #Check if subfolders/files are present
                existing_subfolders = [subfolder for subfolder in expected_subfolders if os.path.isdir(os.path.join(self.outputFolder, subfolder))]
                existing_files = [file for file in expected_files if os.path.isfile(os.path.join(self.outputFolder, file))]

                #Format the message for the existing items
                message = "The selected folder contains the following items:\n"
                if existing_subfolders:
                    message += f"Subfolders: {', '.join(existing_subfolders)}\n"
                if existing_files:
                    message += f"Data Files: {', '.join(existing_files)}\n"
                message += "Do you want to use this data for further processing?"

                reply = QMessageBox.question(
                    self,
                    "Data Found",
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                )
                
                if reply == QMessageBox.Yes:
                    self.log_to_qtalsim_tab("Proceeding with the existing data for further processing. "
                                            "Please select a CRS and start the process by clicking 'Calculate Soil Types'.", Qgis.Info)
                    self.onDownloadData.setVisible(False)
                    self.onCalculateSoilTypes.setEnabled(True) #enable calculation of soil types

                else: #If user does not want to keep the data, data is deleted
                    self.log_to_qtalsim_tab("User chose not to use the existing data.", Qgis.Info)
                    self.onDownloadData.setVisible(True)
                    try:
                        #Specify the paths to delete
                        paths_to_delete = expected_subfolders + expected_files
                        deleted_items = []

                        for item in paths_to_delete:
                            item_path = os.path.join(self.outputFolder, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path) #Recursively delete directories
                                deleted_items.append(item)
                            elif os.path.isfile(item_path):
                                os.remove(item_path) #Delete files
                                deleted_items.append(item)

                        if deleted_items:
                            self.log_to_qtalsim_tab(f"Successfully deleted the following items: {', '.join(deleted_items)}", Qgis.Info)
                        else:
                            self.log_to_qtalsim_tab("No items were deleted. Nothing matched the expected data.", Qgis.Warning)

                    except Exception as e:
                        self.log_to_qtalsim_tab(f"Failed to delete some or all items in the folder. Error: {str(e)}", Qgis.Critical)

    def selectCrs(self): 
        '''
            Saves CRS selected by user
        '''
        #Create the CRS selection dialog
        dialog = QgsProjectionSelectionDialog()
        
        #Display the dialog and check if the user pressed OK
        if dialog.exec_() == QDialog.Accepted:
            #Get the selected CRS
            self.destinationCRS = dialog.crs()
            self.dstSRS = self.destinationCRS.authid() 

            #Log the selected CRS as EPSG code or WKT
            self.log_to_qtalsim_tab(f"Selected destination CRS: {self.destinationCRS.authid()}", Qgis.Info)  #e.g., 'EPSG:4326'
            self.outputCRS.setText(f"{self.destinationCRS.authid()}")
            #self.log_to_qtalsim_tab(f"Selected destination CRS WKT: {self.destinationCRS.toWkt()}", Qgis.Info)  #Full WKT representation
            
        else:
            self.log_to_qtalsim_tab("No destination CRS selected.", Qgis.Warning)
            return None
    
    def downloadData(self):
        '''
            Downloads ISRIC soil data (clay, silt, sand share and bulk density value).
        '''
        try:
            self.start_operation()
            
            #Select layer
            selected_layer_name = self.comboboxExtentLayer.currentText()
            if selected_layer_name != self.noLayerSelected:
                self.layerBoundingBox = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
                self.log_to_qtalsim_tab(f"Selected layer {self.layerBoundingBox.name()} as input layer.", Qgis.Info)
            else:
                self.log_to_qtalsim_tab("Please select a layer.", Qgis.Critical)

            #Transform to Homolosine projection
            #Check if the layer's CRS is already Homolosine
            homolosine_crs = QgsCoordinateReferenceSystem()
            homolosine_crs.createFromProj("+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs")

            current_crs = self.layerBoundingBox.crs()
            if current_crs != homolosine_crs:

                #If bounding box layer is vector layer:
                if isinstance(self.layerBoundingBox, QgsVectorLayer):
                    if not current_crs.ellipsoidAcronym() == 'WGS84':
                        params1 = {
                            'INPUT': self.layerBoundingBox,
                            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'),
                            'OUTPUT': 'memory:',
                            'TRANSFORM_CONTEXT': QgsProject.instance().transformContext()
                        }
                        result1 = processing.run("native:reprojectlayer", params1)
                        self.layerBoundingBox = result1['OUTPUT']
                    params = {
                        'INPUT': self.layerBoundingBox,
                        'TARGET_CRS': homolosine_crs,
                        'OUTPUT': 'memory:'  # Store the reprojected layer in memory
                    }

                    #Reproject the layer
                    reprojectedLayerResult = processing.run("native:reprojectlayer", params)
                    self.layerBoundingBox = reprojectedLayerResult['OUTPUT']   
                
                #If bounding box layer is raster layer
                elif isinstance(self.layerBoundingBox, QgsRasterLayer): 
                    if not current_crs.ellipsoidAcronym() == 'WGS84':
                        params = {
                            'INPUT': self.layerBoundingBox,
                            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'),  #Use the CRS object for Homolosine
                            'RESAMPLING': 0,  #Choose the resampling method (0=nearest neighbor, 1=bilinear, etc.)
                            'NODATA': None,  #Handle NoData values if needed
                            'TARGET_RESOLUTION': None,  #Set if you want to specify a resolution
                            'OPTIONS': '',
                            'DATA_TYPE': 0,  #Keep the data type (0=Byte, 1=Int16, etc.)
                            'TARGET_EXTENT': None,  #Use None to keep the same extent
                            'TARGET_EXTENT_CRS': None,  #If extent is specified, its CRS should be provided
                            'MULTITHREADING': False,
                            'OUTPUT': 'TEMPORARY_OUTPUT' #Store the reprojected raster in memory
                        }

                        #Reproject the raster layer
                        reprojectedLayerResult = processing.run("gdal:warpreproject", params)
                        self.layerBoundingBox = reprojectedLayerResult['OUTPUT']
                    params = {
                        'INPUT': self.layerBoundingBox,
                        'TARGET_CRS': homolosine_crs,  #Use the CRS object for Homolosine
                        'RESAMPLING': 0,  #Choose the resampling method (0=nearest neighbor, 1=bilinear, etc.)
                        'NODATA': None,  #Handle NoData values if needed
                        'TARGET_RESOLUTION': None,  #Set if you want to specify a resolution
                        'OPTIONS': '',
                        'DATA_TYPE': 0,  #Keep the data type (0=Byte, 1=Int16, etc.)
                        'TARGET_EXTENT': None,  #Use None to keep the same extent
                        'TARGET_EXTENT_CRS': None,  #If extent is specified, its CRS should be provided
                        'MULTITHREADING': False,
                        'OUTPUT': 'TEMPORARY_OUTPUT' #Store the reprojected raster in memory
                    }

                    #Reproject the raster layer
                    reprojectedLayerResult = processing.run("gdal:warpreproject", params)
                    self.layerBoundingBox = QgsRasterLayer(reprojectedLayerResult['OUTPUT'], selected_layer_name + '_reprojected')
                QgsProject.instance().addMapLayer(self.layerBoundingBox, False)

            #Get extent
            extent = self.layerBoundingBox.extent()
            min_x = extent.xMinimum()
            min_y = extent.yMinimum()
            max_x = extent.xMaximum()
            max_y = extent.yMaximum()

            #Bounding-Box:
            bb = (min_x, max_y, max_x, min_y)
           
            #Output paths
            path_out = os.path.join(self.outputFolder, 'orig')
            self.path_proj = os.path.join(self.outputFolder, 'proj')

            #Datasets to process
            #name : path_to_vrt
            url = "https://files.isric.org/soilgrids/latest/data/"
            datasets = {
                "bdod_0-5cm_mean": "bdod/bdod_0-5cm_mean.vrt",
                "bdod_5-15cm_mean": "bdod/bdod_5-15cm_mean.vrt",
                "bdod_15-30cm_mean": "bdod/bdod_15-30cm_mean.vrt",
                "bdod_30-60cm_mean": "bdod/bdod_30-60cm_mean.vrt",
                "bdod_60-100cm_mean": "bdod/bdod_60-100cm_mean.vrt",
                "bdod_100-200cm_mean": "bdod/bdod_100-200cm_mean.vrt",
                "sand_0-5cm_mean": "sand/sand_0-5cm_mean.vrt",
                "sand_5-15cm_mean": "sand/sand_5-15cm_mean.vrt",
                "sand_15-30cm_mean": "sand/sand_15-30cm_mean.vrt",
                "sand_30-60cm_mean": "sand/sand_30-60cm_mean.vrt",
                "sand_60-100cm_mean": "sand/sand_60-100cm_mean.vrt",
                "sand_100-200cm_mean": "sand/sand_100-200cm_mean.vrt",
                "clay_0-5cm_mean": "clay/clay_0-5cm_mean.vrt",
                "clay_5-15cm_mean": "clay/clay_5-15cm_mean.vrt",
                "clay_15-30cm_mean": "clay/clay_15-30cm_mean.vrt",
                "clay_30-60cm_mean": "clay/clay_30-60cm_mean.vrt",
                "clay_60-100cm_mean": "clay/clay_60-100cm_mean.vrt",
                "clay_100-200cm_mean": "clay/clay_100-200cm_mean.vrt",
                "silt_0-5cm_mean": "silt/silt_0-5cm_mean.vrt",
                "silt_5-15cm_mean": "silt/silt_5-15cm_mean.vrt",
                "silt_15-30cm_mean": "silt/silt_15-30cm_mean.vrt",
                "silt_30-60cm_mean": "silt/silt_30-60cm_mean.vrt",
                "silt_60-100cm_mean": "silt/silt_60-100cm_mean.vrt",
                "silt_100-200cm_mean": "silt/silt_100-200cm_mean.vrt",
                }

            #Create output-path for original files
            if not os.path.exists(path_out):
                os.mkdir(path_out)

            #Create output-path for projected files
            if not os.path.exists(self.path_proj):
                os.mkdir(self.path_proj)

            gdal.SetConfigOption("GDAL_HTTP_UNSAFESSL", "True")

            igh = "+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs" # proj string for Homolosine projection
            res_download = 250 # download in original resolution
            if self.checkboxResample.isChecked():
                res = int(self.spinboxResample.value())
            else:
                res = res_download 
            
            sg_url = "/vsicurl/" + url

            kwargs = {'format': 'GTiff', 
                    'projWin': bb, 
                    'projWinSRS': igh, 
                    'xRes': res_download, 
                    'yRes': res_download, 
                    'creationOptions': ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "BIGTIFF=YES"]}

            #Save files
            for name, loc in datasets.items():
                try:
                    self.log_to_qtalsim_tab(f"Processing... {name}", Qgis.Info)
                    
                    file_orig = os.path.join(path_out, name + '.tif')
                    file_proj = os.path.join(self.path_proj, name + '.tif')

                    ds = gdal.Translate(file_orig, sg_url + loc, **kwargs)
                    ds = gdal.Warp(file_proj, ds, dstSRS=self.dstSRS, xRes=res, yRes=res, resampleAlg='average') #, srcNodata=-9999, dstNodata=-9999
                        
                    ds = None
                except Exception as e:
                    self.log_to_qtalsim_tab(f"Error processing {name}: {str(e)}", Qgis.Critical)
                    continue
            
            self.onCalculateSoilTypes.setEnabled(True) #enable calculation of soil types
        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

        finally:
            self.end_operation()
    
    def calculateSoilTypes(self):
        '''
            Calls functions to calculate the soil types from clay, silt and sand share for every soil layer.     
        '''
        try:
            self.start_operation()

            #First check if there is is already a geopackage-file in the folder
            file_path = os.path.join(self.outputFolder, "soil_types.gpkg")
            file_path_bdod = os.path.join(self.outputFolder, "bdod.gpkg")
            file_name_soiltypes = os.path.basename(file_path)
            file_name_bdod = os.path.basename(file_path_bdod)
            
            layer_names = []
            if self.path_proj is None:
                self.path_proj = os.path.join(self.outputFolder, 'proj')

            #Check which files exist
            if os.path.exists(file_path) and os.path.exists(file_path_bdod):
                self.log_to_qtalsim_tab(f"The files {file_name_soiltypes} and {file_name_bdod} exist. Using these files to continue the conversion.", Qgis.Info)
                
                #Soil-Types
                #provider_metadata = QgsProviderRegistry.instance().providerMetadata('ogr')

                #Create a data source URI for the GeoPackage
                gpkg_layer = QgsVectorLayer(file_path, "GeoPackage", "ogr")
                sublayers = gpkg_layer.dataProvider().subLayers()

                layer_names = [s.split('!!::!!')[1] for s in sublayers]  #Extract layer names
                soil_horizons = []
                for name in layer_names:
                    soil_horizon = name.split('soiltype_')[-1] #Extract soil horizon
                    soil_horizon += '_mean.tif'
                    soil_horizons.append(soil_horizon)
                    self.layer_data[soil_horizon] = None
                    vector_layer = QgsVectorLayer(f"{file_path}|layername={name}", name, "ogr")
                    if vector_layer.isValid():
                        self.soilTypeLayers.append(vector_layer)
                self.combinedSoilTypeLayer = QgsVectorLayer(f"{file_path}|layername={name}", name, "ogr")

                #BDOD
                #Create a data source URI for the GeoPackage
                gpkg_layer = QgsVectorLayer(file_path_bdod, "GeoPackage", "ogr")
                bdod_layers = gpkg_layer.dataProvider().subLayers()

                bdod_layer_names = [s.split('!!::!!')[1] for s in bdod_layers]  #Extract layer names
                for layer_name in bdod_layer_names:
                    bdod_layer = layer_name.split('bdod_')[-1]
                    bdod_layer += '_mean.tif'
                    self.bdod_data[bdod_layer] = None                    
                    vector_layer = QgsVectorLayer(f"{file_path_bdod}|layername={layer_name}", layer_name, "ogr")
                    if vector_layer.isValid():
                        self.bdod_layers_to_combine.append(vector_layer)

            elif os.path.exists(file_path): #bdod does not exist
                self.log_to_qtalsim_tab(f"The file {file_name_soiltypes} exists. Using this file to continue the conversion.", Qgis.Info)
                
                #provider_metadata = QgsProviderRegistry.instance().providerMetadata('ogr')

                #Create a data source URI for the GeoPackage
                gpkg_layer = QgsVectorLayer(file_path, "GeoPackage", "ogr")
                sublayers = gpkg_layer.dataProvider().subLayers()

                layer_names = [s.split('!!::!!')[1] for s in sublayers]  #Extract layer names
                self.log_to_qtalsim_tab(f"Found layers: {', '.join(layer_names)}", Qgis.Info)
                #self.log_to_qtalsim_tab(f"Raw sublayer metadata: {sublayers}", Qgis.Info)

                #Check which layers exist in soil_types.gpkg
                soil_horizons = []
                for name in layer_names:
                    soil_horizon = name.split('soiltype_')[-1]   #Extract soil horizon
                    soil_horizon += '_mean.tif'
                    soil_horizons.append(soil_horizon)
                    self.layer_data[soil_horizon] = None
                    #if not "Soil Types Combined" in layer_names:
                    vector_layer = QgsVectorLayer(f"{file_path}|layername={name}", name, "ogr")
                    if vector_layer.isValid():
                        self.soilTypeLayers.append(vector_layer)
                if "Soil Types Combined" in layer_names:
                    self.combinedSoilTypeLayer = QgsVectorLayer(f"{file_path}|layername={name}", name, "ogr")
            self.log_to_qtalsim_tab("Calculating soil types from clay, silt and sand share...", Qgis.Info)
            root = QgsProject.instance().layerTreeRoot()

            #Create layer group to store all layers
            group_name = "QTalsim Soil Layers"
            self.layer_group = root.insertGroup(0, group_name) #Add the layer group to the top of the layer catalog

            self.createCombinedLayer()
            self.soilMapping()

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)
        
        finally:
            self.end_operation()

    def createCombinedLayer(self):
        '''
            Creates stacked numpy arrays with clay, silt and sand share of the respective soil layer.
        '''

        def read_tif_as_array(file_path):
            dataset = gdal.Open(file_path)
            array = dataset.ReadAsArray()
            
            #Get the "no data" value from the dataset
            standard_no_data_value = -9999
            no_data_value = dataset.GetRasterBand(1).GetNoDataValue()
            if no_data_value is not None:
                if base_name != 'bdod':
                    #Use NaN for other layers except bdod
                    array = np.where(array == no_data_value, np.nan, array)
                else:
                    #Replace bdod no-data values with standard no-data value
                    array = np.where(array == no_data_value, standard_no_data_value, array)
            else:
                #If no-data value is missing in raster, apply standard no-data for bdod layers
                if base_name == 'bdod':
                    array[array == standard_no_data_value] = standard_no_data_value
            
            return array

        for file_name in os.listdir(self.path_proj):
            if file_name.endswith('.tif'):
                base_name = file_name.split('_')[0]  #'clay', 'sand', 'silt', or 'bdod'
                layer = '_'.join(file_name.split('_')[1:])  #needed to store the arrays in the relevant soil layer, e.g., '0-5cm_mean.tif'

                #Read files with gdal
                file_path = os.path.join(self.path_proj, file_name)
                array = read_tif_as_array(file_path)

                #First, store the data in dictionaries
                if base_name == 'bdod':
                    if layer not in self.bdod_data:
                        self.bdod_data[layer] = array
                else:
                    if layer not in self.layer_data:
                        self.layer_data[layer] = {}
                    if self.layer_data[layer] != None:
                        self.layer_data[layer][base_name] = array #store the data in the respective soil layer + type (clay, silt, sand)
        
        #Convert dicts to numpy arrays and convert the units of the data (https://www.isric.org/explore/soilgrids/faq-soilgrids#What_do_the_filename_codes_mean)
        for layer in self.layer_data:
            if self.layer_data[layer] != None:
                clay = self.layer_data[layer].get('clay')
                silt = self.layer_data[layer].get('silt')
                sand = self.layer_data[layer].get('sand')

                #Create np-array
                if clay is not None and sand is not None and silt is not None:
                    stacked_array = np.stack([clay, silt, sand])
                    self.layer_data[layer] = stacked_array

                    #Convert from g/kg to g/100g by dividing by 10
                    stacked_array = stacked_array / 10
                    
                    #Store the converted array in the dictionary
                    self.layer_data[layer] = stacked_array

                else:
                    self.log_to_qtalsim_tab(f"Missing data for layer {layer}, skipping.", Qgis.Info)

        #Convert bulk density layer from cg/cm³ to kg/dm³ by dividing by 100
        for layer in self.bdod_data:
            if layer is not None and self.bdod_data[layer] is not None:
                self.bdod_data[layer] = self.bdod_data[layer].astype(float)
                
                self.bdod_data[layer][np.isclose(self.bdod_data[layer], -9999, atol=1e-3)] = -9999.0
                #Create a mask to exclude no-data values
                mask = self.bdod_data[layer] > -9999.0

                self.bdod_data[layer][mask] = self.bdod_data[layer][mask] / 100

    def pointInPoly(self, xt, yt):
        """
            Checks, if the point xt / yt is within polygon polyX / polyY.
        """

        kreuz = 0

        xo = self.polyX[self.count]
        yo = self.polyY[self.count]
        
        for np in range(self.count + 1):
            xn = self.polyX[np]
            yn = self.polyY[np]
            if (xn > xo):
                x1 = xo
                x2 = xn
                y1 = yo
                y2 = yn
            else:
                x1 = xn
                x2 = xo
                y1 = yn
                y2 = yo

            if ((xn <  xt and xt <= xo) or (xn >= xt and xt > xo)):
                if ((yt - y1) * (x2 - x1) == (y2 - y1) * (xt - x1)):
                    kreuz += 1
                if ((yt - y1) * (x2 - x1) < (y2 - y1) * (xt - x1)):
                    kreuz += 1

            if (xn == xt or xt == xo):
                if ((yt - y1) * (x2 - x1) == (y2 - y1) * (xt - x1)):
                    if ((yn <= yt and yt <= yo) or (yn > yt and yt > yo)):
                        kreuz += 1
            xo = xn
            yo = yn

        if (kreuz % 2 == 1):
            return True #soil type was found
        
        return False
    
    def polygonize_and_combine(self, arrays, array_names, geotransform, projection, output_gpkg, combined_layer_name):
        '''
            Polygonize multiple arrays and combine them into a single vector layer with additional attributes.
        '''
        self.log_to_qtalsim_tab("Combining soil type layers to one layer...", Qgis.Info)

        nodata_value = -9999
        rows, cols = arrays[0].shape

        #Step 1: Create a dictionary of unique combinations
        unique_combinations = {}
        reverse_lookup = []
        reference_array = np.full((rows, cols), nodata_value, dtype=np.int32)

        for i in range(rows):
            for j in range(cols):
                #Create a tuple of soil IDs for the current cell across all horizons
                combination = tuple(array[i, j] if array[i, j] != nodata_value else None for array in arrays)
                if combination not in unique_combinations:
                    unique_index = len(unique_combinations) + 1
                    unique_combinations[combination] = unique_index
                    reverse_lookup.append(combination)  #Reverse mapping: index -> combination
                reference_array[i, j] = unique_combinations[combination]

        #Step 2: Polygonize the reference array
        driver = gdal.GetDriverByName('MEM')
        raster = driver.Create('', cols, rows, 1, gdal.GDT_Int32)
        raster.SetGeoTransform(geotransform)
        raster.SetProjection(projection)

        band = raster.GetRasterBand(1)
        band.WriteArray(reference_array)
        band.SetNoDataValue(nodata_value)

        #Create output GeoPackage
        gpkg_driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(output_gpkg):
            gpkg_ds = gpkg_driver.Open(output_gpkg, 1)  #Open for update
        else:
            gpkg_ds = gpkg_driver.CreateDataSource(output_gpkg)

        if gpkg_ds is None:
            raise RuntimeError(f"Failed to create or open GeoPackage at {output_gpkg}")

        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection)

        combined_layer = gpkg_ds.CreateLayer(combined_layer_name, srs, ogr.wkbPolygon)
        if combined_layer is None:
            raise RuntimeError(f"Failed to create combined layer '{combined_layer_name}' in GeoPackage.")

        #Add fields for each horizon
        for layer_name in array_names:
            layer_name = layer_name.replace("_mean", "")
            combined_layer.CreateField(ogr.FieldDefn(f"{layer_name}_soil_type", ogr.OFTString))
            combined_layer.CreateField(ogr.FieldDefn(f"{layer_name}_layer_thickness", ogr.OFTReal))

        combined_layer.CreateField(ogr.FieldDefn(f"DN", ogr.OFTInteger))
        field_index = combined_layer.GetLayerDefn().GetFieldIndex("DN")

        #Polygonize
        err = gdal.Polygonize(band, None, combined_layer, field_index, [], callback=None)
        if err != 0:
            raise RuntimeError(f"Polygonization failed.")

        #Step 3: Add attributes to the polygons
        #combined_layer_defn = combined_layer.GetLayerDefn()
        id_to_soil_name = {v: k for k, v in self.talsim_soilids.items()}

        for feature in combined_layer:
            #Get the unique index directly from the polygon's attribute
            unique_index = feature.GetField("DN")  
            if unique_index is None or unique_index == nodata_value:
                continue

            #Retrieve the combination of soil horizons for this unique index
            combination = reverse_lookup[unique_index - 1]

            if all(value is None for value in combination):
                combined_layer.DeleteFeature(feature.GetFID())  #Remove the feature
                continue
            
            #Assign attributes based on the combination
            for idx, layer_name in enumerate(array_names):
                layer_name = layer_name.replace("_mean", "")
                soil_id = combination[idx]
                soil_name = id_to_soil_name.get(soil_id, None) if soil_id is not None else None
                thickness_m = None

                #Calculate thickness if valid
                match = re.search(r'(\d+)[-_](\d+)cm', layer_name)
                if match:
                    lower_depth_cm = int(match.group(1))
                    upper_depth_cm = int(match.group(2))
                    thickness_m = round((upper_depth_cm - lower_depth_cm) / 100.0, 4)

                feature.SetField(f"{layer_name}_soil_type", soil_name)
                feature.SetField(f"{layer_name}_layer_thickness", thickness_m)

            #Update the feature in the layer
            combined_layer.SetFeature(feature)

        #Clean up
        combined_layer = None
        gpkg_ds = None

        #Step 4: Load the GeoPackage layer into QGIS
        result_layer = QgsVectorLayer(f"{output_gpkg}|layername={combined_layer_name}", combined_layer_name, "ogr")
        if not result_layer.isValid():
            raise RuntimeError(f"Failed to load combined layer '{combined_layer_name}' into QGIS.")
        
        field_names = []
        #Iterate over all fields in the layer and append fields for final output
        for field in result_layer.fields():
            if field.name().endswith("soil_type") or field.name().endswith("layer_thickness"):
                field_names.append(field.name())

        #Remove field "DN" (only relevant for internal processing)
        field_name_to_remove = "DN"
        field_index = result_layer.fields().indexOf(field_name_to_remove)
        
        #Check if the field exists
        if field_index != -1:
            result_layer.startEditing()
            result_layer.deleteAttribute(field_index)
            result_layer.commitChanges()

        try:
            dissolve_params = {
                    'INPUT': result_layer,
                    'FIELD': field_names,  #Dissolve all features; add fields to dissolve by specific attributes
                    'OUTPUT': 'TEMPORARY_OUTPUT',
                    'SEPARATE_DISJOINT': False
            }
            result_layer = processing.run("qgis:dissolve", dissolve_params)['OUTPUT']

        except:
            result_layer, _ = self.make_geometries_valid(result_layer)
            dissolve_params = {
                    'INPUT': result_layer,
                    'FIELD': field_names,  #Dissolve all features; add fields to dissolve by specific attributes
                    'OUTPUT': 'TEMPORARY_OUTPUT',
                    'SEPARATE_DISJOINT': False
            }
            result_layer = processing.run("qgis:dissolve", dissolve_params)['OUTPUT']
        
        QgsProject.instance().addMapLayer(result_layer)
        return result_layer, field_names
    
    def convertArrayToVectorLayer(self, array, geotransform, projection, original_dataset, field_name, output_gpkg, layer_name):
        '''
            If user wants to output every soil type layer, this is used. Also used for BDOD.
        '''
        nodata_value = -9999 #Qgis interprets this as nodata
        #Get dimensions
        rows, cols = array.shape
        #Create an in-memory GDAL dataset with the correct dimensions
        driver = gdal.GetDriverByName('MEM')
        dataset = driver.Create('', cols, rows, 1, gdal.GDT_Float32)
        
        #Convert bdod values to bdod classes
        if field_name != 'talsim_soilid':
            class_boundaries = [0, 1.3, 1.55, 1.75, 1.95, np.inf]
            class_values = [1, 2, 3, 4, 5]

            #Replace values in the array with classes
            classified_array = np.full(array.shape, nodata_value, dtype=np.int32)  #Initialize with no-data value
            for i in range(len(class_boundaries) - 1):
                lower_bound = class_boundaries[i]
                upper_bound = class_boundaries[i + 1]
                classified_array[
                    (array >= lower_bound) & (array < upper_bound)
                ] = class_values[i]
            array = classified_array

        #Set geotransform and projection
        dataset.SetGeoTransform(geotransform)
        dataset.SetProjection(projection)
        
        #Write the numpy array data to the GDAL dataset
        band = dataset.GetRasterBand(1)
        band.WriteArray(array)
        band.SetNoDataValue(nodata_value)
    
        #Get the CRS of the raster
        raster_crs = original_dataset.GetProjection()
        srs = osr.SpatialReference()
        srs.ImportFromWkt(raster_crs)
        raster_epsg = srs.GetAttrValue("AUTHORITY", 1)  #Get EPSG code if available

        #Create the CRS for the QGIS layer
        if raster_epsg:
            crs = f"EPSG:{raster_epsg}"
        else:
            crs = QgsCoordinateReferenceSystem()
            crs.createFromWkt(raster_crs)
        
        #Set up the GeoPackage driver
        gpkg_driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(output_gpkg):
            gpkg_ds = gpkg_driver.Open(output_gpkg, 1)  #'1' for update mode
            if gpkg_ds is None:
                raise RuntimeError(f"Failed to open existing GeoPackage at {output_gpkg}")
        else:
            #Create a new GeoPackage
            gpkg_ds = gpkg_driver.CreateDataSource(output_gpkg)
            if gpkg_ds is None:
                raise RuntimeError(f"Failed to create GeoPackage at {output_gpkg}")

        #Create a file path
        layer_name = layer_name.replace("_mean", "")
        if not layer_name.startswith("bdod"):
            layer_name = 'soiltype_' + layer_name

        #Create a new layer in the GeoPackage
        temp_layer = gpkg_ds.CreateLayer(layer_name, srs, ogr.wkbPolygon)
        if temp_layer is None:
            raise RuntimeError(f"Failed to create layer '{layer_name}' in GeoPackage.")

        #Add a field to hold the talsim-soilid
        field_defn = ogr.FieldDefn(field_name, ogr.OFTInteger)

        temp_layer.CreateField(field_defn)

        #Confirm the field was added successfully
        field_index = temp_layer.GetLayerDefn().GetFieldIndex(field_name)

        #Polygonize
        err = gdal.Polygonize(band, None, temp_layer, field_index, [], callback=None)
        if err != 0:
            self.log_to_qtalsim_tab("Polygonization failed with error code:", Qgis.Critical)
        
        #Check if polygons were created
        if temp_layer.GetFeatureCount() == 0 or temp_layer.GetGeomType() != ogr.wkbPolygon:
            self.log_to_qtalsim_tab("No features created by Polygonize.", Qgis.Critical)

        #Delete no data polygons
        temp_layer.StartTransaction() 
        for feature in temp_layer:
            if feature.GetField(field_name) == nodata_value:
                temp_layer.DeleteFeature(feature.GetFID())
        temp_layer.CommitTransaction()  #Commit deletion transaction

        #Load the GeoPackage layer into QGIS
        result_layer = QgsVectorLayer(f"{output_gpkg}|layername={layer_name}", f"{layer_name}", "ogr")
        result_layer,_ = self.make_geometries_valid(result_layer)
        self.log_to_qtalsim_tab(f"Successfully created layer {layer_name}", Qgis.Info)
        return result_layer, layer_name
    
    def soilMapping(self):
        '''
            Finds the correct soil type for every clay/silt/sand combination. 
        '''
        self.polyX = []   #Polygon X-values
        self.polyY = []   #Polygon Y-values
        self.count = None #Count polygon coordinates

        gpkgOutputPath = os.path.join(self.outputFolder, "soil_types.gpkg")

        #Geotransform and projection are taken from the project input dataset
        input_file_path = os.path.join(self.path_proj, 'clay_0-5cm_mean.tif')  
        original_dataset = gdal.Open(input_file_path)
        geotransform = original_dataset.GetGeoTransform()
        projection = original_dataset.GetProjection()
        array_dict = {}

        #Loop over soil-layers
        for layer_name, data_array in self.layer_data.items():
            if data_array is None:
                continue
            clay_array = data_array[0]
            silt_array = data_array[1]
            sand_array = data_array[2]
            
            if clay_array.shape != silt_array.shape or clay_array.shape != sand_array.shape or silt_array.shape != sand_array.shape:
                self.log_to_qtalsim_tab("The input layers have different shapes.", Qgis.Warning)
            
            cols, rows = clay_array.shape
            
            #Initialize result array with nodata values
            nodata = -9999 #no data value
            boa_array = np.full([cols, rows], nodata, dtype=int) #array to store the soil types of the pixels
            for x in range(cols):
                for y in range(rows):
                    sand = sand_array[x,y]
                    clay = clay_array[x,y]
                    silt = silt_array[x,y]
                
                    #Skip cells where any component is NoData
                    if np.isnan(sand) or np.isnan(clay) or np.isnan(silt) or sand == nodata or clay == nodata or silt == nodata:
                        continue
                    
                    #Check that sum is 100%
                    sum = sand + clay + silt
                    if sum < 95.0 or sum > 102.0:
                        self.log_to_qtalsim_tab(f"Sum of shares is not 100%%: %.2f%%! { (x, y, sum)}", Qgis.Warning)
                    
                    #adjust to 100%
                    clay = clay + clay / sum * (100.0 - sum)
                    silt = silt + silt / sum * (100.0 - sum)
                    sand = sand + sand / sum * (100.0 - sum)

                    #Schleife über Bodenarten-Polygone
                    bda = self.boa[0][0]
                    self.polyX = [None]*30
                    self.polyY = [None]*30
                    self.count = -1
                    for i in range(len(self.boa)):
                        if bda != self.boa[i][0]: #Check if this soil type/polygon is finished
                            if self.pointInPoly(clay, silt):
                                # found
                                break
                            self.polyX = [None]*30 #Reset polyX, when soil type changes
                            self.polyY = [None]*30 #Reset polyY, when soil type changes
                            self.count = 0
                            self.polyX[self.count] = self.boa[i][1] #Clay as x-coordinate
                            self.polyY[self.count] = self.boa[i][2] #Silt as y-coordinate
                            bda = self.boa[i][0]
                        else: #if still the same polygon/soil type
                            self.count += 1 #Number of points in the polygon
                            self.polyX[self.count] = self.boa[i][1] #Clay as x-coordinate
                            self.polyY[self.count] = self.boa[i][2] #Silt as y-coordinate
                            
                    boa_array[x, y] = self.talsim_soilids[bda] #store the soil type of the current pixel
            self.log_to_qtalsim_tab(f"Finished calculation of soil types of layer {layer_name}.", Qgis.Info)

            #Convert the boa array to a vector layer
            layer_name = layer_name.replace(".tif", "")
            if not self.checkboxSaveHorizons.isChecked(): #if user does not want to save the soil type layer for every soil type
                array_dict[layer_name] = boa_array
            else:
                result_layer, layer_name = self.convertArrayToVectorLayer(boa_array, geotransform, projection, original_dataset, 'talsim_soilid', gpkgOutputPath, layer_name)

                #Add the "soil_type" column
                result_layer.dataProvider().addAttributes([QgsField("soil_type", QVariant.String)])
                result_layer.dataProvider().addAttributes([QgsField("layer_thickness", QVariant.Double)])
                result_layer.updateFields()

                def get_soil_type_by_id(talsim_soilid):
                    for key, value in self.talsim_soilids.items():
                        if value == talsim_soilid:
                            return key
                    return 'Unknown' 
                
                self.log_to_qtalsim_tab(f"Further processing layer {layer_name}...", Qgis.Info)

                #Populate the "soil_type" field based on talsim_soilid
                with edit(result_layer):
                    for feature in result_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
                        fid = feature.id()
                        talsim_soilid = feature['talsim_soilid'] 
                        soil_type = get_soil_type_by_id(int(talsim_soilid))
                        result_layer.changeAttributeValue(fid, result_layer.fields().indexFromName(self.fieldNameSoilType), soil_type)

                        match = re.search(r'(\d+)[-_](\d+)cm', layer_name)
                        if match:
                            lower_depth_cm = int(match.group(1))
                            upper_depth_cm = int(match.group(2))
                            thickness_m = round(upper_depth_cm / 100 - lower_depth_cm / 100, 4)
                            result_layer.changeAttributeValue(fid, result_layer.fields().indexFromName('layer_thickness'), float(thickness_m))
                    
                result_layer.setName(layer_name)
                self.soilTypeLayers.append(result_layer)

        if self.checkboxSaveHorizons.isChecked():
            #Export soil type layers as geopackage
            self.layers_to_combine = []
            field_names = []
            
            for i, layer in enumerate(self.soilTypeLayers):
                layer_name = layer.name() #Get the layer name
                soil_layer = '_'.join(layer_name.split('_')[1:])
                uri = f"{gpkgOutputPath}|layername={layer_name}"
                gpkg_layer = QgsVectorLayer(uri, layer_name, "ogr")
                dissolve_params = {
                    'INPUT': gpkg_layer,
                    'FIELD': ['talsim_soilid', "soil_type", "layer_thickness"],  #Dissolve all features; add fields to dissolve by specific attributes
                    'OUTPUT': 'TEMPORARY_OUTPUT',
                    'SEPARATE_DISJOINT': False
                }
                gpkg_layer_dissolved = processing.run("qgis:dissolve", dissolve_params)['OUTPUT']
                #Add the layers to the Qgis project
                if gpkg_layer_dissolved.isValid():
                    field_mapping = {}
                    layer_fields = gpkg_layer_dissolved.fields()
                    for field in layer_fields:
                        new_field_name = f"{soil_layer}_{field.name()}"
                        field_index = gpkg_layer_dissolved.fields().indexOf(field.name())
                        if field_index != -1:
                            field_mapping[field_index] = new_field_name

                        field_names.append(new_field_name)
                    # Apply the renaming
                    if field_mapping:
                        gpkg_layer_dissolved.dataProvider().renameAttributes(field_mapping)
                        gpkg_layer_dissolved.updateFields()
                    if not self.combinedSoilTypeLayer:
                        self.layers_to_combine.append(gpkg_layer_dissolved)  


            self.log_to_qtalsim_tab("Combining the soil layers to one soil type layer...", Qgis.Info)
            #2.: Combine the layers to one soil type layer, holding the different soil layers in different columns
            try:
                if self.layers_to_combine and len(self.layers_to_combine) >= 2:
                    params = {
                        'INPUT': self.layers_to_combine[0],
                        'OVERLAYS' : self.layers_to_combine[1:],  #Input layers as a list
                        'OVERLAY_FIELDS_PREFIX':'',
                        'OUTPUT':'TEMPORARY_OUTPUT'
                    }
                    #Run the multiple intersection tool
                    combined_layer = processing.run("qgis:multiintersection", params)['OUTPUT']

            except:
                if self.layers_to_combine and len(self.layers_to_combine) >= 2:
                    for i, layer in enumerate(self.layers_to_combine):
                        self.layers_to_combine[i], _ = self.make_geometries_valid(layer)
                    params = {
                        'INPUT': self.layers_to_combine[0],
                        'OVERLAYS' : self.layers_to_combine[1:],  #Input layers as a list
                        'OVERLAY_FIELDS_PREFIX':'',
                        'OUTPUT':'TEMPORARY_OUTPUT'
                    }
                    #Run the multiple intersection tool
                    combined_layer = processing.run("qgis:multiintersection", params)['OUTPUT']

            if not self.combinedSoilTypeLayer:
                #Necessary to delete the 'fid' column to be able to save the combined layer with all soil types to a geopackage
                #Get the fields (attributes) from the combined layer
                fields = combined_layer.fields()

                #Identify columns that are named 'fid' or start with 'fid'
                fields_to_remove = [field.name() for field in fields if field.name().lower().startswith('fid')]

                if fields_to_remove:
                    #Get the indices of the fields to remove
                    field_indices = [combined_layer.fields().indexOf(field) for field in fields_to_remove]
                    #Start an editing session to remove fields
                    combined_layer.startEditing()
                    #Remove the fields
                    combined_layer.dataProvider().deleteAttributes(field_indices)
                    #Update the fields in the layer
                    combined_layer.updateFields()
                    combined_layer.commitChanges()

                self.log_to_qtalsim_tab("Dissolving the soil type layer...", Qgis.Info)
                #Dissolve the combined soil layer by all soil columns
                try:
                    combined_layer = processing.run("native:dissolve", {'INPUT':combined_layer,'FIELD':field_names,'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
                except:
                    combined_layer, _ = self.make_geometries_valid(combined_layer)
                    combined_layer = processing.run("native:dissolve", {'INPUT':combined_layer,'FIELD':field_names,'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "GPKG"
                options.fileEncoding = "UTF-8"
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer  #This ensures it adds a new layer
                output_layer_name = "Soil Types Combined"
                options.layerName = output_layer_name
                error = QgsVectorFileWriter.writeAsVectorFormatV2(
                            combined_layer,
                            gpkgOutputPath,
                            QgsProject.instance().transformContext(),
                            options
                        )
                
                combined_soil_type_layer = QgsVectorLayer(f"{gpkgOutputPath}|layername={output_layer_name}", output_layer_name, "ogr")
            else:
                combined_soil_type_layer = self.combinedSoilTypeLayer
            self.log_to_qtalsim_tab(f"Soil type vector layers were saved here: {gpkgOutputPath}", Qgis.Info)
        
        else: #if the user does not need every soil type layer
            combined_soil_type_layer, field_names = self.polygonize_and_combine(list(array_dict.values()), list(array_dict.keys()), geotransform, projection, gpkgOutputPath, 'Soil Types Combined')

        self.log_to_qtalsim_tab(f"Processing bulk density layers...", Qgis.Info)

        #Add bulk density raster layers
        gpkgOutputPathBdod = os.path.join(self.outputFolder, "bdod.gpkg")
        bdodLayers = []
        for layer_name, data_array in self.bdod_data.items():
            if data_array is None:
                continue
            layer_name = 'bdod_' + layer_name
            
            #Convert numpy array to raster and add to project
            layer_name = layer_name.replace(".tif", "") #remove .tif from layer_name

            vector_layer, layer_name = self.convertArrayToVectorLayer(data_array, geotransform, projection, original_dataset, self.fieldNameBdodClass, gpkgOutputPathBdod, layer_name)
            #Convert BDOD-layer to vector layer            
            try:
                vector_layer = processing.run("native:dissolve", {'INPUT':vector_layer,'FIELD':[self.fieldNameBdodClass],'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
            except:
                vector_layer, _ = self.make_geometries_valid(vector_layer)
                vector_layer = processing.run("native:dissolve", {'INPUT':vector_layer,'FIELD':[self.fieldNameBdodClass],'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

            vector_layer.setName(layer_name)

            bdodLayers.append(vector_layer) #store bdod vector layers


        #Export bulk density layers as geopackage
        bdod_dissolve_fields = [] #stores the field names of bdod classes in final layer 
        for layer in bdodLayers:
            layer_name = layer.name()  # Get the layer name
            uri = f"{gpkgOutputPathBdod}|layername={layer_name}"
            
            gpkg_layer = QgsVectorLayer(uri, layer_name, "ogr")
            
            field_mapping = {}
            layer_fields = gpkg_layer.fields()
            bdod_layer_name = '_'.join(layer_name.split('_')[1:])
            
            for field in layer_fields:
                new_field_name = f"{bdod_layer_name}_{field.name()}"
                field_index = gpkg_layer.fields().indexOf(field.name())
                if field_index != -1:
                    field_mapping[field_index] = new_field_name

                field_names.append(new_field_name)

            #Apply the renaming
            if field_mapping:
                gpkg_layer.dataProvider().renameAttributes(field_mapping)
                gpkg_layer.updateFields()
            #Only keep the BDOD-class field and delete all other fields
            fields = gpkg_layer.fields()
            gpkg_layer.startEditing()

            #Collect the indices of fields that do NOT end with '_class'
            fields_to_delete = []
            for field in fields:
                if not field.name().endswith('_class'):
                    index = gpkg_layer.fields().indexFromName(field.name())
                    fields_to_delete.append(index)
                else:
                    bdod_dissolve_fields.append(field.name())

            #Remove the fields
            if fields_to_delete:
                gpkg_layer.dataProvider().deleteAttributes(fields_to_delete)
            gpkg_layer.updateFields()
            gpkg_layer.commitChanges()

            self.bdod_layers_to_combine.append(gpkg_layer) 

            #Add the layers to the Qgis project
            #if gpkg_layer.isValid():
                #QgsProject.instance().addMapLayer(gpkg_layer, False)
                #self.layer_group.addLayer(gpkg_layer)

        self.log_to_qtalsim_tab(f"Bulk density vector layers were saved here: {gpkgOutputPathBdod}", Qgis.Info)
  
        #Combine Soil types and BDOD
        #2.: Combine the layers to one soil type layer, holding the different soil layers in different columns
        try:
            for i, layer in enumerate(self.bdod_layers_to_combine + [combined_soil_type_layer]):
                singleparts_layer = processing.run("native:multiparttosingleparts", {'INPUT': layer,'OUTPUT': 'TEMPORARY_OUTPUT'}, feedback=None)['OUTPUT']
                processing.run("native:createspatialindex", {'INPUT': singleparts_layer})
                    
                if i < len(self.bdod_layers_to_combine):  
                    self.bdod_layers_to_combine[i] = singleparts_layer
                else:
                    combined_soil_type_layer = singleparts_layer

            params = {
                'INPUT': combined_soil_type_layer,
                'OVERLAYS' : self.bdod_layers_to_combine[0:],  #Input layers as a list
                'OVERLAY_FIELDS_PREFIX':'',
                'OUTPUT':'TEMPORARY_OUTPUT'
            }

            finalLayer = processing.run("qgis:multiintersection", params)['OUTPUT']
        except:
            for i, layer in enumerate(self.bdod_layers_to_combine):
                self.bdod_layers_to_combine[i], _ = self.make_geometries_valid(layer)
            combined_soil_type_layer, _ = self.make_geometries_valid(combined_soil_type_layer)
            params = {
                'INPUT': combined_soil_type_layer,
                'OVERLAYS' : self.bdod_layers_to_combine[0:],  #Input layers as a list
                'OVERLAY_FIELDS_PREFIX':'',
                'OUTPUT':'TEMPORARY_OUTPUT'
            }

            finalLayer = processing.run("qgis:multiintersection", params)['OUTPUT']

        dissolve_list = bdod_dissolve_fields + field_names
        try:
            finalLayer = processing.run("native:dissolve", {'INPUT':finalLayer,'FIELD':dissolve_list,'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        except:
            finalLayer, _ = self.make_geometries_valid(finalLayer)
            finalLayer = processing.run("native:dissolve", {'INPUT':finalLayer,'FIELD':dissolve_list,'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

        #Delete the 'fid' columns to be able to save the combined layer with all soil types to a geopackage
        #Get the fields (attributes) from the combined layer
        fields = finalLayer.fields()
        QgsProject.instance().addMapLayer(finalLayer, False)
        #Identify columns that are named 'fid' or start with 'fid' and the id columns
        fields_to_remove = [field.name() for field in fields if field.name().lower().startswith('fid') or field.name().lower().endswith('id')]

        if fields_to_remove:
            #Get the indices of the fields to remove
            field_indices = [finalLayer.fields().indexOf(field) for field in fields_to_remove]
            #Start an editing session to remove fields
            finalLayer.startEditing()
            #Remove the fields
            finalLayer.dataProvider().deleteAttributes(field_indices)
            #Update the fields in the layer
            finalLayer.updateFields()
            finalLayer.commitChanges()

        #Sort the fields by the soil layer/horizon
        fields = finalLayer.fields()
        sorted_fields = sorted(fields, key=lambda field: int(field.name().split('_')[0].split('-')[0]))
        layer_crs = finalLayer.crs().authid()
        finalLayerOrdered = QgsVectorLayer(f"Polygon?crs={layer_crs}", "Soil Types BDOD Combined", "memory")
        final_layer_ordered_data_provider = finalLayerOrdered.dataProvider()

        final_layer_ordered_data_provider.addAttributes([QgsField(field.name(), field.type()) for field in sorted_fields])
        finalLayerOrdered.updateFields() 
        for feature in finalLayer.getFeatures():
            new_feature = QgsFeature(finalLayerOrdered.fields())
            new_feature.setGeometry(feature.geometry())
            #Map attributes according to sorted fields
            new_feature.setAttributes([feature[field.name()] for field in sorted_fields])
            final_layer_ordered_data_provider.addFeature(new_feature)

        #Save the final Layer
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer  #This ensures it adds a new layer
        output_layer_name = 'Soil Types BDOD Combined'
        options.layerName = output_layer_name
        error = QgsVectorFileWriter.writeAsVectorFormatV2(
                    finalLayerOrdered,
                    gpkgOutputPath,
                    QgsProject.instance().transformContext(),
                    options
                )
        
        finalLayerSoil = QgsVectorLayer(f"{gpkgOutputPath}|layername={output_layer_name}", output_layer_name, "ogr")
        if finalLayerSoil.isValid():
            QgsProject.instance().addMapLayer(finalLayerSoil, False)
            tree_layer = QgsLayerTreeLayer(finalLayerSoil)
            self.layer_group.addChildNode(tree_layer)

        self.log_to_qtalsim_tab(f"Final soil layer was saved here: {gpkgOutputPath}", Qgis.Info)

    def apply_filtered_symbology(self, gpkg_layer, pathSymbology, symbology_field):
        """
            Loads symbology from a QML file and shows unique values of layer gpkg_layer.
        """
        #Load the symbology from the QML file
        gpkg_layer.loadNamedStyle(pathSymbology, True)
        
        #Get unique values from the layer
        unique_values = gpkg_layer.uniqueValues(gpkg_layer.fields().indexOf(symbology_field))

        #Get the renderer from the layer
        renderer = gpkg_layer.renderer()

        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            #Get the current categories from the symbology file
            categories = renderer.categories()

            #Iterate over categories and remove those that are not in the unique values
            for idx in reversed(range(len(categories))):  #Reverse loop to avoid index shifting when deleting
                category = categories[idx]
                if category.value() not in unique_values:
                    #Delete the category if its value is not in the unique values
                    renderer.deleteCategory(idx)
            
            gpkg_layer.setRenderer(renderer)

            #Repaint the layer to apply the filtered symbology
            gpkg_layer.triggerRepaint()

    def on_resample_toggled(self, checked):
        self.spinboxResample.setEnabled(checked)

    
                     
    


        
        