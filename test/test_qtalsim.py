import unittest
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from qtalsim import QTalsim #QTalsim.qtalsim import QTalsim
sys.path.remove(parent_dir)
import tempfile
import shutil

class TestQTalsim(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_initialization(self):
        """Test if QtalSim initializes correctly."""
        try:
            plugin = QTalsim()
            self.assertIsNotNone(plugin)
        except Exception as e:
            self.fail(f"Initialization failed with an exception: {e}")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
if __name__ == '__main__':
    unittest.main()