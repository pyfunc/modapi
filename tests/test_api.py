"""
Tests for modapi.api modules
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import flask

# Add parent directory to path to import modapi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.api import create_rest_app, start_mqtt_broker
from modapi.api.rest import create_rest_app
from modapi.api.mqtt import start_mqtt_broker
from modapi.api.cmd import execute_command
from modapi.api.shell import interactive_mode
from modapi.rtu import ModbusRTU
from modapi.api.tcp import ModbusTCP


class TestRestApi(unittest.TestCase):
    """Test cases for REST API"""

    def setUp(self):
        """Set up test fixtures"""
        # Create patchers for both ModbusRTU and ModbusConnectionPool
        self.mock_rtu_patcher = patch('modapi.api.rest.ModbusRTU')
        self.mock_pool_patcher = patch('modapi.api.rest.ModbusConnectionPool')
        
        # Start the patchers
        self.mock_client_class = self.mock_rtu_patcher.start()
        self.mock_pool_class = self.mock_pool_patcher.start()
        
        # Set up mock client with required behavior
        self.mock_client = self.mock_client_class.return_value
        self.mock_client.is_connected.return_value = True
        self.mock_client.port = '/dev/ttyUSB0'
        self.mock_client.connect.return_value = True
        
        # Set up mock connection pool
        self.mock_pool = self.mock_pool_class.return_value
        self.mock_pool.get_connection.return_value = self.mock_client
        
        # Create Flask app with mocked client and pool
        self.app = create_rest_app(port='/dev/ttyUSB0')
        self.client = self.app.test_client()
        
    def tearDown(self):
        """Tear down test fixtures"""
        self.mock_rtu_patcher.stop()
        self.mock_pool_patcher.stop()

    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        self.mock_client.is_connected.return_value = True
        # Set port property on mock to match expected value
        self.mock_client.port = '/dev/ttyUSB0'
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'connected')
        self.assertEqual(data['port'], '/dev/ttyUSB0')

    def test_read_coil_endpoint(self):
        """Test /api/coils/<address> endpoint"""
        self.mock_client.read_coils.return_value = [True]
        response = self.client.get('/api/coils/0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Update assertion to match actual response format
        self.assertEqual(data['value'], True)

    def test_read_coils_endpoint(self):
        """Test /api/coils/<address>/<count> endpoint"""
        self.mock_client.read_coils.return_value = [True, False, True]
        response = self.client.get('/api/coils/0/3')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['values'], [True, False, True])

    def test_write_coil_endpoint(self):
        """Test PUT /api/coils/<address> endpoint"""
        self.mock_client.write_coil.return_value = True
        response = self.client.put('/api/coils/0', json={'value': True})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Update assertion to match actual response format
        self.assertTrue(data['success'])

    def test_read_discrete_inputs_endpoint(self):
        """Test /api/discrete_inputs/<address>/<count> endpoint"""
        self.mock_client.read_discrete_inputs.return_value = [True, False, True]
        response = self.client.get('/api/discrete_inputs/0/3')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['values'], [True, False, True])

    def test_read_holding_registers_endpoint(self):
        """Test /api/holding_registers/<address>/<count> endpoint"""
        self.mock_client.read_holding_registers.return_value = [1, 2, 3]
        response = self.client.get('/api/holding_registers/0/3')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['values'], [1, 2, 3])

    def test_write_holding_register_endpoint(self):
        """Test PUT /api/holding_registers/<address> endpoint"""
        self.mock_client.write_register.return_value = True
        response = self.client.put('/api/holding_registers/0', json={'value': 42})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['value'], 42)
        self.assertEqual(data['success'], True)

    def test_read_input_registers_endpoint(self):
        """Test /api/input_registers/<address>/<count> endpoint"""
        self.mock_client.read_input_registers.return_value = [1, 2, 3]
        response = self.client.get('/api/input_registers/0/3')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['values'], [1, 2, 3])

    def test_error_handling(self):
        """Test error handling"""
        self.mock_client.read_coils.return_value = None
        response = self.client.get('/api/coils/0')
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Failed to read coil')


class TestMqttApi(unittest.TestCase):
    """Test cases for MQTT API"""

    @patch('modapi.api.mqtt.mqtt.Client')
    @patch('modapi.api.mqtt.ModbusRTU')
    def test_start_mqtt_broker(self, mock_modbus_client, mock_mqtt_client):
        """Test start_mqtt_broker function"""
        # Mock the mqtt client
        mock_client = MagicMock()
        mock_mqtt_client.return_value = mock_client
        
        # Mock the modbus client
        mock_modbus = MagicMock()
        mock_modbus_client.return_value = mock_modbus
        mock_modbus.is_connected.return_value = True
        
        # Patch time.sleep to avoid blocking
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            try:
                start_mqtt_broker(port='/dev/ttyUSB0', broker='localhost')
            except KeyboardInterrupt:
                pass
        
        # Check that the MQTT client was created and connected
        mock_mqtt_client.assert_called_once()
        mock_client.connect.assert_called_once_with('localhost', 1883, 60)
        mock_client.loop_start.assert_called_once()
        mock_client.loop_stop.assert_called_once()
        
        # Check that the Modbus client was created
        mock_modbus_client.assert_called_once_with(port='/dev/ttyUSB0', baudrate=None, timeout=None)


class TestCmdApi(unittest.TestCase):
    """Test cases for Command API"""
    
    @patch('modapi.api.cmd.ModbusRTU')
    def test_execute_command_wc(self, mock_client_class):
        """Test execute_command with write_coil command"""
        # Mock the modbus client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_client.write_coil.return_value = True
        
        # Execute command
        success, response = execute_command('wc', ['0', '1'], port='/dev/ttyUSB0')
        
        # Check results
        self.assertTrue(success)
        self.assertEqual(response['operation'], 'wc')
        self.assertEqual(response['address'], 0)
        self.assertEqual(response['value'], True)
        self.assertEqual(response['success'], True)
        
        # Verify client calls
        mock_client.connect.assert_called_once()
        mock_client.write_coil.assert_called_once_with(0, True, unit=1)
        mock_client.disconnect.assert_called_once()
    
    @patch('modapi.api.cmd.ModbusRTU')
    def test_execute_command_rc(self, mock_client_class):
        """Test execute_command with read_coils command"""
        # Mock the modbus client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_client.read_coils.return_value = [True, False, True]
        
        # Execute command
        success, response = execute_command('rc', ['0', '3'], port='/dev/ttyUSB0')
        
        # Check results
        self.assertTrue(success)
        self.assertEqual(response['operation'], 'rc')
        self.assertEqual(response['address'], 0)
        self.assertEqual(response['count'], 3)
        self.assertEqual(response['success'], True)
        self.assertEqual(response['data']['values'], [True, False, True])
        
        # Verify client calls
        mock_client.connect.assert_called_once()
        mock_client.read_coils.assert_called_once_with(0, 3, unit=1)
        mock_client.disconnect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
