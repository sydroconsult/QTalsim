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

import unittest

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, parent_dir)

from QTalsim.qtalsim_dialog import QTalsimDialog
sys.path.remove(parent_dir)

from .utilities import get_qgis_app
QGIS_APP = get_qgis_app()


class QTalsimDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = QTalsimDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Rejected)

if __name__ == "__main__":
    suite = unittest.makeSuite(QTalsimDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

