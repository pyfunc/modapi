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

    def setUp(self):
        # Create a mock for ModbusSerialClient
        self.mock_serial = MagicMock()
        self.mock_serial.connect.return_value = True
        
        # Create a mock response
        self.mock_response = MagicMock()
        self.mock_response.isError = False
        self.mock_response.bits = [False, True]
        self.mock_response.registers = [0, 1]
        
        # Create the client with the mock
        self.client = ModbusClient(
            port='/dev/ttyUSB0', 
            baudrate=9600,
            mock_client=self.mock_serial  # Inject the mock client directly
        )
        
        # Set the client attribute directly to ensure our mock is used
        self.client.client = self.mock_serial

    def test_init(self):
        """Test initialization of ModbusClient"""
        self.assertEqual(self.client.port, '/dev/ttyUSB0')
        self.assertEqual(self.client.baudrate, 9600)
        self.assertEqual(self.client.timeout, 1.0)
        self.assertEqual(self.client.unit, 1)

    def test_connect(self):
        """Test connect method"""
        # Configure the mock to return True on connect
        self.mock_serial.connect.return_value = True
        
        # Reset the mock to clear any previous calls
        self.mock_serial.connect.reset_mock()
        
        # Call the method
        result = self.client.connect()
        
        # Verify
        self.assertTrue(result)
        self.mock_serial.connect.assert_called_once()
        self.assertTrue(self.client.is_connected())

    def test_close(self):
        """Test close method"""
        # First connect to set up the client
        self.mock_serial.connect.return_value = True
        self.client.connect()
        
        # Reset the mock to clear any previous calls
        self.mock_serial.close.reset_mock()
        
        # Now test close
        self.client.close()
        self.mock_serial.close.assert_called_once()
        self.assertFalse(self.client.is_connected())

    def test_read_coils(self):
        """Test read_coils method"""
        # Setup mock response
        self.mock_serial.read_coils.return_value = self.mock_response
        self.mock_response.bits = [True, False]
        
        # Make sure the client is connected
        self.client.client = self.mock_serial
        self.client.is_connected = lambda: True
        
        # Test the method
        result = self.client.read_coils(0, 2)
        
        # Verify
        self.assertEqual(result, [True, False])
        self.mock_serial.read_coils.assert_called_once_with(0, 2, unit=1)

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

    def test_read_discrete_inputs(self):
        """Test read_discrete_inputs method"""
        # Setup mock response
        self.mock_serial.read_discrete_inputs.return_value = self.mock_response
        self.mock_response.bits = [True, False]
        
        # Make sure the client is connected
        self.client.client = self.mock_serial
        self.client.is_connected = lambda: True
        
        # Test the method
        result = self.client.read_discrete_inputs(0, 2)
        
        # Verify
        self.assertEqual(result, [True, False])
        self.mock_serial.read_discrete_inputs.assert_called_once_with(0, 2, unit=1)

    def test_read_holding_registers(self):
        """Test read_holding_registers method"""
        # Setup mock response
        self.mock_serial.read_holding_registers.return_value = self.mock_response
        self.mock_response.registers = [123, 456]
        
        # Make sure the client is connected
        self.client.client = self.mock_serial
        self.client.is_connected = lambda: True
        
        # Test the method
        result = self.client.read_holding_registers(0, 2)
        
        # Verify
        self.assertEqual(result, [123, 456])
        self.mock_serial.read_holding_registers.assert_called_once_with(0, 2, unit=1)

    def test_write_register(self):
        """Test write_register method"""
        # Setup mock response
        self.mock_serial.write_register.return_value = self.mock_response

        # Test the method
        result = self.client.write_register(0, 123)

        # Verify
        self.assertTrue(result)
        self.mock_serial.write_register.assert_called_once_with(0, 123, unit=1)

    def test_read_input_registers(self):
        """Test read_input_registers method"""
        # Setup mock response
        self.mock_serial.read_input_registers.return_value = self.mock_response
        self.mock_response.registers = [789, 101]
        
        # Make sure the client is connected
        self.client.client = self.mock_serial
        self.client.is_connected = lambda: True
        
        # Test the method
        result = self.client.read_input_registers(0, 2)
        
        # Verify
        self.assertEqual(result, [789, 101])
        self.mock_serial.read_input_registers.assert_called_once_with(0, 2, unit=1)

    @patch('modapi.client.test_modbus_port')
    @patch('modapi.client.find_serial_ports')
    @patch('serial.tools.list_ports.comports')
    def test_auto_detect_modbus_port(self, mock_comports, mock_find_ports, mock_test_port):
        """Test auto_detect_modbus_port function"""
        # Setup mock ports
        mock_port1 = MagicMock()
        mock_port1.device = '/dev/ttyUSB0'
        mock_port1.description = 'USB Serial'

        mock_port2 = MagicMock()
        mock_port2.device = '/dev/ttyACM0'
        mock_port2.description = 'Arduino Uno'

        # Configure mocks
        mock_comports.return_value = [mock_port1, mock_port2]
        mock_find_ports.return_value = ['/dev/ttyUSB0', '/dev/ttyACM0']
        
        # Configure test_modbus_port to only return True for ttyUSB0
        def test_port_side_effect(port, baudrate=9600, timeout=0.5):
            return port == '/dev/ttyUSB0'
        
        mock_test_port.side_effect = test_port_side_effect

        # Test with default patterns
        port = auto_detect_modbus_port()
        self.assertEqual(port, '/dev/ttyUSB0')
        
        # Verify test_modbus_port was called with correct parameters
        mock_test_port.assert_called_with('/dev/ttyACM0', baudrate=9600, timeout=0.5)
        
        # Test with custom pattern
        port = auto_detect_modbus_port(patterns=['Arduino'])
        self.assertEqual(port, '/dev/ttyACM0')
        
        # Test with no matches
        mock_comports.return_value = []
        port = auto_detect_modbus_port()
        self.assertIsNone(port)


if __name__ == '__main__':
    unittest.main()
