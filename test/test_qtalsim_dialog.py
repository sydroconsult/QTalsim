import os
import sys
import unittest
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsApplication
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
import pandas as pd


# Initialize QGIS (once)
qgs = QgsApplication([], False)
qgs.initQgis()
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Plugin paths
plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, plugin_dir)

from QTalsim.qtalsim import QTalsim #remove QTalsim. for local testing
from test.utilities import get_qgis_app
from QTalsim.qtalsim_subbasin_dialog import SubBasinPreprocessingDialog
from QTalsim.qtalsim_landuse_dialog import LanduseAssignmentDialog
from QTalsim.qtalsim_soil_dialog import SoilPreprocessingDialog
from QTalsim.qtalsim_sqllite_dialog import SQLConnectDialog

class QTalsimDialogTest(unittest.TestCase):
    def setUp(self):
        QSettings().setValue("locale/userLocale", "en_US")
        self.app, self.canvas, self.iface, self.parent = get_qgis_app()

        self.plugin = QTalsim(self.iface)
        self.plugin.init_dialog()
        self.dialog = self.plugin.dlg

    def test_dialog_cancel(self):
        """Test that the Cancel button works."""
        cancel_btn = self.dialog.finalButtonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.DialogCode.Rejected)

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
        cancel_btn = self.dialog.finalButtonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.click()
            result = self.dialog.result()
            self.assertEqual(result, QDialog.DialogCode.Rejected)
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

    def test_resample_checkbox_toggle(self):
        """Test that toggling the ESA WorldCover resample checkbox enables/disables the resolution spinbox."""
        self.dialog.checkboxResample.setChecked(True)
        self.assertTrue(self.dialog.spinboxResample.isEnabled())
        self.dialog.checkboxResample.setChecked(False)
        self.assertFalse(self.dialog.spinboxResample.isEnabled())

    def tearDown(self):
        self.dialog = None
        self.plugin = None

class LanduseParameterDataTest(unittest.TestCase):
    """Tests for the German/English land use name mapping added to talsim_parameter CSVs."""

    @classmethod
    def setUpClass(cls):
        param_dir = os.path.join(plugin_dir, "QTalsim", "talsim_parameter")
        cls.df_landuse_values = pd.read_csv(
            os.path.join(param_dir, "landuseParameterValues.csv"), delimiter=";", decimal=","
        )
        cls.df_esa_mapping = pd.read_csv(
            os.path.join(param_dir, "esa_talsim_zuordnung.csv"), delimiter=";"
        )

    def test_name_en_column_present_and_populated(self):
        """landuseParameterValues.csv must have a fully populated Name_en column."""
        self.assertIn("Name_en", self.df_landuse_values.columns)
        self.assertFalse(self.df_landuse_values["Name_en"].isna().any())

    def test_esa_mapping_names_resolve_in_both_languages(self):
        """Every German/English Talsim land use name referenced by the ESA mapping
        table must exist in landuseParameterValues.csv, so the HRU calculation's
        name-based parameter join succeeds regardless of which language the input
        land use layer uses."""
        names_de = self.df_landuse_values["Name"].str.strip().str.lower()
        names_en = self.df_landuse_values["Name_en"].str.strip().str.lower()

        for _, row in self.df_esa_mapping.iterrows():
            talsim_de = str(row["Talsim Landuse"]).strip().lower()
            talsim_en = str(row["Talsim Landuse (english)"]).strip().lower()

            self.assertIn(
                talsim_de, names_de.values,
                f"German name '{talsim_de}' from ESA mapping not found in landuseParameterValues.csv",
            )
            self.assertIn(
                talsim_en, names_en.values,
                f"English name '{talsim_en}' from ESA mapping not found in landuseParameterValues.csv",
            )

    def test_name_matching_is_case_and_whitespace_insensitive(self):
        """Reproduces the join logic in QTalsim.confirmLanduseMapping: an input land
        use name must match a Talsim parameter row regardless of case/whitespace,
        in either German (Name) or English (Name_en)."""
        input_norm = "  CROPLAND  ".strip().lower()
        mask_de = self.df_landuse_values["Name"].str.strip().str.lower() == input_norm
        mask_en = self.df_landuse_values["Name_en"].str.strip().str.lower() == input_norm
        mask = mask_de | mask_en
        self.assertTrue(mask.any())
        self.assertEqual(self.df_landuse_values.loc[mask, "Name"].iloc[0], "Ackerland")

    def test_new_dict_lookup_matches_old_mask_lookup(self):
        """Regression test for the confirmLanduseMapping performance fix
        (QTalsim.qtalsim.py): the precomputed name->row-index dict lookup
        must return exactly the same row as the original per-call
        mask_de | mask_en approach, for every name in the table plus some
        edge cases (whitespace/case variants, an unknown name)."""
        df = self.df_landuse_values
        name_norm = df["Name"].str.strip().str.lower()
        name_en_norm = df["Name_en"].str.strip().str.lower()

        name_to_row_index = {}
        for idx, name, name_en in zip(df.index, name_norm, name_en_norm):
            name_to_row_index.setdefault(name, idx)
            name_to_row_index.setdefault(name_en, idx)

        test_inputs = list(df["Name"]) + list(df["Name_en"]) + [
            "  Ackerland  ", "CROPLAND", "NonexistentLandUse",
        ]

        for raw_input in test_inputs:
            input_norm = str(raw_input).strip().lower()

            mask = (name_norm == input_norm) | (name_en_norm == input_norm)
            old_result = df.loc[mask, "RootDepth"].iloc[0] if mask.any() else None

            row_idx = name_to_row_index.get(input_norm)
            new_result = df.at[row_idx, "RootDepth"] if row_idx is not None else None

            self.assertEqual(
                old_result, new_result,
                f"Dict lookup diverged from mask lookup for input '{raw_input}'",
            )

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