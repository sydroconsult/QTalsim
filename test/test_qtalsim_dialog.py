import os
import sys
import unittest
from PyQt5.QtCore import QSettings
from qgis.core import QgsApplication
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qtalsim_subbasin_dialog import SubBasinPreprocessingDialog
from qtalsim_landuse_dialog import LanduseAssignmentDialog
from qtalsim_soil_dialog import SoilPreprocessingDialog
from qtalsim_sqllite_dialog import SQLConnectDialog

# Initialize QGIS (once)
qgs = QgsApplication([], False)
qgs.initQgis()
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Plugin paths
plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, plugin_dir)

from qtalsim import QTalsim
from test.utilities import get_qgis_app

class QTalsimDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()

        self.plugin = QTalsim(self.iface)
        self.plugin.init_dialog()
        self.dialog = self.plugin.dlg

    def test_dialog_cancel(self):
        """Test that the Cancel button works."""
        cancel_btn = self.dialog.finalButtonBox.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.Rejected)

    def tearDown(self):
        self.plugin = None
        self.dialog = None

class SubBasinPreprocessingDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()
        
        # Initialize the SubBasin dialog
        self.plugin = QTalsim(self.iface)
        self.dialog = SubBasinPreprocessingDialog(self.iface, self.plugin, self.parent)

    def test_initialization(self):
        """Test if SubBasinPreprocessingDialog initializes correctly."""
        try:
            self.assertIsNotNone(self.dialog)
            print("SUCCESS: SubBasinPreprocessingDialog initialized successfully")
        except Exception as e:
            self.fail(f"SubBasinPreprocessingDialog initialization failed with an exception: {e}")

    def test_dialog_cancel(self):
        """Test that the Cancel button works in SubBasinPreprocessingDialog."""
        # Look for cancel button - adjust based on your dialog's actual button setup
        cancel_btn = self.dialog.finalButtonBox.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.Rejected)
            print("SUCCESS: SubBasinPreprocessingDialog cancel button works")

    def tearDown(self):
        self.dialog = None
        self.plugin = None

class LanduseAssignmentDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()
        
        # Initialize the SubBasin dialog
        self.plugin = QTalsim(self.iface)
        self.dialog = LanduseAssignmentDialog(self.iface, self.plugin, self.parent)

    def test_initialization(self):
        """Test if LanduseAssignmentDialog initializes correctly."""
        try:
            self.assertIsNotNone(self.dialog)
            print("SUCCESS: LanduseAssignmentDialog initialized successfully")
        except Exception as e:
            self.fail(f"LanduseAssignmentDialog initialization failed with an exception: {e}")

    def tearDown(self):
        self.dialog = None
        self.plugin = None

class SoilPreprocessingDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()
        
        # Initialize the SubBasin dialog
        self.plugin = QTalsim(self.iface)
        self.dialog = SoilPreprocessingDialog(self.iface, self.plugin, self.parent)

    def test_initialization(self):
        """Test if SoilPreprocessingDialog initializes correctly."""
        try:
            self.assertIsNotNone(self.dialog)
            print("SUCCESS: SoilPreprocessingDialog initialized successfully")
        except Exception as e:
            self.fail(f"SoilPreprocessingDialog initialization failed with an exception: {e}")

    def tearDown(self):
        self.dialog = None
        self.plugin = None

class SQLConnectDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()
        
        # Initialize the SubBasin dialog
        self.plugin = QTalsim(self.iface)
        self.dialog = SQLConnectDialog(self.iface, self.plugin, self.parent)

    def test_initialization(self):
        """Test if SQLConnectDialog initializes correctly."""
        try:
            self.assertIsNotNone(self.dialog)
            print("SUCCESS: SQLConnectDialog initialized successfully")
        except Exception as e:
            self.fail(f"SQLConnectDialog initialization failed with an exception: {e}")

    def tearDown(self):
        self.dialog = None
        self.plugin = None
        
if __name__ == "__main__":
    unittest.main(verbosity=2)

qgs.exitQgis()