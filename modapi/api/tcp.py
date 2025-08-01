"""
Modbus TCP Communication Module
Komunikacja Modbus TCP przez Ethernet
"""

import socket
import struct
import time
import logging
from typing import Optional, List, Tuple, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class ModbusTCP:
    """
    Modbus TCP communication class
    Komunikacja Modbus TCP przez Ethernet
    """
    
    def __init__(self, 
                 host: str = '192.168.1.100',
                 port: int = 502,
                 timeout: float = 5.0,
                 unit_id: int = 1):
        """
        Initialize Modbus TCP connection
        
        Args:
            host: TCP host address (default: 192.168.1.100)
            port: TCP port (default: 502 - standard Modbus TCP port)
            timeout: Connection timeout in seconds
            unit_id: Default unit ID for requests
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.unit_id = unit_id
        
        self.socket: Optional[socket.socket] = None
        self.lock = Lock()  # Thread safety
        self.transaction_id = 0
        
        # Modbus function codes
        self.FUNC_READ_COILS = 0x01
        self.FUNC_READ_DISCRETE_INPUTS = 0x02
        self.FUNC_READ_HOLDING_REGISTERS = 0x03
        self.FUNC_READ_INPUT_REGISTERS = 0x04
        self.FUNC_WRITE_SINGLE_COIL = 0x05
        self.FUNC_WRITE_SINGLE_REGISTER = 0x06
        self.FUNC_WRITE_MULTIPLE_COILS = 0x0F
        self.FUNC_WRITE_MULTIPLE_REGISTERS = 0x10
        
        logger.info(f"Initialized ModbusTCP for {host}:{port}")
    
    def connect(self) -> bool:
        """
        Connect to Modbus TCP server
        
        Returns:
            bool: True if connected successfully
        """
        try:
            with self.lock:
                if self.socket:
                    self.socket.close()
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
                
                logger.info(f"Connected to {self.host}:{self.port}")
                return True
                
        except Exception as e:
            logger.error(f"TCP connection error: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from TCP server"""
        try:
            with self.lock:
                if self.socket:
                    self.socket.close()
                    self.socket = None
                    logger.info("Disconnected from TCP server")
        except Exception as e:
            logger.error(f"TCP disconnect error: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to TCP server"""
        return self.socket is not None
    
    def _get_transaction_id(self) -> int:
        """Get next transaction ID"""
        self.transaction_id = (self.transaction_id + 1) % 65536
        return self.transaction_id
    
    def _build_mbap_header(self, unit_id: int, data_length: int) -> bytes:
        """
        Build Modbus Application Protocol (MBAP) header
        
        Args:
            unit_id: Unit identifier
            data_length: Length of PDU data
            
        Returns:
            bytes: MBAP header (7 bytes)
        """
        transaction_id = self._get_transaction_id()
        protocol_id = 0  # Modbus protocol
        length = data_length + 1  # PDU + Unit ID
        
        return struct.pack('>HHHB', transaction_id, protocol_id, length, unit_id)
    
    def _build_request(self, unit_id: int, function_code: int, data: bytes) -> bytes:
        """
        Build complete Modbus TCP request
        
        Args:
            unit_id: Unit identifier
            function_code: Modbus function code
            data: Request data (PDU)
            
        Returns:
            bytes: Complete TCP request with MBAP header
        """
        pdu = struct.pack('B', function_code) + data
        mbap_header = self._build_mbap_header(unit_id, len(pdu))
        return mbap_header + pdu
    
    def _parse_response(self, response: bytes, expected_function: int) -> Optional[bytes]:
        """
        Parse Modbus TCP response
        
        Args:
            response: Raw response bytes
            expected_function: Expected function code
            
        Returns:
            Optional[bytes]: Response data or None if invalid
        """
        if len(response) < 8:  # MBAP header (7) + function code (1)
            logger.error("TCP response too short")
            return None
        
        try:
            # Parse MBAP header
            transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', response[:7])
            
            # Extract PDU
            pdu = response[7:7+length-1]  # -1 because length includes unit_id
            
            if len(pdu) < 1:
                logger.error("Empty PDU")
                return None
            
            function_code = pdu[0]
            data = pdu[1:]
            
            # Check for exception response
            if function_code & 0x80:
                exception_code = data[0] if len(data) > 0 else 0
                logger.error(f"Modbus TCP exception: {exception_code}")
                return None
            
            # Validate function code
            if function_code != expected_function:
                logger.error(f"Function code mismatch: got {function_code}, expected {expected_function}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing TCP response: {e}")
            return None
    
    def _send_request(self, unit_id: int, function_code: int, data: bytes) -> Optional[bytes]:
        """
        Send TCP request and receive response
        
        Args:
            unit_id: Unit identifier
            function_code: Modbus function code
            data: Request data
            
        Returns:
            Optional[bytes]: Response data or None if error
        """
        if not self.is_connected():
            logger.error("Not connected to TCP server")
            return None
        
        try:
            with self.lock:
                # Build and send request
                request = self._build_request(unit_id, function_code, data)
                logger.debug(f"Sending TCP: {request.hex()}")
                self.socket.send(request)
                
                # Read response header first
                header_data = b""
                while len(header_data) < 7:  # MBAP header size
                    chunk = self.socket.recv(7 - len(header_data))
                    if not chunk:
                        logger.error("Connection closed while reading header")
                        return None
                    header_data += chunk
                
                # Parse header to get data length
                transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', header_data)
                
                # Read remaining data
                remaining_length = length - 1  # -1 for unit_id already read
                pdu_data = b""
                while len(pdu_data) < remaining_length:
                    chunk = self.socket.recv(remaining_length - len(pdu_data))
                    if not chunk:
                        logger.error("Connection closed while reading data")
                        return None
                    pdu_data += chunk
                
                response = header_data + pdu_data
                logger.debug(f"Received TCP: {response.hex()}")
                
                # Parse response
                return self._parse_response(response, function_code)
                
        except Exception as e:
            logger.error(f"TCP communication error: {e}")
            return None
    
    def read_coils(self, unit_id: Optional[int] = None, address: int = 0, count: int = 1) -> Optional[List[bool]]:
        """
        Read coils (function code 0x01)
        
        Args:
            unit_id: Unit identifier (uses default if None)
            address: Starting address
            count: Number of coils to read
            
        Returns:
            Optional[List[bool]]: List of coil states or None if error
        """
        if unit_id is None:
            unit_id = self.unit_id
            
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
    
    def read_holding_registers(self, unit_id: Optional[int] = None, address: int = 0, count: int = 1) -> Optional[List[int]]:
        """
        Read holding registers (function code 0x03)
        
        Args:
            unit_id: Unit identifier (uses default if None)
            address: Starting address
            count: Number of registers to read
            
        Returns:
            Optional[List[int]]: List of register values or None if error
        """
        if unit_id is None:
            unit_id = self.unit_id
            
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
    
    def write_single_coil(self, unit_id: Optional[int] = None, address: int = 0, value: bool = False) -> bool:
        """
        Write single coil (function code 0x05)
        
        Args:
            unit_id: Unit identifier (uses default if None)
            address: Coil address
            value: Coil value (True/False)
            
        Returns:
            bool: True if successful
        """
        if unit_id is None:
            unit_id = self.unit_id
            
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
    
    def write_single_register(self, unit_id: Optional[int] = None, address: int = 0, value: int = 0) -> bool:
        """
        Write single register (function code 0x06)
        
        Args:
            unit_id: Unit identifier (uses default if None)
            address: Register address
            value: Register value
            
        Returns:
            bool: True if successful
        """
        if unit_id is None:
            unit_id = self.unit_id
            
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
    
    def test_connection(self, unit_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Test connection to Modbus TCP server
        
        Args:
            unit_id: Unit ID to test (uses default if None)
            
        Returns:
            Tuple[bool, Dict]: (success, info_dict)
        """
        if unit_id is None:
            unit_id = self.unit_id
            
        result = {
            'host': self.host,
            'port': self.port,
            'unit_id': unit_id,
            'connected': False,
            'test_read': False,
            'error': None
        }
        
        try:
            if not self.is_connected():
                if not self.connect():
                    result['error'] = 'Failed to connect to TCP server'
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
    
    def scan_network(self, base_ip: str = "192.168.1", port: int = 502, 
                    timeout: float = 1.0, ip_range: range = range(1, 255)) -> List[Dict[str, Any]]:
        """
        Scan network for Modbus TCP devices
        
        Args:
            base_ip: Base IP address (e.g., "192.168.1")
            port: TCP port to scan (default: 502)
            timeout: Connection timeout per IP
            ip_range: Range of IP addresses to scan
            
        Returns:
            List[Dict]: List of found devices with connection info
        """
        found_devices = []
        
        logger.info(f"Scanning network {base_ip}.x:{port} for Modbus TCP devices...")
        
        for ip_suffix in ip_range:
            host = f"{base_ip}.{ip_suffix}"
            
            try:
                # Test connection
                test_client = ModbusTCP(host=host, port=port, timeout=timeout)
                if test_client.connect():
                    # Test communication
                    success, result = test_client.test_connection()
                    if success:
                        device_info = {
                            'host': host,
                            'port': port,
                            'unit_id': self.unit_id,
                            'status': 'active',
                            'test_result': result
                        }
                        found_devices.append(device_info)
                        logger.info(f"Found device at {host}:{port}")
                    
                    test_client.disconnect()
                    
            except Exception as e:
                logger.debug(f"No device at {host}:{port} - {e}")
                continue
        
        logger.info(f"Network scan complete. Found {len(found_devices)} devices.")
        return found_devices
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience functions
def create_tcp_client(host: str = '192.168.1.100', 
                     port: int = 502,
                     timeout: float = 5.0,
                     unit_id: int = 1) -> ModbusTCP:
    """
    Create TCP client instance
    
    Args:
        host: TCP host address
        port: TCP port
        timeout: Connection timeout
        unit_id: Default unit ID
        
    Returns:
        ModbusTCP: TCP client instance
    """
    return ModbusTCP(host=host, port=port, timeout=timeout, unit_id=unit_id)


def test_tcp_connection(host: str = '192.168.1.100',
                       port: int = 502,
                       unit_id: int = 1) -> Tuple[bool, Dict[str, Any]]:
    """
    Test TCP connection quickly
    
    Args:
        host: TCP host address
        port: TCP port
        unit_id: Unit ID to test
        
    Returns:
        Tuple[bool, Dict]: (success, result_dict)
    """
    with ModbusTCP(host=host, port=port, unit_id=unit_id) as client:
        return client.test_connection(unit_id)


def scan_modbus_network(base_ip: str = "192.168.1") -> List[Dict[str, Any]]:
    """
    Scan network for Modbus TCP devices
    
    Args:
        base_ip: Base IP address
        
    Returns:
        List[Dict]: List of found devices
    """
    scanner = ModbusTCP()
    return scanner.scan_network(base_ip)


if __name__ == "__main__":
    # Test the TCP module
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Modbus TCP communication...")
    
    # Test with default settings
    client = ModbusTCP()
    
    if client.connect():
        print(f"Connected to {client.host}:{client.port}")
        
        # Test basic operations
        success, result = client.test_connection()
        if success:
            print(f"Test successful: {result}")
            
            # Test reading coils
            coils = client.read_coils(address=0, count=8)
            if coils:
                print(f"Coils 0-7: {coils}")
            
            # Test reading registers
            registers = client.read_holding_registers(address=0, count=4)
            if registers:
                print(f"Registers 0-3: {registers}")
                
            # Test writing coil
            if client.write_single_coil(address=0, value=True):
                print("Successfully wrote coil 0 to True")
        else:
            print(f"Test failed: {result}")
            
        client.disconnect()
    else:
        print(f"Failed to connect to {client.host}:{client.port}")
        
        # Try network scan
        print("Scanning network for Modbus TCP devices...")
        devices = scan_modbus_network()
        if devices:
            print(f"Found {len(devices)} devices:")
            for device in devices:
                print(f"  - {device['host']}:{device['port']}")
        else:
            print("No Modbus TCP devices found on network")
