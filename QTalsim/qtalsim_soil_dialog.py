
import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import  QFileDialog
from qgis.core import QgsProject, Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRasterLayer
from osgeo import gdal
import processing
import numpy as np

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

        #Main Functions
        self.connectButtontoFunction = self.mainPlugin.connectButtontoFunction
        self.getAllLayers = self.mainPlugin.getAllLayers #Function to get PolygonLayers
        self.start_operation = self.mainPlugin.start_operation
        self.end_operation = self.mainPlugin.end_operation
        self.log_to_qtalsim_tab = self.mainPlugin.log_to_qtalsim_tab

        #Connect functions
        self.connectButtontoFunction(self.onOutputFolder, self.selectOutputFolder) 
        self.connectButtontoFunction(self.onDownloadData, self.downloadData)
        self.fillLayerComboboxes()

    def fillLayerComboboxes(self):
        '''
            Fills all comboboxes with layers
        '''

        self.polygonLayers, self.rasterLayers = self.getAllLayers(QgsProject.instance().layerTreeRoot())
        #self.lineLayers = self.getAllLineLayers(QgsProject.instance().layerTreeRoot())

        #Sub-basins layer
        self.comboboxExtentLayer.clear() #clear combobox EZG from previous runs
        self.comboboxExtentLayer.addItem(self.noLayerSelected)
        self.comboboxExtentLayer.addItems([layer.name() for layer in self.rasterLayers])

    def selectOutputFolder(self):
        '''
            Function to select the output folder. 
        '''
        self.outputFolder = None
        self.outputFolder = QFileDialog.getExistingDirectory(self, "Select Folder","") #, options=options
        if self.outputFolder:
            self.outputPath.setText(self.outputFolder) 

    def downloadData(self):
        '''
        
        '''
        try:
            self.start_operation()
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
                '''
                Code zum Transformieren, falls als Input-Layer Vektor-Layer ausgewählt werden sollen
                params = {
                    'INPUT': self.layerBoundingBox,
                    'TARGET_CRS': homolosine_crs,
                    'OUTPUT': 'memory:'  # Store the reprojected layer in memory
                }

                # Reproject the layer
                reprojectedLayerResult = processing.run("native:reprojectlayer", params)
                self.layerBoundingBox = reprojectedLayerResult['OUTPUT']   
                '''
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
            print(extent)
            min_x = extent.xMinimum()
            min_y = extent.yMinimum()
            max_x = extent.xMaximum()
            max_y = extent.yMaximum()

            #Bounding-Box:
            bb = (min_x, max_y, max_x, min_y)

            # Destination SRS
            dstSRS = 'EPSG:25832' 

            path_out = os.path.join(self.outputFolder, 'orig')
            self.path_proj = os.path.join(self.outputFolder, 'proj')

            # Datasets to process
            # name : path_to_vrt
            url = "https://files.isric.org/soilgrids/latest/data/"
            datasets = {
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
                "bdod_0-5cm_mean": "bdod/bdod_0-5cm_mean.vrt",
                "bdod_5-15cm_mean": "bdod/bdod_5-15cm_mean.vrt",
                "bdod_15-30cm_mean": "bdod/bdod_15-30cm_mean.vrt",
                "bdod_30-60cm_mean": "bdod/bdod_30-60cm_mean.vrt",
                "bdod_60-100cm_mean": "bdod/bdod_60-100cm_mean.vrt",
                "bdod_100-200cm_mean": "bdod/bdod_100-200cm_mean.vrt",
                }

            #--------------------------------------------------------------------------------

            if not os.path.exists(path_out):
                os.mkdir(path_out)

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

            for name, loc in datasets.items():

                print("Processing %s..." % name)
                
                file_orig = os.path.join(path_out, name + '.tif')
                file_proj = os.path.join(self.path_proj, name + '.tif')

                ds = gdal.Translate(file_orig, sg_url + loc, **kwargs)
                ds = gdal.Warp(file_proj, ds, dstSRS=dstSRS)
                    
                del ds

        except Exception as e:
            self.log_to_qtalsim_tab(f"{e}", Qgis.Critical)

        finally:
            self.end_operation()
    
    def createCombinedLayer(self):

        layer_data = {}
        bdod_data = {}

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
            print(file_name)
            if file_name.endswith('.tif'):
                base_name = file_name.split('_')[0]  # 'clay', 'sand', 'silt', or 'bdod'
                layer = '_'.join(file_name.split('_')[1:])  # e.g., '0-5cm_mean.tif'
                
                #Read files with gdal
                file_path = os.path.join(self.path_proj, file_name)
                array = read_tif_as_array(file_path)

                #First, store the data in dictionaries
                if base_name == 'bdod':
                    if layer not in bdod_data:
                        bdod_data[layer] = array
                else:
                    if layer not in layer_data:
                        layer_data[layer] = {}
                    
                    layer_data[layer][base_name] = array

        
        #Convert dicts to numpy arrays and convert the units of the data (https://www.isric.org/explore/soilgrids/faq-soilgrids#What_do_the_filename_codes_mean)
        for layer in layer_data:
            clay = layer_data[layer].get('clay')
            sand = layer_data[layer].get('sand')
            silt = layer_data[layer].get('silt')

            #Create np-array
            if clay is not None and sand is not None and silt is not None:
                stacked_array = np.stack([clay, sand, silt])
                layer_data[layer] = stacked_array

                #Convert from g/kg to g/100g by dividing by 10
                stacked_array = stacked_array / 10
                
                #Store the converted array in the dictionary
                layer_data[layer] = stacked_array

            else:
                self.log_to_qtalsim_tab(f"Missing data for layer {layer}, skipping.", Qgis.Info)

        #Convert bulk density layer from cg/cm³ to kg/dm³ by dividing by 100
        for layer in bdod_data:
            bdod_data[layer] = bdod_data[layer] / 100

        #Ab hier gehört noch überarbeitet: 
        talsim_soilids = {
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

        boa = {} # {ID: (Kürzel, %Ton, %Schluff, %Sand, Bezeichnung), ...}
        boa[  0] = ("Ss",    0, 10, 90, "Sand")
        boa[  1] = ("Ss",    5, 10, 85, "Sand")
        boa[  2] = ("Ss",    5,  0, 95, "Sand")
        boa[  3] = ("Ss",    0,  0,100, "Sand")
        boa[  4] = ("Su2",   0, 25, 75, "schwach schluffiger Sand")
        boa[  5] = ("Su2",   5, 25, 70, "schwach schluffiger Sand")
        boa[  6] = ("Su2",   5, 10, 85, "schwach schluffiger Sand")
        boa[  7] = ("Su2",   0, 10, 90, "schwach schluffiger Sand")
        boa[  8] = ("Sl2",   5, 25, 70, "schwach lehmiger Sand")
        boa[  9] = ("Sl2",   8, 25, 67, "schwach lehmiger Sand")
        boa[ 10] = ("Sl2",   8, 10, 82, "schwach lehmiger Sand")
        boa[ 11] = ("Sl2",   5, 10, 85, "schwach lehmiger Sand")
        boa[ 12] = ("Sl3",   8, 25, 67, "mittel lehmiger Sand")
        boa[ 13] = ("Sl3",   8, 40, 52, "mittel lehmiger Sand")
        boa[ 14] = ("Sl3",  12, 40, 48, "mittel lehmiger Sand")
        boa[ 15] = ("Sl3",  12, 10, 78, "mittel lehmiger Sand")
        boa[ 16] = ("Sl3",   8, 10, 82, "mittel lehmiger Sand")
        boa[ 17] = ("St2",   8, 10, 82, "schwach toniger Sand")
        boa[ 18] = ("St2",  12, 10, 78, "schwach toniger Sand")
        boa[ 19] = ("St2",  17, 10, 73, "schwach toniger Sand")
        boa[ 20] = ("St2",  17,  0, 83, "schwach toniger Sand")
        boa[ 21] = ("St2",   5,  0, 95, "schwach toniger Sand")
        boa[ 22] = ("St2",   5, 10, 85, "schwach toniger Sand")
        boa[ 23] = ("Su3",   0, 40, 60, "mittel schluffiger Sand")
        boa[ 24] = ("Su3",   8, 40, 52, "mittel schluffiger Sand")
        boa[ 25] = ("Su3",   8, 25, 67, "mittel schluffiger Sand")
        boa[ 26] = ("Su3",   5, 25, 70, "mittel schluffiger Sand")
        boa[ 27] = ("Su3",   0, 25, 75, "mittel schluffiger Sand")
        boa[ 28] = ("Su4",   0, 50, 50, "stark schluffiger Sand")
        boa[ 29] = ("Su4",   8, 50, 42, "stark schluffiger Sand")
        boa[ 30] = ("Su4",   8, 40, 52, "stark schluffiger Sand")
        boa[ 31] = ("Su4",   0, 40, 60, "stark schluffiger Sand")
        boa[ 32] = ("Slu",   8, 50, 42, "schluffig-lehmiger Sand")
        boa[ 33] = ("Slu",  17, 50, 33, "schluffig-lehmiger Sand")
        boa[ 34] = ("Slu",  17, 40, 43, "schluffig-lehmiger Sand")
        boa[ 35] = ("Slu",  12, 40, 48, "schluffig-lehmiger Sand")
        boa[ 36] = ("Slu",   8, 40, 52, "schluffig-lehmiger Sand")
        boa[ 37] = ("Sl4",  17, 30, 53, "stark lehmiger Sand")
        boa[ 38] = ("Sl4",  17, 15, 68, "stark lehmiger Sand")
        boa[ 39] = ("Sl4",  17, 10, 73, "stark lehmiger Sand")
        boa[ 40] = ("Sl4",  12, 10, 78, "stark lehmiger Sand")
        boa[ 41] = ("Sl4",  12, 40, 48, "stark lehmiger Sand")
        boa[ 42] = ("Sl4",  17, 40, 43, "stark lehmiger Sand")
        boa[ 43] = ("St3",  17, 10, 73, "mittel toniger Sand")
        boa[ 44] = ("St3",  17, 15, 68, "mittel toniger Sand")
        boa[ 45] = ("St3",  25, 15, 60, "mittel toniger Sand")
        boa[ 46] = ("St3",  25,  0, 75, "mittel toniger Sand")
        boa[ 47] = ("St3",  17,  0, 83, "mittel toniger Sand")
        boa[ 48] = ("Ls2",  25, 50, 25, "schwach sandiger Lehm")
        boa[ 49] = ("Ls2",  25, 40, 35, "schwach sandiger Lehm")
        boa[ 50] = ("Ls2",  17, 40, 43, "schwach sandiger Lehm")
        boa[ 51] = ("Ls2",  17, 50, 33, "schwach sandiger Lehm")
        boa[ 52] = ("Ls3",  17, 40, 43, "mittel sandiger Lehm")
        boa[ 53] = ("Ls3",  25, 40, 35, "mittel sandiger Lehm")
        boa[ 54] = ("Ls3",  25, 30, 45, "mittel sandiger Lehm")
        boa[ 55] = ("Ls3",  17, 30, 53, "mittel sandiger Lehm")
        boa[ 56] = ("Ls4",  25, 15, 60, "stark sandiger Lehm")
        boa[ 57] = ("Ls4",  17, 15, 68, "stark sandiger Lehm")
        boa[ 58] = ("Ls4",  17, 30, 53, "stark sandiger Lehm")
        boa[ 59] = ("Ls4",  25, 30, 45, "stark sandiger Lehm")
        boa[ 60] = ("Lts",  45, 15, 40, "sandig-toniger Lehm")
        boa[ 61] = ("Lts",  35, 15, 50, "sandig-toniger Lehm")
        boa[ 62] = ("Lts",  25, 15, 60, "sandig-toniger Lehm")
        boa[ 63] = ("Lts",  25, 30, 45, "sandig-toniger Lehm")
        boa[ 64] = ("Lts",  35, 30, 35, "sandig-toniger Lehm")
        boa[ 65] = ("Lts",  45, 30, 25, "sandig-toniger Lehm")
        boa[ 66] = ("Ts4",  35,  0, 65, "stark sandiger Ton")
        boa[ 67] = ("Ts4",  25,  0, 75, "stark sandiger Ton")
        boa[ 68] = ("Ts4",  25, 15, 60, "stark sandiger Ton")
        boa[ 69] = ("Ts4",  35, 15, 50, "stark sandiger Ton")
        boa[ 70] = ("Ts3",  45, 15, 40, "mittel sandiger Ton")
        boa[ 71] = ("Ts3",  45,  0, 55, "mittel sandiger Ton")
        boa[ 72] = ("Ts3",  35,  0, 65, "mittel sandiger Ton")
        boa[ 73] = ("Ts3",  35, 15, 50, "mittel sandiger Ton")
        boa[ 74] = ("Uu",    0,100,  0, "Schluff")
        boa[ 75] = ("Uu",    8, 92,  0, "Schluff")
        boa[ 76] = ("Uu",    8, 80, 12, "Schluff")
        boa[ 77] = ("Uu",    0, 80, 20, "Schluff")
        boa[ 78] = ("Us",    0, 80, 20, "sandiger Schluff")
        boa[ 79] = ("Us",    8, 80, 12, "sandiger Schluff")
        boa[ 80] = ("Us",    8, 65, 27, "sandiger Schluff")
        boa[ 81] = ("Us",    8, 50, 42, "sandiger Schluff")
        boa[ 82] = ("Us",    0, 50, 50, "sandiger Schluff")
        boa[ 83] = ("Ut2",   8, 80, 12, "schwach toniger Schluff")
        boa[ 84] = ("Ut2",   8, 92,  0, "schwach toniger Schluff")
        boa[ 85] = ("Ut2",  12, 88,  0, "schwach toniger Schluff")
        boa[ 86] = ("Ut2",  12, 65, 23, "schwach toniger Schluff")
        boa[ 87] = ("Ut2",   8, 65, 27, "schwach toniger Schluff")
        boa[ 88] = ("Ut3",  12, 88,  0, "mittel toniger Schluff")
        boa[ 89] = ("Ut3",  17, 83,  0, "mittel toniger Schluff")
        boa[ 90] = ("Ut3",  17, 65, 18, "mittel toniger Schluff")
        boa[ 91] = ("Ut3",  12, 65, 23, "mittel toniger Schluff")
        boa[ 92] = ("Uls",  12, 65, 23, "sandig-lehmiger Schluff")
        boa[ 93] = ("Uls",  17, 65, 18, "sandig-lehmiger Schluff")
        boa[ 94] = ("Uls",  17, 50, 33, "sandig-lehmiger Schluff")
        boa[ 95] = ("Uls",   8, 50, 42, "sandig-lehmiger Schluff")
        boa[ 96] = ("Uls",   8, 65, 27, "sandig-lehmiger Schluff")
        boa[ 97] = ("Lu",   17, 65, 18, "schluffiger Lehm")
        boa[ 98] = ("Lu",   25, 65, 10, "schluffiger Lehm")
        boa[ 99] = ("Lu",   30, 65,  5, "schluffiger Lehm")
        boa[100] = ("Lu",   30, 50, 20, "schluffiger Lehm")
        boa[101] = ("Lu",   25, 50, 25, "schluffiger Lehm")
        boa[102] = ("Lu",   17, 50, 33, "schluffiger Lehm")
        boa[103] = ("Ut4",  17, 83,  0, "stark toniger Schluff")
        boa[104] = ("Ut4",  25, 75,  0, "stark toniger Schluff")
        boa[105] = ("Ut4",  25, 65, 10, "stark toniger Schluff")
        boa[106] = ("Ut4",  17, 65, 18, "stark toniger Schluff")
        boa[107] = ("Tu4",  25, 65, 10, "stark schluffiger Ton")
        boa[108] = ("Tu4",  25, 75,  0, "stark schluffiger Ton")
        boa[109] = ("Tu4",  35, 65,  0, "stark schluffiger Ton")
        boa[110] = ("Tu4",  30, 65,  5, "stark schluffiger Ton")
        boa[111] = ("Tu3",  30, 65,  5, "mittel schluffiger Ton")
        boa[112] = ("Tu3",  35, 65,  0, "mittel schluffiger Ton")
        boa[113] = ("Tu3",  45, 55,  0, "mittel schluffiger Ton")
        boa[114] = ("Tu3",  45, 50,  5, "mittel schluffiger Ton")
        boa[115] = ("Tu3",  35, 50, 15, "mittel schluffiger Ton")
        boa[116] = ("Tu3",  30, 50, 20, "mittel schluffiger Ton")
        boa[117] = ("Lt2",  35, 50, 15, "schwach toniger Lehm")
        boa[118] = ("Lt2",  35, 30, 35, "schwach toniger Lehm")
        boa[119] = ("Lt2",  25, 30, 45, "schwach toniger Lehm")
        boa[120] = ("Lt2",  25, 40, 35, "schwach toniger Lehm")
        boa[121] = ("Lt2",  25, 50, 25, "schwach toniger Lehm")
        boa[122] = ("Lt2",  30, 50, 20, "schwach toniger Lehm")
        boa[123] = ("Lt3",  45, 50,  5, "toniger Lehm")
        boa[124] = ("Lt3",  45, 30, 25, "toniger Lehm")
        boa[125] = ("Lt3",  35, 30, 35, "toniger Lehm")
        boa[126] = ("Lt3",  35, 50, 15, "toniger Lehm")
        boa[127] = ("Tu2",  45, 30, 25, "schwach schluffiger Ton")
        boa[128] = ("Tu2",  45, 50,  5, "schwach schluffiger Ton")
        boa[129] = ("Tu2",  45, 55,  0, "schwach schluffiger Ton")
        boa[130] = ("Tu2",  65, 35,  0, "schwach schluffiger Ton")
        boa[131] = ("Tu2",  65, 30,  5, "schwach schluffiger Ton")
        boa[132] = ("Tl",   65, 30,  5, "lehmiger Ton")
        boa[133] = ("Tl",   65, 15, 20, "lehmiger Ton")
        boa[134] = ("Tl",   45, 15, 40, "lehmiger Ton")
        boa[135] = ("Tl",   45, 30, 25, "lehmiger Ton")
        boa[136] = ("Ts2",  45, 15, 40, "schwach sandiger Ton")
        boa[137] = ("Ts2",  65, 15, 20, "schwach sandiger Ton")
        boa[138] = ("Ts2",  65,  0, 35, "schwach sandiger Ton")
        boa[139] = ("Ts2",  45,  0, 55, "schwach sandiger Ton")
        boa[140] = ("Tt",   65, 15, 20, "Ton")
        boa[141] = ("Tt",   65, 30,  5, "Ton")
        boa[142] = ("Tt",   65, 35,  0, "Ton")
        boa[143] = ("Tt",  100,  0,  0, "Ton")
        boa[144] = ("Tt",   65,  0, 35, "Ton")




        def add_single_band_numpy_array_to_qgis(numpy_array, geotransform, projection, layer_name):

            # Get dimensions
            rows, cols = numpy_array.shape
            print(f"Rows: {rows}, Cols: {cols}")  # Debugging output

            # Create an in-memory GDAL dataset with the correct dimensions
            driver = gdal.GetDriverByName('MEM')
            dataset = driver.Create('', cols, rows, 1, gdal.GDT_Float32)
            
            # Set geotransform and projection
            dataset.SetGeoTransform(geotransform)
            dataset.SetProjection(projection)
            
            # Write the numpy array data to the GDAL dataset
            band = dataset.GetRasterBand(1)
            band.WriteArray(numpy_array)
            
            nodata_value = -9999
            #numpy_array = np.where(np.isnan(numpy_array), nodata_value, numpy_array)
            band.SetNoDataValue(nodata_value)
        
            # Create a temporary file path (memory-based file)
            tmp_path = '/vsimem/' + layer_name

            # Save the dataset to this temporary path
            gdal.GetDriverByName('GTiff').CreateCopy(tmp_path, dataset)

            # Add the raster layer to the QGIS project from the in-memory path
            raster_layer = QgsRasterLayer(tmp_path, layer_name)
            
            if not raster_layer.isValid():
                print("Failed to create the layer!")
                return None
            
            QgsProject.instance().addMapLayer(raster_layer)
            print(f"Layer '{layer_name}' added to QGIS project successfully!")
            
            # Cleanup: remove the in-memory file
            #gdal.Unlink(tmp_path) - doesnt work correctly if deleted

            return raster_layer



        # globale Variablen
        polyX = []   # Polygon X-Werte
        polyY = []   # Polygon Y-Werte
        count = None # Anzahl Polygon-Koordinaten

        def pointInPoly(xt, yt):
            """
            Prüft, ob der Punkt xt / yt im Polygon polyY / polyY liegt
            """

            kreuz = 0

            xo = polyX[count]
            yo = polyY[count]
            
            for np in range(count + 1):

                xn = polyX[np]
                yn = polyY[np]
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

        #Loop over soil-layers
        for layer_name, data_array in layer_data.items():
            clay_array = data_array[0]
            silt_array = data_array[1]
            sand_array = data_array[2]
            
            if clay_array.shape != silt_array.shape or clay_array.shape != sand_array.shape or silt_array.shape != sand_array.shape:
                print("The input layers have different shapes.")
            
            cols, rows = clay_array.shape
            
            # initialize result array with nodata values
            nodata = -9999
            boa_array = np.full([cols, rows], nodata, dtype=int)
            print(boa_array)
            for x in range(cols):
                for y in range(rows):
                    sand = sand_array[x,y]
                    clay = clay_array[x,y]
                    silt = silt_array[x,y]
                
                    # skip cells where any component is NoData
                    if np.isnan(sand) or np.isnan(clay) or np.isnan(silt) or sand == nodata or clay == nodata or silt == nodata:
                        continue
                    
                    #Check that sum is 100%
                    sum = sand + clay + silt
                    if sum < 95.0 or sum > 102.0:
                        print(f"Zelle %i, %i: Summe der Anteile ist ungleich 100%%: %.2f%%! { (x, y, sum)}")
                    
                    # adjust to 100%
                    clay = clay + clay / sum * (100.0 - sum)
                    silt = silt + silt / sum * (100.0 - sum)
                    sand = sand + sand / sum * (100.0 - sum)

                    # Schleife über Bodenarten-Polygone
                    bda = boa[0][0]
                    polyX = [None]*30
                    polyY = [None]*30
                    count = -1;
                    for i in range(len(boa)):
                        if bda != boa[i][0]: #Check if this polygon is finished
                            if pointInPoly(clay, silt):
                                # found
                                break
                            count = 0
                            polyX[count] = boa[i][1]
                            polyY[count] = boa[i][2]
                            bda = boa[i][0]
                        else: #if still the same polygon
                            count += 1
                            polyX[count] = boa[i][1]
                            polyY[count] = boa[i][2]
                            
                    boa_array[x, y] = talsim_soilids[bda]

            # Assuming geotransform and projection are taken from the original dataset
            input_file_path = r'C:\Users\loren\Documents\Sydro\Daten_QTalsim\Bodendaten\Tests\proj\proj/clay_0-5cm_mean.tif'  # Replace with actual path
            original_dataset = gdal.Open(input_file_path)
            geotransform = original_dataset.GetGeoTransform()
            projection = original_dataset.GetProjection()

            # Add the clay layer array to QGIS
            add_single_band_numpy_array_to_qgis(boa_array, geotransform, projection, layer_name)
                     
    


        
        