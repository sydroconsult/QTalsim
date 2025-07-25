import os
import sys
import unittest
from PyQt5.QtCore import QSettings
from qgis.core import QgsApplication
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

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

if __name__ == "__main__":
    unittest.main(verbosity=2)

qgs.exitQgis()