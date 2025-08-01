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

    @patch('modapi.output.ModbusClient')
    @patch('modapi.output.auto_detect_modbus_port')
    @patch('flask.Flask')
    def test_create_output_app(self, mock_flask, mock_auto_detect, mock_modbus_client):
        """Test output app creation"""
        # Set up mocks
        mock_app = MagicMock()
        mock_flask.return_value = mock_app
        mock_auto_detect.return_value = '/dev/ttyUSB0'
        
        # Mock ModbusClient instance
        mock_client_instance = MagicMock()
        mock_modbus_client.return_value = mock_client_instance
        
        # Test app creation
        app = create_output_app(debug=True)
        self.assertIsNotNone(app)
        
        # Verify Flask app was created
        mock_flask.assert_called_once_with(__name__)
        
        # Verify route was added with expected path
        mock_app.route.assert_any_call('/module/output/<int:channel>')
        
        # Verify before_request and after_request handlers were added
        mock_app.before_request.assert_called_once()
        mock_app.after_request.assert_called_once()


if __name__ == '__main__':
    unittest.main()
