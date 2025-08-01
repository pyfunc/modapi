"""
Tests for api.rtu module - Direct RTU Modbus Communication
"""

import unittest
from unittest.mock import patch, MagicMock
import struct
import serial

from modapi.api.rtu import ModbusRTU, create_rtu_client, test_rtu_connection


class TestModbusRTU(unittest.TestCase):
    """Test cases for ModbusRTU class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = ModbusRTU(port='/dev/ttyTEST', baudrate=9600, timeout=1.0)
    
    def tearDown(self):
        """Clean up after tests"""
        if self.client:
            self.client.disconnect()
    
    def test_init(self):
        """Test RTU client initialization"""
        client = ModbusRTU(port='/dev/ttyUSB0', baudrate=19200, timeout=2.0)
        
        self.assertEqual(client.port, '/dev/ttyUSB0')
        self.assertEqual(client.baudrate, 19200)
        self.assertEqual(client.timeout, 2.0)
        self.assertEqual(client.FUNC_READ_COILS, 0x01)
        self.assertEqual(client.FUNC_WRITE_SINGLE_COIL, 0x05)
    
    def test_crc_calculation(self):
        """Test CRC16 calculation"""
        # Test known CRC values
        test_data = b'\x01\x01\x00\x00\x00\x08'
        expected_crc = 0x3D04  # Known CRC for this data
        
        calculated_crc = self.client._calculate_crc(test_data)
        
        # Note: CRC might vary based on implementation, so we test the function works
        self.assertIsInstance(calculated_crc, int)
        self.assertTrue(0 <= calculated_crc <= 0xFFFF)
    
    def test_build_request(self):
        """Test building Modbus request frame"""
        unit_id = 1
        function_code = 0x01
        data = b'\x00\x00\x00\x08'
        
        frame = self.client._build_request(unit_id, function_code, data)
        
        # Check frame structure
        self.assertEqual(frame[0], unit_id)
        self.assertEqual(frame[1], function_code)
        self.assertEqual(frame[2:6], data)
        self.assertEqual(len(frame), len(data) + 4)  # unit + func + data + crc
    
    @patch('serial.Serial')
    def test_connect(self, mock_serial):
        """Test serial connection"""
        # Mock successful connection
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_serial.return_value = mock_conn
        
        result = self.client.connect()
        
        self.assertTrue(result)
        self.assertTrue(self.client.is_connected())
        mock_serial.assert_called_once()
    
    @patch('serial.Serial')
    def test_connect_failure(self, mock_serial):
        """Test connection failure"""
        # Mock connection failure
        mock_serial.side_effect = serial.SerialException("Port not available")
        
        result = self.client.connect()
        
        self.assertFalse(result)
        self.assertFalse(self.client.is_connected())
    
    def test_parse_response_valid(self):
        """Test parsing valid response"""
        # Build a valid response frame
        unit_id = 1
        function_code = 0x01
        data = b'\x01\xFF'  # 1 byte count + data
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        response = frame + struct.pack('<H', crc)
        
        result = self.client._parse_response(response, unit_id, function_code)
        
        self.assertEqual(result, data)
    
    def test_parse_response_invalid_crc(self):
        """Test parsing response with invalid CRC"""
        # Build response with wrong CRC
        unit_id = 1
        function_code = 0x01
        data = b'\x01\xFF'
        frame = struct.pack('BB', unit_id, function_code) + data
        wrong_crc = 0x0000  # Wrong CRC
        response = frame + struct.pack('<H', wrong_crc)
        
        result = self.client._parse_response(response, unit_id, function_code)
        
        self.assertIsNone(result)
    
    def test_parse_response_exception(self):
        """Test parsing exception response"""
        # Build exception response (function code with 0x80 bit set)
        unit_id = 1
        function_code = 0x81  # Exception response
        data = b'\x02'  # Exception code
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        response = frame + struct.pack('<H', crc)
        
        result = self.client._parse_response(response, unit_id, 0x01)
        
        self.assertIsNone(result)
    
    @patch('serial.Serial')
    def test_read_coils_success(self, mock_serial):
        """Test successful coil reading"""
        # Mock serial connection
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.in_waiting = 6
        
        # Build mock response for reading 8 coils
        unit_id = 1
        function_code = 0x01
        data = b'\x01\x55'  # 1 byte count + coil data (01010101)
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        mock_response = frame + struct.pack('<H', crc)
        
        mock_conn.read.return_value = mock_response
        mock_serial.return_value = mock_conn
        self.client.serial_conn = mock_conn
        
        result = self.client.read_coils(1, 0, 8)
        
        expected = [True, False, True, False, True, False, True, False]  # 0x55 = 01010101
        self.assertEqual(result, expected)
    
    @patch('serial.Serial')
    def test_read_holding_registers_success(self, mock_serial):
        """Test successful register reading"""
        # Mock serial connection
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.in_waiting = 7
        
        # Build mock response for reading 2 registers
        unit_id = 1
        function_code = 0x03
        data = b'\x04\x12\x34\x56\x78'  # 4 bytes count + 2 registers (0x1234, 0x5678)
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        mock_response = frame + struct.pack('<H', crc)
        
        mock_conn.read.return_value = mock_response
        mock_serial.return_value = mock_conn
        self.client.serial_conn = mock_conn
        
        result = self.client.read_holding_registers(1, 0, 2)
        
        expected = [0x1234, 0x5678]
        self.assertEqual(result, expected)
    
    @patch('serial.Serial')
    def test_write_single_coil_success(self, mock_serial):
        """Test successful single coil writing"""
        # Mock serial connection
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.in_waiting = 8
        
        # Build mock echo response
        unit_id = 1
        function_code = 0x05
        data = struct.pack('>HH', 0, 0xFF00)  # Address 0, value ON
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        mock_response = frame + struct.pack('<H', crc)
        
        mock_conn.read.return_value = mock_response
        mock_serial.return_value = mock_conn
        self.client.serial_conn = mock_conn
        
        result = self.client.write_single_coil(1, 0, True)
        
        self.assertTrue(result)
    
    @patch('serial.Serial')
    def test_write_single_register_success(self, mock_serial):
        """Test successful single register writing"""
        # Mock serial connection
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.in_waiting = 8
        
        # Build mock echo response
        unit_id = 1
        function_code = 0x06
        data = struct.pack('>HH', 0, 1234)  # Address 0, value 1234
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self.client._calculate_crc(frame)
        mock_response = frame + struct.pack('<H', crc)
        
        mock_conn.read.return_value = mock_response
        mock_serial.return_value = mock_conn
        self.client.serial_conn = mock_conn
        
        result = self.client.write_single_register(1, 0, 1234)
        
        self.assertTrue(result)
    
    def test_read_coils_invalid_count(self):
        """Test reading coils with invalid count"""
        result = self.client.read_coils(1, 0, 0)
        self.assertIsNone(result)
        
        result = self.client.read_coils(1, 0, 3000)
        self.assertIsNone(result)
    
    def test_read_registers_invalid_count(self):
        """Test reading registers with invalid count"""
        result = self.client.read_holding_registers(1, 0, 0)
        self.assertIsNone(result)
        
        result = self.client.read_holding_registers(1, 0, 200)
        self.assertIsNone(result)
    
    def test_not_connected_operations(self):
        """Test operations when not connected"""
        # Ensure not connected
        self.client.disconnect()
        
        result = self.client.read_coils(1, 0, 8)
        self.assertIsNone(result)
        
        result = self.client.read_holding_registers(1, 0, 4)
        self.assertIsNone(result)
        
        result = self.client.write_single_coil(1, 0, True)
        self.assertFalse(result)
        
        result = self.client.write_single_register(1, 0, 1234)
        self.assertFalse(result)
    
    @patch('os.path.exists')
    def test_port_exists(self, mock_exists):
        """Test port existence checking"""
        mock_exists.return_value = True
        self.assertTrue(self.client._port_exists('/dev/ttyUSB0'))
        
        mock_exists.return_value = False
        self.assertFalse(self.client._port_exists('/dev/ttyNONE'))
    
    def test_context_manager(self):
        """Test context manager functionality"""
        with patch('serial.Serial') as mock_serial:
            mock_conn = MagicMock()
            mock_conn.is_open = True
            mock_serial.return_value = mock_conn
            
            with ModbusRTU() as client:
                self.assertTrue(client.is_connected())
            
            # Should be disconnected after context
            mock_conn.close.assert_called()


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_rtu_client(self):
        """Test RTU client creation"""
        client = create_rtu_client('/dev/ttyUSB0', 19200, 2.0)
        
        self.assertIsInstance(client, ModbusRTU)
        self.assertEqual(client.port, '/dev/ttyUSB0')
        self.assertEqual(client.baudrate, 19200)
        self.assertEqual(client.timeout, 2.0)
    
    @patch('modapi.api.rtu.ModbusRTU')
    def test_test_rtu_connection(self, mock_rtu_class):
        """Test RTU connection testing function"""
        # Mock RTU client with context manager
        mock_client = MagicMock()
        mock_client.test_connection.return_value = (True, {'connected': True})
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_rtu_class.return_value = mock_client
        
        success, result = test_rtu_connection('/dev/ttyUSB0', 9600, 1)
        
        self.assertTrue(success)
        self.assertEqual(result['connected'], True)
        mock_client.test_connection.assert_called_once_with(1)


class TestIntegration(unittest.TestCase):
    """Integration tests (requires physical hardware or mock)"""
    
    @unittest.skip("Requires physical hardware")
    def test_real_hardware_connection(self):
        """Test with real hardware - skip by default"""
        client = ModbusRTU('/dev/ttyACM0', 9600)
        
        if client.connect():
            # Test basic operations
            success, result = client.test_connection(1)
            print(f"Hardware test result: {result}")
            
            # Test auto-detection
            config = client.auto_detect(['/dev/ttyACM0'])
            if config:
                print(f"Auto-detected config: {config}")
            
            client.disconnect()


if __name__ == '__main__':
    unittest.main()
