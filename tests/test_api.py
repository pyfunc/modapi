"""
Tests for modbusapi.api module
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import flask

# Add parent directory to path to import modbusapi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modbusapi.api import create_rest_app, start_mqtt_broker


class TestRestApi(unittest.TestCase):
    """Test cases for REST API"""

    @patch('modbusapi.api.ModbusClient')
    def setUp(self, mock_client_class):
        """Set up test fixtures"""
        self.mock_client = mock_client_class.return_value
        self.app = create_rest_app(port='/dev/ttyUSB0')
        self.client = self.app.test_client()

    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        self.mock_client.is_connected.return_value = True
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
        self.assertEqual(data['address'], 0)
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
        """Test POST /api/coils/<address> endpoint"""
        self.mock_client.write_coil.return_value = True
        response = self.client.post('/api/coils/0', 
                                   data=json.dumps({'value': True}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['success'], True)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['value'], True)
        self.mock_client.write_coil.assert_called_with(0, True, unit=1)

    def test_toggle_endpoint(self):
        """Test POST /api/toggle/<address> endpoint"""
        # Mock read_coils to return False (OFF)
        self.mock_client.read_coils.return_value = [False]
        # Mock write_coil to return True (success)
        self.mock_client.write_coil.return_value = True
        
        response = self.client.post('/api/toggle/0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['success'], True)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['previous'], False)
        self.assertEqual(data['current'], True)
        
        # Verify that write_coil was called with True (ON)
        self.mock_client.write_coil.assert_called_with(0, True, unit=1)

    def test_read_discrete_inputs_endpoint(self):
        """Test /api/discrete_inputs/<address>/<count> endpoint"""
        self.mock_client.read_discrete_inputs.return_value = [True, False]
        response = self.client.get('/api/discrete_inputs/0/2')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['values'], [True, False])

    def test_read_holding_registers_endpoint(self):
        """Test /api/holding_registers/<address>/<count> endpoint"""
        self.mock_client.read_holding_registers.return_value = [123, 456]
        response = self.client.get('/api/holding_registers/0/2')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['values'], [123, 456])

    def test_write_holding_register_endpoint(self):
        """Test POST /api/holding_registers/<address> endpoint"""
        self.mock_client.write_register.return_value = True
        response = self.client.post('/api/holding_registers/0', 
                                   data=json.dumps({'value': 123}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['success'], True)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['value'], 123)
        self.mock_client.write_register.assert_called_with(0, 123, unit=1)

    def test_read_input_registers_endpoint(self):
        """Test /api/input_registers/<address>/<count> endpoint"""
        self.mock_client.read_input_registers.return_value = [789, 101]
        response = self.client.get('/api/input_registers/0/2')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['address'], 0)
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['values'], [789, 101])

    def test_scan_endpoint(self):
        """Test /api/scan endpoint"""
        with patch('modbusapi.api.auto_detect_modbus_port') as mock_scan:
            mock_scan.return_value = '/dev/ttyUSB0'
            response = self.client.get('/api/scan')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['port'], '/dev/ttyUSB0')


class TestMqttApi(unittest.TestCase):
    """Test cases for MQTT API"""

    @patch('modbusapi.api.mqtt.Client')
    @patch('modbusapi.api.ModbusClient')
    def test_start_mqtt_broker(self, mock_modbus_client, mock_mqtt_client):
        """Test start_mqtt_broker function"""
        # Setup mocks
        mock_mqtt = mock_mqtt_client.return_value
        mock_modbus = mock_modbus_client.return_value
        
        # Call function
        client = start_mqtt_broker(
            port='/dev/ttyUSB0',
            mqtt_broker='localhost',
            mqtt_port=1883,
            mqtt_topic_prefix='modbus'
        )
        
        # Verify MQTT client was created and connected
        self.assertEqual(client, mock_mqtt)
        mock_mqtt.connect.assert_called_with('localhost', 1883, 60)
        mock_mqtt.loop_start.assert_called_once()
        
        # Verify subscriptions
        expected_topics = [
            'modbus/command/#',
        ]
        mock_mqtt.subscribe.assert_called_with(expected_topics[0])

    @patch('modbusapi.api.mqtt.Client')
    @patch('modbusapi.api.ModbusClient')
    def test_mqtt_on_message(self, mock_modbus_client, mock_mqtt_client):
        """Test MQTT message handling"""
        # Setup mocks
        mock_mqtt = mock_mqtt_client.return_value
        mock_modbus = mock_modbus_client.return_value
        mock_modbus.read_coils.return_value = [True]
        
        # Call function to get the on_message handler
        start_mqtt_broker(
            port='/dev/ttyUSB0',
            mqtt_broker='localhost',
            mqtt_port=1883,
            mqtt_topic_prefix='modbus'
        )
        
        # Get the on_message callback that was registered
        on_message = mock_mqtt.on_message
        
        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = 'modbus/command/read_coil/0/1'
        mock_msg.payload = b''
        
        # Call the handler
        on_message(mock_mqtt, None, mock_msg)
        
        # Verify modbus client was called
        mock_modbus.read_coils.assert_called_with(0, 1, unit=1)
        
        # Verify publish was called with the result
        mock_mqtt.publish.assert_called()
        args = mock_mqtt.publish.call_args[0]
        self.assertEqual(args[0], 'modbus/response/read_coil/0/1')
        # The second argument is the payload, which should be a JSON string
        payload = json.loads(args[1])
        self.assertEqual(payload['success'], True)


if __name__ == '__main__':
    unittest.main()
