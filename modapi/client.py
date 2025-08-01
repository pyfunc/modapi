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


def test_modbus_port(port: str, baudrate: int = 9600, timeout: float = 0.5, 
                   unit_id: int = None, debug: bool = False) -> bool:
    """
    Test if a serial port responds to Modbus communication
    
    Args:
        port: Serial port path
        baudrate: Communication speed
        timeout: Connection timeout in seconds
        unit_id: Specific unit ID to test (None to test common ones)
        debug: Enable detailed debug output
        
    Returns:
        Tuple of (success: bool, details: dict) with test results
    """
    def log(msg, level='debug'):
        if debug or level == 'info':
            print(f"[DEBUG] {msg}" if level == 'debug' else f"[INFO] {msg}")
            
    try:
        log(f"Testing Modbus on {port} at {baudrate} baud, timeout={timeout}s", 'info')
        
        # Configure client with minimal parameters for pymodbus 3.10.0
        client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=timeout,
            # Set the unit ID (slave ID) for the client
            unit=unit if unit is not None else 1
        )
        
        # Test connection
        if not client.connect():
            log(f"Failed to open serial port {port}", 'info')
            return False, {"error": "Failed to open serial port", "port": port}
            
        log(f"Successfully opened {port}")
        
        # Define test parameters
        test_addresses = [0, 1, 40001]  # Common starting addresses
        test_units = [unit_id] if unit_id is not None else [1, 2, 255, 0]  # Common unit IDs
        
        for unit in test_units:
            for address in test_addresses:
                # Test function code 1 (read coils)
                try:
                    log(f"Testing FC01 (read coils) - Unit: {unit}, Address: {address}")
                    result = client.read_coils(address, 1)
                    if not result.isError():
                        log(f"✓ Modbus device found (FC01) - Unit: {unit}, Address: {address}", 'info')
                        client.close()
                        return True, {
                            "port": port,
                            "baudrate": baudrate,
                            "unit_id": unit,
                            "function_code": 1,
                            "address": address
                        }
                except Exception as e:
                    log(f"Error with FC01 (unit {unit}, addr {address}): {str(e)}")
                
                # Test function code 3 (read holding registers)
                try:
                    log(f"Testing FC03 (read holding regs) - Unit: {unit}, Address: {address}")
                    result = client.read_holding_registers(address, 1)
                    if not result.isError():
                        log(f"✓ Modbus device found (FC03) - Unit: {unit}, Address: {address}", 'info')
                        client.close()
                        return True, {
                            "port": port,
                            "baudrate": baudrate,
                            "unit_id": unit,
                            "function_code": 3,
                            "address": address
                        }
                except Exception as e:
                    log(f"Error with FC03 (unit {unit}, addr {address}): {str(e)}")
                
                # Test function code 4 (read input registers)
                try:
                    log(f"Testing FC04 (read input regs) - Unit: {unit}, Address: {address}")
                    result = client.read_input_registers(address, 1)
                    if not result.isError():
                        log(f"✓ Modbus device found (FC04) - Unit: {unit}, Address: {address}", 'info')
                        client.close()
                        return True, {
                            "port": port,
                            "baudrate": baudrate,
                            "unit_id": unit,
                            "function_code": 4,
                            "address": address
                        }
                except Exception as e:
                    log(f"Error with FC04 (unit {unit}, addr {address}): {str(e)}")
        
        # If we get here, no device was found
        client.close()
        log(f"No Modbus device found on {port} after testing all combinations", 'info')
        return False, {
            "port": port,
            "baudrate": baudrate,
            "error": "No Modbus device found"
        }
        
    except Exception as e:
        error_msg = f"Error testing {port}: {str(e)}"
        log(error_msg, 'info')
        if 'client' in locals():
            try:
                client.close()
            except:
                pass
        return False, {
            "port": port,
            "baudrate": baudrate,
            "error": error_msg
        }


def auto_detect_modbus_port(baudrates: List[int] = None, debug: bool = False, unit_id: int = None) -> Optional[dict]:
    """
    Automatically detect which serial port has a working Modbus device
    
    Args:
        baudrates: List of baud rates to test (default: common rates)
        debug: Enable debug output
        
    Returns:
        Path to working Modbus port or None if not found
    """
    if baudrates is None:
        baudrates = [9600, 19200, 38400, 57600, 115200]
        
    print("Scanning for Modbus devices...")
    
    # Get available ports
    ports = find_serial_ports()
    if not ports:
        print("❌ No serial ports found!")
        return None
        
    print(f"🔍 Found {len(ports)} serial port(s): {', '.join(ports)}")
    print(f"🔧 Testing common baud rates: {', '.join(map(str, baudrates))}")
    
    # Try each port with all baudrates
    for port in ports:
        print(f"\n🔌 Testing port: {port}")
        
        for baudrate in baudrates:
            if debug:
                print(f"  ⚙️  Testing {baudrate} baud...")
            else:
                print(f"  ⚙️  {baudrate} baud...", end=" ")
            
            success, result = test_modbus_port(
                port=port,
                baudrate=baudrate,
                unit_id=unit_id,
                debug=debug
            )
            
            if success:
                print(f"✅ Device found! {result}")
                return result
            else:
                if debug:
                    print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
                else:
                    print("❌")
    
    print("\n❌ No Modbus devices found on any port with the tested configurations.")
    print("   Please check the following:")
    print("   1. Is the device properly connected?")
    print("   2. Is the device powered on?")
    print("   3. Are you using the correct cable?")
    print("   4. Does the device use a non-standard baud rate?")
    print("   5. Is the device using a different unit ID?")
    print("\n💡 Tip: Run with --debug for more detailed information")
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
        try:
            # If a mock client was provided, use it directly
            if self.mock_client:
                self.client = self.mock_client
                # Call connect on the mock client to ensure it's recorded for test assertions
                return self.client.connect()
            
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
        # Use provided unit or default to self.unit_id
        unit = unit if unit is not None else self.unit_id
        
        if not self.is_connected():
            logger.error("Client not connected")
            return False
            
        try:
            response = self.client.write_coil(address, value, unit=unit)
            
            # Handle different types of responses
            if response:
                # Check if response has isError method (real response) or isError attribute (mock)
                if hasattr(response, 'isError'):
                    if callable(response.isError):
                        return not response.isError()
                    else:
                        return not response.isError
                return True
            return False
            
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
        if not self.is_connected():
            logger.error("Client not connected")
            return False
            
        try:
            response = self.client.write_register(address, value, unit=unit)
            return response and not getattr(response, 'isError', True)
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
        if not self.is_connected():
            logger.error("Client not connected")
            return False
            
        try:
            response = self.client.write_coils(address, values, unit=unit)
            return response and not getattr(response, 'isError', True)
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
        if not self.is_connected():
            logger.error("Client not connected")
            return False
            
        try:
            response = self.client.write_registers(address, values, unit=unit)
            return response and not getattr(response, 'isError', True)
        except Exception as e:
            logger.error(f"Error writing registers: {e}")
            return False
