import unittest
from io import StringIO
from contextlib import redirect_stdout
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.vastai.vast_display import display_vast_offers

class TestDisplayVastOffers(unittest.TestCase):

    def setUp(self):
        self.mock_config = {
            "columns": ["id", "gpu_name", "gpu_ram", "geolocation", "score"],
            "column_headers": {
                "id": "ID",
                "gpu_name": "GPU",
                "gpu_ram": "GPU RAM (GB)",
                "geolocation": "Location",
                "score": "Score"
            },
            "column_filters": {
                "geolocation": "*, CA",
                "gpu_ram": ">= 24576"
            },
            "max_rows": 5
        }

        self.mock_response = {
            "offers": [
                {
                    "id": 123,
                    "gpu_name": "RTX 3090",
                    "gpu_ram": 24576,
                    "geolocation": "Quebec, CA",
                    "score": 900.123
                },
                {
                    "id": 456,
                    "gpu_name": "RTX 3090",
                    "gpu_ram": 16384,
                    "geolocation": "Texas, US",
                    "score": 800.00
                },
                {
                    "id": 789,
                    "gpu_name": "RTX 4090",
                    "gpu_ram": 24576,
                    "geolocation": "Ontario, CA",
                    "score": 950.5
                }
            ]
        }

    def test_display_vast_offers_filtering(self):
        with StringIO() as buf, redirect_stdout(buf):
            display_vast_offers(self.mock_response, self.mock_config)
            output = buf.getvalue()

        self.assertIn("Quebec, CA", output)
        self.assertIn("Ontario, CA", output)
        self.assertNotIn("Texas, US", output)  # Should be filtered out
        self.assertIn("RTX 3090", output)
        self.assertIn("RTX 4090", output)

if __name__ == "__main__":
    unittest.main()
