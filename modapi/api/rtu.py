"""
Direct RTU Modbus Communication Module
Bezpośrednia komunikacja z /dev/ttyACM0 bez PyModbus
"""

import serial
import struct
import time
import logging
from typing import Optional, List, Tuple, Union, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class ModbusRTU:
    """
    Direct RTU Modbus communication class
    Bezpośrednia komunikacja Modbus RTU przez port szeregowy
    """
    
    def __init__(self, 
                 port: str = '/dev/ttyACM0',
                 baudrate: int = 9600,
                 timeout: float = 1.0,
                 parity: str = 'N',
                 stopbits: int = 1,
                 bytesize: int = 8):
        """
        Initialize RTU Modbus connection
        
        Args:
            port: Serial port path (default: /dev/ttyACM0)
            baudrate: Baud rate (default: 9600)
            timeout: Read timeout in seconds
            parity: Parity setting (N/E/O)
            stopbits: Stop bits (1 or 2)
            bytesize: Data bits (7 or 8)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        
        self.serial_conn: Optional[serial.Serial] = None
        self.lock = Lock()  # Thread safety
        
        # Modbus function codes
        self.FUNC_READ_COILS = 0x01
        self.FUNC_READ_DISCRETE_INPUTS = 0x02
        self.FUNC_READ_HOLDING_REGISTERS = 0x03
        self.FUNC_READ_INPUT_REGISTERS = 0x04
        self.FUNC_WRITE_SINGLE_COIL = 0x05
        self.FUNC_WRITE_SINGLE_REGISTER = 0x06
        self.FUNC_WRITE_MULTIPLE_COILS = 0x0F
        self.FUNC_WRITE_MULTIPLE_REGISTERS = 0x10
        
        logger.info(f"Initialized ModbusRTU for {port} at {baudrate} baud")
    
    def connect(self) -> bool:
        """
        Connect to serial port
        
        Returns:
            bool: True if connected successfully
        """
        try:
            with self.lock:
                if self.serial_conn and self.serial_conn.is_open:
                    self.serial_conn.close()
                
                self.serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    bytesize=self.bytesize
                )
                
                if self.serial_conn.is_open:
                    logger.info(f"Connected to {self.port}")
                    return True
                else:
                    logger.error(f"Failed to open {self.port}")
                    return False
                    
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        try:
            with self.lock:
                if self.serial_conn and self.serial_conn.is_open:
                    self.serial_conn.close()
                    logger.info("Disconnected from serial port")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to serial port"""
        return self.serial_conn is not None and self.serial_conn.is_open
    
    def _calculate_crc(self, data: bytes) -> int:
        """
        Calculate Modbus RTU CRC16
        
        Args:
            data: Data bytes for CRC calculation
            
        Returns:
            int: CRC16 value
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _build_request(self, unit_id: int, function_code: int, data: bytes) -> bytes:
        """
        Build Modbus RTU request frame
        
        Args:
            unit_id: Slave unit ID
            function_code: Modbus function code
            data: Request data
            
        Returns:
            bytes: Complete RTU frame with CRC
        """
        frame = struct.pack('BB', unit_id, function_code) + data
        crc = self._calculate_crc(frame)
        frame += struct.pack('<H', crc)  # Little endian CRC
        return frame
    
    def _parse_response(self, response: bytes, expected_unit: int, expected_function: int) -> Optional[bytes]:
        """
        Parse and validate Modbus RTU response
        
        Args:
            response: Raw response bytes
            expected_unit: Expected unit ID
            expected_function: Expected function code
            
        Returns:
            Optional[bytes]: Response data or None if invalid
        """
        if len(response) < 4:
            logger.error("Response too short")
            return None
        
        # Extract components
        unit_id = response[0]
        function_code = response[1]
        data = response[2:-2]
        received_crc = struct.unpack('<H', response[-2:])[0]
        
        # Validate CRC
        calculated_crc = self._calculate_crc(response[:-2])
        if received_crc != calculated_crc:
            logger.error(f"CRC mismatch: got {received_crc:04X}, expected {calculated_crc:04X}")
            return None
        
        # Validate unit ID
        if unit_id != expected_unit:
            logger.error(f"Unit ID mismatch: got {unit_id}, expected {expected_unit}")
            return None
        
        # Check for exception response
        if function_code & 0x80:
            exception_code = data[0] if len(data) > 0 else 0
            logger.error(f"Modbus exception: {exception_code}")
            return None
        
        # Validate function code
        if function_code != expected_function:
            logger.error(f"Function code mismatch: got {function_code}, expected {expected_function}")
            return None
        
        return data
    
    def _send_request(self, unit_id: int, function_code: int, data: bytes) -> Optional[bytes]:
        """
        Send request and receive response
        
        Args:
            unit_id: Slave unit ID
            function_code: Modbus function code
            data: Request data
            
        Returns:
            Optional[bytes]: Response data or None if error
        """
        if not self.is_connected():
            logger.error("Not connected to serial port")
            return None
        
        try:
            with self.lock:
                # Clear input buffer
                self.serial_conn.reset_input_buffer()
                
                # Build and send request
                request = self._build_request(unit_id, function_code, data)
                logger.debug(f"Sending: {request.hex()}")
                self.serial_conn.write(request)
                
                # Wait for response
                time.sleep(0.01)  # Small delay for response
                
                # Read response
                response = b""
                start_time = time.time()
                
                while len(response) < 4 and (time.time() - start_time) < self.timeout:
                    if self.serial_conn.in_waiting:
                        response += self.serial_conn.read(self.serial_conn.in_waiting)
                    else:
                        time.sleep(0.001)
                
                if len(response) < 4:
                    logger.error("Timeout waiting for response")
                    return None
                
                logger.debug(f"Received: {response.hex()}")
                
                # Parse response
                return self._parse_response(response, unit_id, function_code)
                
        except Exception as e:
            logger.error(f"Communication error: {e}")
            return None
    
    def read_coils(self, unit_id: int, address: int, count: int) -> Optional[List[bool]]:
        """
        Read coils (function code 0x01)
        
        Args:
            unit_id: Slave unit ID
            address: Starting address
            count: Number of coils to read
            
        Returns:
            Optional[List[bool]]: List of coil states or None if error
        """
        if count < 1 or count > 2000:
            logger.error("Invalid coil count")
            return None
        
        # Build request data
        data = struct.pack('>HH', address, count)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_READ_COILS, data)
        if response_data is None:
            return None
        
        try:
            # Parse response
            byte_count = response_data[0]
            coil_data = response_data[1:1+byte_count]
            
            # Convert bytes to boolean list
            coils = []
            for i in range(count):
                byte_index = i // 8
                bit_index = i % 8
                if byte_index < len(coil_data):
                    coils.append(bool(coil_data[byte_index] & (1 << bit_index)))
                else:
                    coils.append(False)
            
            return coils
            
        except Exception as e:
            logger.error(f"Error parsing coils response: {e}")
            return None
    
    def read_holding_registers(self, unit_id: int, address: int, count: int) -> Optional[List[int]]:
        """
        Read holding registers (function code 0x03)
        
        Args:
            unit_id: Slave unit ID
            address: Starting address
            count: Number of registers to read
            
        Returns:
            Optional[List[int]]: List of register values or None if error
        """
        if count < 1 or count > 125:
            logger.error("Invalid register count")
            return None
        
        # Build request data
        data = struct.pack('>HH', address, count)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_READ_HOLDING_REGISTERS, data)
        if response_data is None:
            return None
        
        try:
            # Parse response
            byte_count = response_data[0]
            register_data = response_data[1:1+byte_count]
            
            # Convert bytes to register values
            registers = []
            for i in range(0, len(register_data), 2):
                if i + 1 < len(register_data):
                    value = struct.unpack('>H', register_data[i:i+2])[0]
                    registers.append(value)
            
            return registers
            
        except Exception as e:
            logger.error(f"Error parsing registers response: {e}")
            return None
    
    def write_single_coil(self, unit_id: int, address: int, value: bool) -> bool:
        """
        Write single coil (function code 0x05)
        
        Args:
            unit_id: Slave unit ID
            address: Coil address
            value: Coil value (True/False)
            
        Returns:
            bool: True if successful
        """
        # Build request data
        coil_value = 0xFF00 if value else 0x0000
        data = struct.pack('>HH', address, coil_value)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_WRITE_SINGLE_COIL, data)
        if response_data is None:
            return False
        
        # Validate echo response
        try:
            resp_address, resp_value = struct.unpack('>HH', response_data)
            return resp_address == address and resp_value == coil_value
        except Exception as e:
            logger.error(f"Error validating coil write response: {e}")
            return False
    
    def write_single_register(self, unit_id: int, address: int, value: int) -> bool:
        """
        Write single register (function code 0x06)
        
        Args:
            unit_id: Slave unit ID
            address: Register address
            value: Register value
            
        Returns:
            bool: True if successful
        """
        # Build request data
        data = struct.pack('>HH', address, value & 0xFFFF)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_WRITE_SINGLE_REGISTER, data)
        if response_data is None:
            return False
        
        # Validate echo response
        try:
            resp_address, resp_value = struct.unpack('>HH', response_data)
            return resp_address == address and resp_value == (value & 0xFFFF)
        except Exception as e:
            logger.error(f"Error validating register write response: {e}")
            return False
    
    def test_connection(self, unit_id: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        Test connection to Modbus device
        
        Args:
            unit_id: Unit ID to test
            
        Returns:
            Tuple[bool, Dict]: (success, info_dict)
        """
        result = {
            'port': self.port,
            'baudrate': self.baudrate,
            'unit_id': unit_id,
            'connected': False,
            'test_read': False,
            'error': None
        }
        
        try:
            if not self.is_connected():
                if not self.connect():
                    result['error'] = 'Failed to connect to serial port'
                    return False, result
            
            result['connected'] = True
            
            # Test read operation (try to read 1 coil at address 0)
            coils = self.read_coils(unit_id, 0, 1)
            if coils is not None:
                result['test_read'] = True
                result['coil_0_value'] = coils[0] if len(coils) > 0 else None
                return True, result
            else:
                result['error'] = 'Failed to read test coil'
                return False, result
                
        except Exception as e:
            result['error'] = str(e)
            return False, result
    
    def auto_detect(self, ports: List[str] = None, 
                   baudrates: List[int] = None,
                   unit_ids: List[int] = None) -> Optional[Dict[str, Any]]:
        """
        Auto-detect working Modbus RTU configuration
        
        Args:
            ports: List of ports to test (default: ['/dev/ttyACM0', '/dev/ttyUSB0'])
            baudrates: List of baudrates to test
            unit_ids: List of unit IDs to test
            
        Returns:
            Optional[Dict]: Working configuration or None
        """
        if ports is None:
            ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyS0']
        
        if baudrates is None:
            baudrates = [9600, 19200, 38400, 57600, 115200]
        
        if unit_ids is None:
            unit_ids = [1, 2, 3, 4, 5]
        
        logger.info("Auto-detecting Modbus RTU configuration...")
        
        for port in ports:
            if not self._port_exists(port):
                continue
                
            logger.info(f"Testing port: {port}")
            
            for baudrate in baudrates:
                logger.info(f"  Testing baudrate: {baudrate}")
                
                # Update configuration
                old_port = self.port
                old_baudrate = self.baudrate
                
                self.port = port
                self.baudrate = baudrate
                
                # Disconnect and reconnect with new settings
                self.disconnect()
                
                if self.connect():
                    for unit_id in unit_ids:
                        success, result = self.test_connection(unit_id)
                        if success:
                            logger.info(f"Found working configuration: {port} @ {baudrate} baud, unit {unit_id}")
                            return {
                                'port': port,
                                'baudrate': baudrate,
                                'unit_id': unit_id,
                                'test_result': result
                            }
                
                # Restore old settings if not found
                self.port = old_port
                self.baudrate = old_baudrate
                self.disconnect()
        
        logger.warning("No working Modbus RTU configuration found")
        return None
    
    def _port_exists(self, port: str) -> bool:
        """Check if serial port exists"""
        import os
        return os.path.exists(port)
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def find_serial_ports() -> List[str]:
    """
    Find available serial ports on the system
    
    Returns:
        List[str]: List of available serial port paths
    """
    import serial.tools.list_ports
    
    # Common serial port paths to check
    common_ports = [
        '/dev/ttyACM0',  # Common for USB adapters on Linux
        '/dev/ttyUSB0',  # Common for USB-to-serial adapters on Linux
        '/dev/ttyS0',    # Common for built-in serial ports on Linux
        '/dev/ttyAMA0',  # Common for Raspberry Pi GPIO UART
        'COM1',          # Common on Windows
        'COM3',          # Common on Windows
    ]
    
    # Get list of available ports
    available_ports = []
    
    # First try to use list_ports.comports() which works on most platforms
    try:
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if port.device and port.device not in available_ports:
                available_ports.append(port.device)
    except Exception as e:
        logger.warning(f"Error listing serial ports: {e}")
    
    # Also check common ports in case they weren't found by list_ports
    for port in common_ports:
        try:
            if port not in available_ports and os.path.exists(port):
                available_ports.append(port)
        except Exception as e:
            logger.debug(f"Error checking port {port}: {e}")
    
    if not available_ports:
        logger.warning("No serial ports found. Check connections and permissions.")
    else:
        logger.info(f"Found serial ports: {', '.join(available_ports)}")
    
    return available_ports


def test_modbus_port(port: str, baudrate: int = 9600, timeout: float = 0.5) -> bool:
    """
    Test if a serial port has a Modbus device connected
    
    Args:
        port: Serial port path to test
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        
    Returns:
        bool: True if a Modbus device is detected
    """
    try:
        with ModbusRTU(port=port, baudrate=baudrate, timeout=timeout) as client:
            if not client.is_connected():
                return False
            
            # Try to read a register to verify it's a Modbus device
            # Using function code 0x03 (read holding registers) with address 0
            # This is a common register that many Modbus devices implement
            success, _ = client.test_connection(unit_id=1)
            return success
            
    except Exception as e:
        logger.debug(f"Error testing port {port}: {e}")
        return False


# Convenience functions for backward compatibility
def create_rtu_client(port: str = '/dev/ttyACM0', 
                     baudrate: int = 9600,
                     timeout: float = 1.0) -> ModbusRTU:
    """
    Create RTU client instance
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        timeout: Timeout in seconds
        
    Returns:
        ModbusRTU: RTU client instance
    """
    return ModbusRTU(port=port, baudrate=baudrate, timeout=timeout)


def test_rtu_connection(port: str = '/dev/ttyACM0',
                       baudrate: int = 9600,
                       unit_id: int = 1) -> Tuple[bool, Dict[str, Any]]:
    """
    Test RTU connection quickly
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        unit_id: Unit ID to test
        
    Returns:
        Tuple[bool, Dict]: (success, result_dict)
    """
    with ModbusRTU(port=port, baudrate=baudrate) as client:
        return client.test_connection(unit_id)


if __name__ == "__main__":
    # Test the RTU module
    logging.basicConfig(level=logging.INFO)
    
    print("Testing direct RTU communication...")
    
    client = ModbusRTU()
    
    # Auto-detect configuration
    config = client.auto_detect()
    if config:
        print(f"Found working configuration: {config}")
        
        # Test operations
        with client:
            unit_id = config['unit_id']
            
            # Test reading coils
            coils = client.read_coils(unit_id, 0, 8)
            if coils:
                print(f"Coils 0-7: {coils}")
            
            # Test reading registers
            registers = client.read_holding_registers(unit_id, 0, 4)
            if registers:
                print(f"Registers 0-3: {registers}")
                
            # Test writing coil
            if client.write_single_coil(unit_id, 0, True):
                print("Successfully wrote coil 0 to True")
    else:
        print("No working configuration found")
