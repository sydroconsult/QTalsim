
import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog, QDialog, QDialogButtonBox
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject, Qgis, QgsCoordinateReferenceSystem, QgsRasterLayer, QgsVectorLayer, QgsField, edit, QgsLayerTreeLayer
from qgis.gui import QgsProjectionSelectionDialog
from osgeo import gdal
import processing
import numpy as np
import webbrowser

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
        self.path_proj = None
        self.destinationCRS = None
        self.outputPath.clear()
        self.outputCRS.clear()

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

    def selectCrs(self): 
        '''
            Saves CRS selected by user
        '''
        # Create the CRS selection dialog
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
            Downloads ISRIC soil data (clay, silt, sand share and bulk density value.)
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
                    params = {
                        'INPUT': self.layerBoundingBox,
                        'TARGET_CRS': homolosine_crs,
                        'OUTPUT': 'memory:'  # Store the reprojected layer in memory
                    }

                    # Reproject the layer
                    reprojectedLayerResult = processing.run("native:reprojectlayer", params)
                    self.layerBoundingBox = reprojectedLayerResult['OUTPUT']   
                
                #If bounding box layer is raster layer
                elif isinstance(self.layerBoundingBox, QgsRasterLayer): 
                    params = {
                        'INPUT': self.layerBoundingBox,
                        'TARGET_CRS': homolosine_crs,  # Use the CRS object for Homolosine
                        'RESAMPLING': 0,  # Choose the resampling method (0=nearest neighbor, 1=bilinear, etc.)
                        'NODATA': None,  # Handle NoData values if needed
                        'TARGET_RESOLUTION': None,  # Set if you want to specify a resolution
                        'OPTIONS': '',
                        'DATA_TYPE': 0,  # Keep the data type (0=Byte, 1=Int16, etc.)
                        'TARGET_EXTENT': None,  # Use None to keep the same extent
                        'TARGET_EXTENT_CRS': None,  # If extent is specified, its CRS should be provided
                        'MULTITHREADING': False,
                        'OUTPUT': 'TEMPORARY_OUTPUT' # Store the reprojected raster in memory
                    }

                    # Reproject the raster layer
                    reprojectedLayerResult = processing.run("gdal:warpreproject", params)
                    self.layerBoundingBox = QgsRasterLayer(reprojectedLayerResult['OUTPUT'], selected_layer_name + '_reprojected')
                QgsProject.instance().addMapLayer(self.layerBoundingBox, False)
            self.layerBoundingBox

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

            # Datasets to process
            # name : path_to_vrt
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
            res = 250 
            sg_url = "/vsicurl/" + url

            kwargs = {'format': 'GTiff', 
                    'projWin': bb, 
                    'projWinSRS': igh, 
                    'xRes': res, 
                    'yRes': res, 
                    'creationOptions': ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "BIGTIFF=YES"]}

            #Save files
            for name, loc in datasets.items():
                try:
                    self.log_to_qtalsim_tab(f"Processing... {name}", Qgis.Info)
                    
                    file_orig = os.path.join(path_out, name + '.tif')
                    file_proj = os.path.join(self.path_proj, name + '.tif')

                    ds = gdal.Translate(file_orig, sg_url + loc, **kwargs)
                    ds = gdal.Warp(file_proj, ds, dstSRS=self.dstSRS)
                        
                    ds = None
                except Exception as e:
                    self.log_to_qtalsim_tab(f"Error processing {name}: {str(e)}", Qgis.Critical)
                    continue

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
            self.log_to_qtalsim_tab("Calculating soil types from clay, silt and sand share...", Qgis.Info)
            root = QgsProject.instance().layerTreeRoot()

            # Create a new group in the layer tree
            group_name = "QTalsim Soil Layers"
            self.layer_group = root.addGroup(group_name)

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
        self.layer_data = {}
        self.bdod_data = {}

        def read_tif_as_array(file_path):
            dataset = gdal.Open(file_path)
            array = dataset.ReadAsArray()
            
            # Get the "no data" value from the dataset
            no_data_value = dataset.GetRasterBand(1).GetNoDataValue()
            
            if no_data_value is not None:
                # Replace "no data" values in the array with numpy's NaN
                array = np.where(array == no_data_value, np.nan, array)
            
            return array

        for file_name in os.listdir(self.path_proj):
            if file_name.endswith('.tif'):
                base_name = file_name.split('_')[0]  # 'clay', 'sand', 'silt', or 'bdod'
                layer = '_'.join(file_name.split('_')[1:])  # e.g., '0-5cm_mean.tif'
                
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
                    
                    self.layer_data[layer][base_name] = array
        
        self.log_to_qtalsim_tab("Recalculating the clay, silt and sand values.", Qgis.Info)

        #Convert dicts to numpy arrays and convert the units of the data (https://www.isric.org/explore/soilgrids/faq-soilgrids#What_do_the_filename_codes_mean)
        for layer in self.layer_data:
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
            self.bdod_data[layer] = self.bdod_data[layer] / 100


    def add_single_band_numpy_array_to_qgis(self, numpy_array, geotransform, projection, layer_name):
        '''
            Converts a numpy array to a raster file/layer, saves the file to the output-folder and adds it to the Qgis project.
        '''
        #Get dimensions
        rows, cols = numpy_array.shape

        #Create an in-memory GDAL dataset with the correct dimensions
        driver = gdal.GetDriverByName('MEM')
        dataset = driver.Create('', cols, rows, 1, gdal.GDT_Float32)
        
        #Set geotransform and projection
        dataset.SetGeoTransform(geotransform)
        dataset.SetProjection(projection)
        
        #Write the numpy array data to the GDAL dataset
        band = dataset.GetRasterBand(1)
        band.WriteArray(numpy_array)
        
        nodata_value = -9999 #Qgis interprets this as nodata
        band.SetNoDataValue(nodata_value)
    
        #Create a file path
        layer_name = layer_name.replace("_mean", "")
        if not layer_name.startswith("bdod"):
            layer_name = 'soiltype_' + layer_name
        output_path_raster = os.path.join(self.outputFolder, layer_name)
        
        #Save the dataset to this path
        gdal.GetDriverByName('GTiff').CreateCopy(output_path_raster, dataset)

        #Add the raster layer to the QGIS project from the in-memory path
        raster_layer = QgsRasterLayer(output_path_raster, layer_name)
        QgsProject.instance().addMapLayer(raster_layer, False)
        self.layer_group.addLayer(raster_layer) 
        self.log_to_qtalsim_tab(f"Created layer '{layer_name}' successfully!", Qgis.Info)
        
        #Cleanup: remove the in-memory file
        #gdal.Unlink(tmp_path) - doesnt work correctly if unlinked

        return raster_layer, layer_name

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
            return True
        
        return False

    def convertRasterToVectorLayer(self, raster_layer, field_name):
        #Convert the raster_layer to polygon_layer
        result_layer = processing.run("native:pixelstopolygons", {'INPUT_RASTER':raster_layer,'RASTER_BAND':1,'FIELD_NAME':field_name,'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        result_layer = processing.run("native:dissolve", {'INPUT':result_layer,'FIELD':[field_name],'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        'talsim_soilid'
        #Buffer and negative buffer to remove borders of pixels, when neighboring a pixel with the same soil type
        result_layer = processing.run("native:buffer", {
            'INPUT': result_layer,
            'DISTANCE': 0.01,
            'SEGMENTS': 5,
            'END_CAP_STYLE': 0,
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'DISSOLVE': False,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        vector_layer = processing.run("native:buffer", {
            'INPUT': result_layer,
            'DISTANCE': -0.01,
            'SEGMENTS': 5,
            'END_CAP_STYLE': 0,
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'DISSOLVE': False,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        return vector_layer
    
    def soilMapping(self):
        '''
            Finds the correct soil type for every clay/silt/sand combination. 
        '''
        self.polyX = []   # Polygon X-Werte
        self.polyY = []   # Polygon Y-Werte
        self.count = None # Anzahl Polygon-Koordinaten
        soilTypeLayers = []

        #Loop over soil-layers
        for layer_name, data_array in self.layer_data.items():
            clay_array = data_array[0]
            silt_array = data_array[1]
            sand_array = data_array[2]
            
            if clay_array.shape != silt_array.shape or clay_array.shape != sand_array.shape or silt_array.shape != sand_array.shape:
                self.log_to_qtalsim_tab("The input layers have different shapes.", Qgis.Warning)
            
            cols, rows = clay_array.shape
            
            #Initialize result array with nodata values
            nodata = -9999
            boa_array = np.full([cols, rows], nodata, dtype=int)
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
                    
                    # adjust to 100%
                    clay = clay + clay / sum * (100.0 - sum)
                    silt = silt + silt / sum * (100.0 - sum)
                    sand = sand + sand / sum * (100.0 - sum)

                    # Schleife über Bodenarten-Polygone
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
                        else: #if still the same polygon
                            self.count += 1 #Number of points in the polygon
                            self.polyX[self.count] = self.boa[i][1] #Clay as x-coordinate
                            self.polyY[self.count] = self.boa[i][2] #Silt as y-coordinate
                            
                    boa_array[x, y] = self.talsim_soilids[bda]

            #Geotransform and projection are taken from the project input dataset
            input_file_path = os.path.join(self.path_proj, 'clay_0-5cm_mean.tif')  
            original_dataset = gdal.Open(input_file_path)
            geotransform = original_dataset.GetGeoTransform()
            projection = original_dataset.GetProjection()

            #Add the soil type layer to QGIS
            raster_layer, layer_name = self.add_single_band_numpy_array_to_qgis(boa_array, geotransform, projection, layer_name)
            layer_name = layer_name.replace(".tif", "")

            #Convert to Vector Layer
            result_layer = self.convertRasterToVectorLayer(raster_layer, 'talsim_soilid')

            #Add the "soil_type" column
            result_layer.dataProvider().addAttributes([QgsField("soil_type", QVariant.String)])
            result_layer.updateFields()

            def get_soil_type_by_id(talsim_soilid):
                for key, value in self.talsim_soilids.items():
                    if value == talsim_soilid:
                        return key
                return 'Unknown' 

            #Populate the "soil_type" field based on talsim_soilid
            with edit(result_layer):
                for feature in result_layer.getFeatures():
                    talsim_soilid = feature['talsim_soilid']
                    soil_type = get_soil_type_by_id(int(talsim_soilid))
                    feature['soil_type'] = soil_type
                    result_layer.updateFeature(feature)
            
            result_layer.setName(layer_name)
            soilTypeLayers.append(result_layer)

        #Export soil type layers as geopackage
        gpkgOutputPath = os.path.join(self.outputFolder, "soil_types.gpkg")
        processing.run("native:package", {'LAYERS':soilTypeLayers,'OUTPUT':gpkgOutputPath,'OVERWRITE':True,'SAVE_STYLES':True,'SAVE_METADATA':True,'SELECTED_FEATURES_ONLY':False,'EXPORT_RELATED_LAYERS':False})
        
        for layer in soilTypeLayers:
            layer_name = layer.name()  # Get the layer name
            uri = f"{gpkgOutputPath}|layername={layer_name}"
            
            gpkg_layer = QgsVectorLayer(uri, layer_name, "ogr")

            #Add the layers to the Qgis project
            if gpkg_layer.isValid():
                current_path = os.path.dirname(os.path.abspath(__file__))
                pathSymbology = os.path.join(current_path, "symbology", "SoilTypes.qml")

                gpkg_layer.loadNamedStyle(pathSymbology)
                gpkg_layer.triggerRepaint()

                QgsProject.instance().addMapLayer(gpkg_layer, False)

                tree_layer = QgsLayerTreeLayer(gpkg_layer)
                self.layer_group.addChildNode(tree_layer)

        self.log_to_qtalsim_tab(f"Soil type vector layers were saved here: {gpkgOutputPath}", Qgis.Info)

        
        #Add bulk density raster layers
        bdodLayers = []
        for layer_name, data_array in self.bdod_data.items():
            layer_name = 'bdod_' + layer_name
            bdod_raster_layer, layer_name = self.add_single_band_numpy_array_to_qgis(data_array, geotransform, projection, layer_name)
            vector_layer = self.convertRasterToVectorLayer(bdod_raster_layer, 'bbod')
            vector_layer.setName(layer_name)
            bdodLayers.append(vector_layer)

        #Export bulk density layers as geopackage
        gpkgOutputPathBdod = os.path.join(self.outputFolder, "bdod.gpkg")
        processing.run("native:package", {'LAYERS':bdodLayers,'OUTPUT':gpkgOutputPathBdod,'OVERWRITE':True,'SAVE_STYLES':True,'SAVE_METADATA':True,'SELECTED_FEATURES_ONLY':False,'EXPORT_RELATED_LAYERS':False})
        
        for layer in bdodLayers:
            layer_name = layer.name()  # Get the layer name
            uri = f"{gpkgOutputPathBdod}|layername={layer_name}"
            
            gpkg_layer = QgsVectorLayer(uri, layer_name, "ogr")
            
            #Add the layers to the Qgis project
            if gpkg_layer.isValid():
                QgsProject.instance().addMapLayer(gpkg_layer, False)
                self.layer_group.addLayer(gpkg_layer)

        self.log_to_qtalsim_tab(f"Bulk density vector layers were saved here: {gpkgOutputPathBdod}", Qgis.Info)



    
                     
    


        
        