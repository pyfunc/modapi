#!/usr/bin/env python3
"""
Integration tests for Modbus RTU module

This script tests the Modbus RTU functionality with a real or simulated device.
"""

import unittest
import logging
from unittest.mock import patch, MagicMock
import serial
from typing import Optional, List, Dict, Any

# Import the RTU module
from modapi.rtu import ModbusRTU, create_rtu_client, test_rtu_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_PORT = '/dev/ttyTEST'  # Will be mocked
TEST_BAUDRATE = 9600
TEST_UNIT_ID = 1

class TestModbusRTUIntegration(unittest.TestCase):
    """Integration tests for ModbusRTU class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once before all tests"""
        # This will be our mock serial connection
        cls.mock_serial = MagicMock(spec=serial.Serial)
        cls.mock_serial.is_open = True
        cls.mock_serial.read.return_value = b''
        
        # Patch serial.Serial to return our mock
        cls.patcher = patch('serial.Serial', return_value=cls.mock_serial)
        cls.patcher.start()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.patcher.stop()
    
    def setUp(self):
        """Set up test fixtures before each test"""
        self.client = ModbusRTU(port=TEST_PORT, baudrate=TEST_BAUDRATE, timeout=1.0)
        self.client.connect()
    
    def tearDown(self):
        """Clean up after each test"""
        if self.client.is_connected():
            self.client.disconnect()
    
    def test_connection(self):
        """Test connection to serial port"""
        self.assertTrue(self.client.is_connected())
        serial.Serial.assert_called_once_with(
            port=TEST_PORT,
            baudrate=TEST_BAUDRATE,
            timeout=1.0,
            parity='N',
            stopbits=1,
            bytesize=8
        )
    
    def test_read_coils(self):
        """Test reading coils"""
        # Mock response: 2 coils, values [True, False]
        response = bytes([0x01, 0x01, 0x01, 0x00, 0x00])  # Mocked response
        self.mock_serial.read.return_value = response
        
        result = self.client.read_coils(0, 2, TEST_UNIT_ID)
        self.assertEqual(result, [True, False])
    
    def test_read_holding_registers(self):
        """Test reading holding registers"""
        # Mock response: 2 registers, values [0x1234, 0x5678]
        response = bytes([0x01, 0x03, 0x04, 0x12, 0x34, 0x56, 0x78, 0x00, 0x00])
        self.mock_serial.read.return_value = response
        
        result = self.client.read_holding_registers(0, 2, TEST_UNIT_ID)
        self.assertEqual(result, [0x1234, 0x5678])
    
    def test_write_coil(self):
        """Test writing a single coil"""
        # Mock response for write single coil
        response = bytes([0x01, 0x05, 0x00, 0x01, 0xFF, 0x00, 0x00, 0x00])
        self.mock_serial.read.return_value = response
        
        result = self.client.write_coil(1, True, TEST_UNIT_ID)
        self.assertTrue(result)
    
    def test_write_register(self):
        """Test writing a single register"""
        # Mock response for write single register
        response = bytes([0x01, 0x06, 0x00, 0x01, 0x12, 0x34, 0x00, 0x00])
        self.mock_serial.read.return_value = response
        
        result = self.client.write_register(1, 0x1234, TEST_UNIT_ID)
        self.assertTrue(result)

class TestRTUFunctions(unittest.TestCase):
    """Tests for convenience functions"""
    
    @patch('modapi.api.rtu.ModbusRTU')
    def test_create_rtu_client(self, mock_rtu):
        """Test create_rtu_client function"""
        # Create a mock client
        mock_client = MagicMock()
        mock_rtu.return_value = mock_client
        
        # Test creating a client
        client = create_rtu_client(port=TEST_PORT, baudrate=TEST_BAUDRATE)
        
        # Verify client was created and connected
        self.assertEqual(client, mock_client)
        mock_client.connect.assert_called_once()
    
    @patch('modapi.api.rtu.ModbusRTU')
    def test_test_rtu_connection(self, mock_rtu):
        """Test test_rtu_connection function"""
        # Create a mock client with successful connection
        mock_client = MagicMock()
        mock_client.read_holding_registers.return_value = [0x1234]
        mock_rtu.return_value = mock_client
        
        # Test connection
        success, result = test_rtu_connection(port=TEST_PORT, baudrate=TEST_BAUDRATE)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(result['port'], TEST_PORT)
        self.assertEqual(result['baudrate'], TEST_BAUDRATE)
        self.assertTrue(result['success'])

if __name__ == '__main__':
    unittest.main()
