import unittest
from unittest.mock import MagicMock
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from qtalsim import QTalsim #QTalsim.qtalsim import QTalsim
from qtalsim_subbasin_dialog import SubBasinPreprocessingDialog
sys.path.remove(parent_dir)
import tempfile
import shutil

class TestQTalsim(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_initialization(self):
        """Test if QTalsim initializes correctly."""
        try:
            plugin = QTalsim()
            self.assertIsNotNone(plugin)
            logger.info("SUCCESS: QTalsim - HRU calculation initialized successfully")
        except Exception as e:
            self.fail(f"QTalsim - HRU calculation initialization failed with an exception: {e}")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

class TestSubBasinPreprocessingDialog(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_initialization(self):
        """Test if SubBasinPreprocessingDialog initializes correctly."""
        try:
            dialog = SubBasinPreprocessingDialog()
            self.assertIsNotNone(dialog)
            logger.info("✓ SubBasinPreprocessingDialog initialized successfully")
        except Exception as e:
            self.fail(f"SubBasinPreprocessingDialog initialization failed with an exception: {e}")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

if __name__ == '__main__':
    unittest.main()