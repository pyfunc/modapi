"""
modapi Client - Core Modbus communication functionality
"""

import os
import logging
import glob
from typing import Optional, List, Union, Dict, Any

try:
    from pymodbus.client.serial import ModbusSerialClient
    from pymodbus.exceptions import ModbusException, ConnectionException
    # Try to import payload modules, but make them optional
    try:
        from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
    except ImportError:
        BinaryPayloadDecoder = None
        BinaryPayloadBuilder = None
except ImportError:
    raise ImportError(
        "pymodbus library not found! Install with: pip install pymodbus[serial]"
    )

try:
    from dotenv import load_dotenv
except ImportError:
    raise ImportError(
        "python-dotenv library not found! Install with: pip install python-dotenv"
    )

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


def find_serial_ports() -> List[str]:
    """
    Find all available serial ports (ACM and USB)
    
    Returns:
        List of available serial port paths
    """
    ports = []
    
    # Check for ACM ports (USB CDC devices)
    acm_ports = glob.glob('/dev/ttyACM*')
    ports.extend(sorted(acm_ports))
    
    # Check for USB serial ports
    usb_ports = glob.glob('/dev/ttyUSB*')
    ports.extend(sorted(usb_ports))
    
    logger.info(f"Found serial ports: {ports}")
    return ports


def test_modbus_port(port: str, baudrate: int = 9600, timeout: float = 0.5) -> bool:
    """
    Test if a serial port responds to Modbus communication
    
    Args:
        port: Serial port path
        baudrate: Communication speed
        timeout: Connection timeout
        
    Returns:
        True if port responds to Modbus, False otherwise
    """
    try:
        logger.info(f"Testing Modbus on {port} at {baudrate} baud")
        
        client = ModbusSerialClient(
            method='rtu',
            port=port,
            baudrate=baudrate,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=timeout
        )
        
        if not client.connect():
            logger.debug(f"Failed to connect to {port}")
            return False
            
        # Try to read a coil to test communication
        try:
            result = client.read_coils(0, 1, unit=1)
            if not result.isError():
                logger.info(f"Modbus device found on {port} (unit 1, address 0)")
                return True
        except Exception as e:
            logger.debug(f"Error testing {port}: {e}")
            
        client.close()
        return False
        
    except Exception as e:
        logger.debug(f"Error connecting to {port}: {e}")
        return False


def auto_detect_modbus_port(baudrates: List[int] = None) -> Optional[str]:
    """
    Automatically detect which serial port has a working Modbus device
    
    Args:
        baudrates: List of baud rates to test (default: common rates)
        
    Returns:
        Path to working Modbus port or None if not found
    """
    if baudrates is None:
        baudrates = [9600, 19200, 38400, 57600, 115200]
        
    print("Scanning for Modbus devices...")
    
    # Get available ports
    ports = find_serial_ports()
    if not ports:
        print("No serial ports found!")
        return None
        
    print(f"Scanning {len(ports)} serial ports for Modbus devices...")
    
    # Try each port with default baudrate first
    for port in ports:
        print(f"Testing {port}...")
        if test_modbus_port(port, baudrate=9600):
            print(f"✓ Modbus device detected on {port} at 9600 baud")
            return port
            
    # If not found, try all baudrates
    for port in ports:
        for baudrate in baudrates:
            if baudrate == 9600:  # Already tested
                continue
                
            if test_modbus_port(port, baudrate=baudrate):
                print(f"✓ Modbus device detected on {port} at {baudrate} baud")
                return port
                
    print("No Modbus devices found!")
    return None


class ModbusClient:
    """Modbus RTU Client for USB-RS485 communication"""
    
    def __init__(self, 
                 port: Optional[str] = None,
                 baudrate: Optional[int] = None,
                 parity: str = 'N',
                 stopbits: int = 1,
                 bytesize: int = 8,
                 timeout: Optional[float] = None,
                 verbose: bool = False,
                 mock_client: Optional[Any] = None):
        """
        Initialize Modbus RTU client
        
        Args:
            port: Serial port (default: from .env MODBUS_PORT or /dev/ttyUSB0)
            baudrate: Communication speed (default: from .env MODBUS_BAUDRATE or 9600)
            parity: Parity bit ('N', 'E', 'O') (default: 'N')
            stopbits: Stop bits (default: 1)
            bytesize: Data bits (default: 8)
            timeout: Communication timeout in seconds (default: from .env MODBUS_TIMEOUT or 1.0)
            verbose: Enable verbose logging (default: False)
            mock_client: For testing purposes, allows injecting a mock client
        """
        # Configure logging level based on verbose flag
        if verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)  # Only show warnings and errors by default
            
        # Load configuration from .env file with fallbacks
        self.port = port or os.getenv('MODBUS_PORT', '/dev/ttyUSB0')
        self.baudrate = baudrate or int(os.getenv('MODBUS_BAUDRATE', '9600'))
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout or float(os.getenv('MODBUS_TIMEOUT', '1.0'))
        # Handle different environment variable names for device address
        self.unit_id = int(os.getenv('MODBUS_DEVICE_ADDRESS', os.getenv('MODBUS_UNIT_ID', '1')))
        # Add alias for unit to match test expectations
        self.unit = self.unit_id
        
        # For testing - store mock client if provided
        self.mock_client = mock_client
        self.client = None
        
        logger.info(f"Initializing Modbus RTU client on {self.port}")
        logger.info(f"Parameters: {self.baudrate} {self.parity} {self.bytesize} {self.stopbits}")
        logger.info(f"Configuration loaded from .env: port={self.port}, baudrate={self.baudrate}, timeout={self.timeout}")
        self.verbose = verbose
        
    def connect(self):
        """
        Connect to Modbus device
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # If a mock client was provided, use it directly
        if self.mock_client:
            self.client = self.mock_client
            # Don't call connect() on the mock_client as it's already set up in tests
            return True
            
        try:
            # Create a real ModbusSerialClient
            self.client = ModbusSerialClient(
                method='rtu',
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout
            )
            
            if not self.client.connect():
                logger.error(f"Failed to connect to {self.port}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to {self.port}: {e}")
            return False
            
    def is_connected(self):
        """
        Check if client is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.client is not None
            
    def disconnect(self):
        """Disconnect from Modbus device"""
        if self.client and hasattr(self.client, 'close'):
            self.client.close()
            self.client = None
            logger.info("Disconnected from Modbus device")
    
    def close(self):
        """Alias for disconnect() to match test expectations"""
        return self.disconnect()
            
    def read_coils(self, address: int, count: int, unit: int = None) -> Optional[List[bool]]:
        """
        Read coils (discrete outputs)
        
        Args:
            address: Starting address
            count: Number of coils to read
            unit: Slave unit ID (default: from configuration)
            
        Returns:
            List of boolean values or None if error
        """
        # Use provided unit or default to self.unit_id
        unit = unit if unit is not None else self.unit_id
        
        if not self.is_connected():
            logger.error("Client not connected")
            return None
            
        try:
            response = self.client.read_coils(address, count, unit=unit)
            
            if response and not getattr(response, 'isError', True):
                return response.bits
            else:
                logger.error(f"Error reading coils: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading coils: {e}")
            return None
            
    def read_discrete_inputs(self, address: int, count: int, unit: int = 1) -> Optional[List[bool]]:
        """
        Read discrete inputs
        
        Args:
            address: Starting address
            count: Number of inputs to read
            unit: Slave unit ID (default: 1)
            
        Returns:
            List of boolean values or None if error
        """
        if not self.is_connected():
            logger.error("Client not connected")
            return None
            
        try:
            response = self.client.read_discrete_inputs(address, count, unit=unit)
            
            if response and not getattr(response, 'isError', True):
                return response.bits
            else:
                logger.error(f"Error reading discrete inputs: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading discrete inputs: {e}")
            return None
            
    def read_holding_registers(self, address: int, count: int, unit: int = 1) -> Optional[List[int]]:
        """
        Read holding registers
        
        Args:
            address: Starting address
            count: Number of registers to read
            unit: Slave unit ID (default: 1)
            
        Returns:
            List of register values or None if error
        """
        if not self.is_connected():
            logger.error("Client not connected")
            return None
            
        try:
            response = self.client.read_holding_registers(address, count, unit=unit)
            
            if response and not getattr(response, 'isError', True):
                return response.registers
            else:
                logger.error(f"Error reading holding registers: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading holding registers: {e}")
            return None
            
    def read_input_registers(self, address: int, count: int, unit: int = 1) -> Optional[List[int]]:
        """
        Read input registers
        
        Args:
            address: Starting address
            count: Number of registers to read
            unit: Slave unit ID (default: 1)
            
        Returns:
            List of register values or None if error
        """
        if not self.is_connected():
            logger.error("Client not connected")
            return None
            
        try:
            response = self.client.read_input_registers(address, count, unit=unit)
            
            if response and not getattr(response, 'isError', True):
                return response.registers
            else:
                logger.error(f"Error reading input registers: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading input registers: {e}")
            return None
            
    def write_coil(self, address: int, value: bool, unit: int = None) -> bool:
        """
        Write single coil
        
        Args:
            address: Coil address
            value: Boolean value to write
            unit: Slave unit ID (default: from configuration)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.client.is_socket_open():
            if not self.connect():
                logger.error("Failed to connect to Modbus device")
                return False
        
        # Użyj unit_id z konfiguracji, jeśli nie podano innego
        unit_to_use = unit if unit is not None else self.unit_id
        
        try:
            result = self.client.write_coil(address, value, unit=unit_to_use)
            if result.isError():
                logger.error(f"Error writing coil: {result}")
                return False
            
            logger.info(f"Written coil at address {address}: {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing coil: {e}")
            return False
            
    def write_register(self, address: int, value: int, unit: int = 1) -> bool:
        """
        Write single holding register
        
        Args:
            address: Register address
            value: Value to write
            unit: Slave unit ID (default: 1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.client is None and not self.connect():
                logger.error("Failed to connect to Modbus device")
                return False
                
            response = self.client.write_register(address, value, unit=unit)
            if response.isError():
                logger.error(f"Error writing register: {response}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error writing register: {e}")
            return False
            
    def write_coils(self, address: int, values: List[bool], unit: int = 1) -> bool:
        """
        Write multiple coils
        
        Args:
            address: Starting address
            values: List of boolean values to write
            unit: Slave unit ID (default: 1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.client.write_coils(address, values, unit=unit)
            if result.isError():
                logger.error(f"Error writing coils: {result}")
                return False
                
            logger.info(f"Written {len(values)} coils starting at address {address}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing coils: {e}")
            return False
            
    def write_registers(self, address: int, values: List[int], unit: int = 1) -> bool:
        """
        Write multiple holding registers
        
        Args:
            address: Starting address
            values: List of values to write
            unit: Slave unit ID (default: 1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.client.write_registers(address, values, unit=unit)
            if result.isError():
                logger.error(f"Error writing registers: {result}")
                return False
                
            logger.info(f"Written {len(values)} registers starting at address {address}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing registers: {e}")
            return False
