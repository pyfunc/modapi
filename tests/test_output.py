"""
Tests for modapi.output module
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import sys
import os

# Add parent directory to path to import modapi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.output import parse_coil_status, parse_coil_output, generate_svg, create_output_app


class TestOutputModule(unittest.TestCase):
    """Test cases for output module"""

    def test_parse_coil_status_valid(self):
        """Test parsing valid coil status messages"""
        # Test ON status
        addr, status = parse_coil_status("Coil 0 set to ON")
        self.assertEqual(addr, 0)
        self.assertTrue(status)
        
        # Test OFF status
        addr, status = parse_coil_status("Coil 5 set to OFF")
        self.assertEqual(addr, 5)
        self.assertFalse(status)
        
        # Test case insensitivity
        addr, status = parse_coil_status("coil 2 SET to on")
        self.assertEqual(addr, 2)
        self.assertTrue(status)

    def test_parse_coil_status_invalid(self):
        """Test parsing invalid coil status messages"""
        # Test invalid formats
        self.assertEqual(parse_coil_status("Invalid message"), (None, None))
        self.assertEqual(parse_coil_status("Coil X set to ON"), (None, None))
        self.assertEqual(parse_coil_status(""), (None, None))
        self.assertEqual(parse_coil_status(None), (None, None))

    def test_parse_coil_output_json(self):
        """Test parsing coil output from JSON format"""
        # Test valid JSON with values
        json_str = '{"data": {"values": [false, true, false]}}'
        self.assertFalse(parse_coil_output(json_str, 0))
        self.assertTrue(parse_coil_output(json_str, 1))
        self.assertFalse(parse_coil_output(json_str, 2))
        
        # Test invalid JSON
        self.assertIsNone(parse_coil_output('{"invalid": "json"', 0))

    def test_parse_coil_output_status_message(self):
        """Test parsing coil output from status message format"""
        # Test valid status message
        self.assertTrue(parse_coil_output("Coil 1 set to ON", 1))
        self.assertFalse(parse_coil_output("Coil 3 set to OFF", 3))
        
        # Test with non-matching channel
        self.assertIsNone(parse_coil_output("Coil 1 set to ON", 2))

    def test_parse_coil_output_list(self):
        """Test parsing coil output from list format"""
        # Test list format
        self.assertTrue(parse_coil_output("[False, True, False]", 1))
        self.assertFalse(parse_coil_output("[False, True, False]", 0))
        
        # Test with spaces
        self.assertTrue(parse_coil_output("[ False,  True,  False ]", 1))
        
        # Test with newlines
        self.assertTrue(parse_coil_output("\n[\nFalse,\nTrue,\nFalse\n]\n", 1))

    def test_generate_svg(self):
        """Test SVG generation"""
        # Test with default config
        svg = generate_svg(0, True)
        self.assertIn("<svg", svg)
        self.assertIn("output-active", svg)
        
        # Test with custom config
        config = {
            'ui': {'theme': 'light'},
            'widget': {'name': 'CustomName'}
        }
        svg = generate_svg(1, False, config)
        self.assertIn("CustomName", svg)
        self.assertIn("output-inactive", svg)

    def test_create_output_app(self):
        """Test output app creation"""
        # Test app creation with debug mode
        app = create_output_app(debug=True)
        
        # Verify the app is a Flask app
        self.assertIsNotNone(app)
        self.assertEqual(app.name, 'modapi.output')
        
        # Verify the route is registered
        url_rules = list(app.url_map.iter_rules())
        self.assertTrue(any(rule.rule == '/module/output/<int:channel>' for rule in url_rules))


if __name__ == '__main__':
    unittest.main()
