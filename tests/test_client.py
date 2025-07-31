"""
Tests for modapi.client module
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent directory to path to import modapi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.client import ModbusClient, auto_detect_modbus_port


class TestModbusClient(unittest.TestCase):
    """Test cases for ModbusClient class"""

    @patch('modapi.client.ModbusSerialClient')
    def setUp(self, mock_serial_client):
        """Set up test fixtures"""
        self.mock_serial = mock_serial_client.return_value
        self.mock_serial.connect.return_value = True
        self.client = ModbusClient(port='/dev/ttyUSB0', baudrate=9600)

    def test_init(self):
        """Test initialization of ModbusClient"""
        self.assertEqual(self.client.port, '/dev/ttyUSB0')
        self.assertEqual(self.client.baudrate, 9600)
        self.assertEqual(self.client.timeout, 1.0)
        self.assertEqual(self.client.unit, 1)

    def test_connect(self):
        """Test connect method"""
        result = self.client.connect()
        self.assertTrue(result)
        self.mock_serial.connect.assert_called_once()

    def test_close(self):
        """Test close method"""
        self.client.close()
        self.mock_serial.close.assert_called_once()

    @patch('modapi.client.ModbusSerialClient')
    def test_read_coils(self, mock_serial_client):
        """Test read_coils method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_response.bits = [True, False, True]
        mock_client.read_coils.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.read_coils(0, 3)

        # Verify
        self.assertEqual(result, [True, False, True])
        mock_client.read_coils.assert_called_with(0, 3, unit=1)

    @patch('modapi.client.ModbusSerialClient')
    def test_read_coils_error(self, mock_serial_client):
        """Test read_coils method with error response"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = True
        mock_client.read_coils.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.read_coils(0, 3)

        # Verify
        self.assertIsNone(result)

    @patch('modapi.client.ModbusSerialClient')
    def test_write_coil(self, mock_serial_client):
        """Test write_coil method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_client.write_coil.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.write_coil(0, True)

        # Verify
        self.assertTrue(result)
        mock_client.write_coil.assert_called_with(0, True, unit=1)

    @patch('modapi.client.ModbusSerialClient')
    def test_write_coil_error(self, mock_serial_client):
        """Test write_coil method with error response"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = True
        mock_client.write_coil.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.write_coil(0, True)

        # Verify
        self.assertFalse(result)

    @patch('modapi.client.ModbusSerialClient')
    def test_read_discrete_inputs(self, mock_serial_client):
        """Test read_discrete_inputs method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_response.bits = [True, False]
        mock_client.read_discrete_inputs.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.read_discrete_inputs(0, 2)

        # Verify
        self.assertEqual(result, [True, False])
        mock_client.read_discrete_inputs.assert_called_with(0, 2, unit=1)

    @patch('modapi.client.ModbusSerialClient')
    def test_read_holding_registers(self, mock_serial_client):
        """Test read_holding_registers method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_response.registers = [123, 456]
        mock_client.read_holding_registers.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.read_holding_registers(0, 2)

        # Verify
        self.assertEqual(result, [123, 456])
        mock_client.read_holding_registers.assert_called_with(0, 2, unit=1)

    @patch('modapi.client.ModbusSerialClient')
    def test_write_register(self, mock_serial_client):
        """Test write_register method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_client.write_register.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.write_register(0, 123)

        # Verify
        self.assertTrue(result)
        mock_client.write_register.assert_called_with(0, 123, unit=1)

    @patch('modapi.client.ModbusSerialClient')
    def test_read_input_registers(self, mock_serial_client):
        """Test read_input_registers method"""
        # Setup mock
        mock_client = mock_serial_client.return_value
        mock_client.connect.return_value = True
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_response.registers = [789, 101]
        mock_client.read_input_registers.return_value = mock_response

        # Create client and test
        client = ModbusClient(port='/dev/ttyUSB0')
        result = client.read_input_registers(0, 2)

        # Verify
        self.assertEqual(result, [789, 101])
        mock_client.read_input_registers.assert_called_with(0, 2, unit=1)

    @patch('serial.tools.list_ports.comports')
    def test_auto_detect_modbus_port(self, mock_comports):
        """Test auto_detect_modbus_port function"""
        # Setup mock ports
        mock_port1 = MagicMock()
        mock_port1.device = '/dev/ttyUSB0'
        mock_port1.description = 'USB Serial'
        
        mock_port2 = MagicMock()
        mock_port2.device = '/dev/ttyACM0'
        mock_port2.description = 'Arduino Uno'
        
        mock_comports.return_value = [mock_port1, mock_port2]
        
        # Test with default patterns
        port = auto_detect_modbus_port()
        self.assertEqual(port, '/dev/ttyUSB0')
        
        # Test with custom pattern
        port = auto_detect_modbus_port(patterns=['Arduino'])
        self.assertEqual(port, '/dev/ttyACM0')
        
        # Test with no matches
        mock_comports.return_value = []
        port = auto_detect_modbus_port()
        self.assertIsNone(port)


if __name__ == '__main__':
    unittest.main()
