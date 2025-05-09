# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'l.treitler@sydro.de'
__date__ = '2023-10-12'
__copyright__ = 'Copyright 2023, SYDRO Consult GmbH'

import os
import sys
import unittest
from qgis.PyQt.QtCore import QSettings
from unittest.mock import MagicMock

#from .utilities import get_qgis_app
#QGIS_APP = get_qgis_app()

from qgis.core import QgsApplication, QgsVectorLayer

qgs = QgsApplication([], False)
qgs.initQgis()
from qgis.analysis import QgsNativeAlgorithms 
import processing
from processing.core.Processing import Processing

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, plugin_dir)
from qtalsim_dialog import QTalsimDialog #QTalsim.?
from qtalsim import QTalsim

from test.utilities import get_qgis_app
QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

class QTalsimDialogTest(unittest.TestCase):
    """Test dialog works."""
    #@patch("qgis.PyQt.QtCore.QSettings")
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")

        self.app, self.canvas, self.iface, self.parent = get_qgis_app()
        self.plugin = QTalsim(self.iface)
        self.plugin.init_dialog()
        if not hasattr(self.plugin, "dlg"):
            raise RuntimeError("QTalsim.dlg is not initialized. Check if iface and plugin setup are correct.")
        self.dialog = self.plugin.dlg

        #self.plugin.performIntersect = MagicMock()

        #self.dialog.onPerformIntersect.clicked.connect(self.plugin.performIntersect)

        #Load test layers
        testdata_path = os.path.join(os.path.dirname(__file__), "testdata")
        self.plugin.landuseTalsim = self.load_test_layer(os.path.join(testdata_path, "testDataLanduseFinal.gpkg"))
        self.plugin.ezgLayer = self.load_test_layer(os.path.join(testdata_path, "testDataSubBasins.gpkg"))
        self.plugin.soilTalsim = self.load_test_layer(os.path.join(testdata_path, "testDataSoilFinal.gpkg"))

        #Parameters for intersect
        self.ezgUniqueIdentifier = 'id'
        self.plugin.ezgUniqueIdentifier = self.ezgUniqueIdentifier
        self.plugin.selected_landuse_parameters = ["Talsim Landuse", "RootDepth", "PlantCoverage", "LeafAreaIndex"]
        self.fieldLanduseID = "ID_LNZ"
        self.plugin.soilFieldNames = ["NameSoil"]
        self.soilIDNames = ["ID_Soil"]

    def load_test_layer(self, path: str) -> QgsVectorLayer:
        layer = QgsVectorLayer(path, os.path.basename(path), "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Failed to load layer from {path}")
        return layer

    def test_ezg(self):
        self.plugin.ezgLayerCombobox = self.plugin.ezgLayer

        self.plugin.dlg.comboboxUICatchment.addItem(self.ezgUniqueIdentifier)
        self.plugin.dlg.comboboxUICatchment.setCurrentText(self.ezgUniqueIdentifier)
        self.plugin.selectEZG()
    '''
    def test_intersect(self):
        """Test that performIntersect creates self.eflLayer correctly."""
        self.plugin.performIntersect()
        efl = self.plugin.eflLayer

        self.assertIsNotNone(efl, "eflLayer should not be None")
        self.assertTrue(efl.isValid(), "eflLayer should be valid")
        self.assertGreater(efl.featureCount(), 0, "eflLayer should have features")
    '''
    def tearDown(self):
        """Runs after each test."""
        self.plugin = None
        self.dialog = None

    '''
    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.Ok)
        if button:  
            button.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.Accepted)
    '''
    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.finalButtonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if button:  
            button.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.DialogCode.Rejected)

    def test_layers_loaded(self):
        """Simple test that layers are valid and loaded."""
        self.assertTrue(self.plugin.landuseTalsim.isValid())
        self.assertTrue(self.plugin.ezgLayer.isValid())
        self.assertTrue(self.plugin.soilTalsim.isValid())

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(QTalsimDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

qgs.exitQgis()


