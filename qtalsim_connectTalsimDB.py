from .qtalsim_sqllite_dialog import Ui_Dialog
import os.path
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QgsProcessingFeedback
from qgis.PyQt.QtGui import QIcon, QCursor, QMovie
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem, QComboBox, QFileDialog, QInputDialog
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QAction
class ConnectToDB:
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QTalsim_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Talsim DB')
        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads

        self.first_start = None
        self.initialize_parameters()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&QTalsim'),
                action)
            self.iface.removeToolBarIcon(action)


    class CustomFeedback(QgsProcessingFeedback):
        def __init__(self, log_function):
            super().__init__()
            self.log_function = log_function

        def setProgress(self, progress):
            pass
            #self.log_function(f"Progress: {progress}%", Qgis.Info)

        def pushInfo(self, info):
            self.log_function(f"Info: {info}", Qgis.Info)
        
        def pushWarning(self, warning):
            self.log_function(f"Warning: {warning}", Qgis.Warning)
        
        def reportError(self, error, fatalError=False):
            level = Qgis.Critical if fatalError else Qgis.Warning
            self.log_function(f"Error: {error}", level)

    def run(self):
        '''
            Run method that performs all the real work.
        '''
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = Ui_Dialog()
        self.dlg.show()