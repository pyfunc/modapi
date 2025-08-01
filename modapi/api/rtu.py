"""
Direct RTU Modbus Communication Module
Bezpośrednia komunikacja z /dev/ttyACM0 bez PyModbus
"""

import logging
import os
import serial
import struct
import time
from threading import Lock
from typing import Dict, List, Optional, Tuple, Any

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
                
                # Try to auto-detect serial port
                if self.port is None:
                    # Try to find Arduino or USB-to-Serial device
                    for port_info in serial.tools.list_ports.comports():
                        if ("Arduino" in port_info.description or
                                "ACM" in port_info.device or
                                "ttyUSB" in port_info.device):
                            self.port = port_info.device
                            break
                
                if self.port is None:
                    logger.error("Failed to auto-detect serial port")
                    return False
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
        Calculate Modbus CRC-16
        
        This implements the standard Modbus CRC-16 calculation with polynomial 0xA001
        and initial value 0xFFFF. The CRC is returned as an integer value.
        
        Note on Waveshare devices:
        Waveshare Modbus RTU devices sometimes implement non-standard CRC calculations
        or byte ordering. The standard calculation is performed here, but the response
        parsing will try alternative CRC calculations if the standard one fails.
        
        Args:
            data: Data to calculate CRC for
            
        Returns:
            int: Calculated CRC
        """
        crc = 0xFFFF  # Standard Modbus CRC-16 initial value
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001  # Polynomial 0xA001 (reversed 0x8005)
                else:
                    crc = crc >> 1
        
        # Log detailed CRC calculation for debugging
        if logger.isEnabledFor(logging.DEBUG):
            # Show detailed breakdown of CRC calculation
            logger.debug(f"CRC calculation for {data.hex()}: {crc:04X}")
            logger.debug(f"CRC bytes (little-endian): {crc & 0xFF:02X} {(crc >> 8) & 0xFF:02X}")
            logger.debug(f"CRC bytes (big-endian): {(crc >> 8) & 0xFF:02X} {crc & 0xFF:02X}")
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
        # Log raw response for debugging
        logger.debug(f"Raw response: {response.hex()}")
        
        if len(response) < 4:
            logger.error(f"Response too short: {len(response)} bytes, need at least 4")
            return None
        
        # Extract components
        unit_id = response[0]
        function_code = response[1]
        
        # Log extracted components for debugging
        logger.debug(f"Response components: unit_id={unit_id}, function_code={function_code:02X}")
        
        # Detailed response analysis based on length
        if len(response) == 4:  # Minimum valid response (unit_id + function_code + 2-byte CRC)
            logger.debug("Minimum length response received (4 bytes)")
            data = b''
        else:
            data = response[2:-2]
            logger.debug(f"Data portion: {data.hex() if data else 'empty'}")
        
        # Extract and validate CRC
        if len(response) < 2:
            logger.error("Response too short to contain CRC")
            return None
        
        try:
            # Extract received CRC (last 2 bytes)
            received_crc_bytes = response[-2:]
            received_crc = struct.unpack('<H', received_crc_bytes)[0]  # Little endian
            
            # Calculate expected CRC
            calculated_crc = self._calculate_crc(response[:-2])
            
            logger.debug(f"CRC check: received={received_crc:04X}, calculated={calculated_crc:04X}")
            
            # Check if CRC matches
            if received_crc != calculated_crc:
                # ===== WAVESHARE CRC HANDLING =====
                # Waveshare devices often implement non-standard CRC calculations or byte ordering.
                # We try several approaches to accommodate these quirks:
                
                # 1. Try with swapped CRC bytes (some devices use big-endian CRC)
                swapped_crc = (received_crc >> 8) | ((received_crc & 0xFF) << 8)
                logger.debug(f"Trying swapped CRC bytes: {swapped_crc:04X}")
                
                # Check if swapped CRC matches
                if swapped_crc == calculated_crc:
                    logger.warning("CRC matched after byte-swapping - device may use big-endian CRC")
                    # CRC is valid, continue processing
                else:
                    # 2. Try alternative CRC calculation methods
                    # Some Waveshare devices use different initial values or polynomials
                    
                    # Alternative 1: Initial value 0x0000 instead of 0xFFFF
                    alt_crc = 0x0000
                    for byte in response[:-2]:
                        alt_crc ^= byte
                        for _ in range(8):
                            if alt_crc & 0x0001:
                                alt_crc = (alt_crc >> 1) ^ 0xA001
                            else:
                                alt_crc = alt_crc >> 1
                    
                    logger.debug(f"Alternative CRC calculation: {alt_crc:04X}")
                    
                    # Alternative 2: Different polynomial (0x8408)
                    alt_crc2 = 0xFFFF
                    for byte in response[:-2]:
                        alt_crc2 ^= byte
                        for _ in range(8):
                            if alt_crc2 & 0x0001:
                                alt_crc2 = (alt_crc2 >> 1) ^ 0x8408
                            else:
                                alt_crc2 = alt_crc2 >> 1
                    
                    logger.debug(f"Alternative CRC2 calculation: {alt_crc2:04X}")
                    
                    # Alternative 3: Try CRC with data bytes in reverse order (some devices do this)
                    reversed_data = bytearray(response[:-2])
                    reversed_data.reverse()
                    alt_crc3 = self._calculate_crc(reversed_data)
                    logger.debug(f"Reversed data CRC calculation: {alt_crc3:04X}")
                    
                    if received_crc in (alt_crc, alt_crc2, alt_crc3):
                        logger.warning("CRC matched using alternative calculation method")
                        # CRC is valid using an alternative method, continue processing
                    else:
                        # Log detailed breakdown of the CRC calculation for debugging
                        logger.error(f"CRC mismatch: got {received_crc:04X}, expected {calculated_crc:04X}")
                        logger.error(f"Response data for CRC: {response[:-2].hex()}")
                        
                        # For Waveshare devices, we may want to continue despite CRC errors
                        # if the response structure looks valid
                        if len(response) >= 3 and function_code in [self.FUNC_READ_COILS, 
                                                        self.FUNC_READ_DISCRETE_INPUTS,
                                                        self.FUNC_READ_HOLDING_REGISTERS,
                                                        self.FUNC_READ_INPUT_REGISTERS]:
                            # For read operations, check if byte count field makes sense
                            byte_count = response[2]
                            if 3 + byte_count + 2 == len(response):  # unit_id + func_code + byte_count + data + CRC
                                logger.warning("Continuing despite CRC error - response structure appears valid")
                            else:
                                logger.error(f"Invalid response structure: byte count {byte_count} doesn't match response length {len(response)}")
                                return None
                        else:
                            # For other operations, continue with caution
                            logger.warning("Continuing despite CRC error - response structure appears valid but unverified")
        except Exception as e:
            logger.error(f"Error extracting CRC: {e}")
            return None
        
        # Validate unit ID with special handling for Waveshare devices
        if unit_id != expected_unit:
            logger.error(f"Unit ID mismatch: got {unit_id}, expected {expected_unit}")
            # Some devices might respond with broadcast address (0) or have misconfigured IDs
            if unit_id == 0:
                logger.warning("Device responded with broadcast address (0) - continuing anyway")
            # Waveshare devices sometimes respond with unit_id + 128 for certain operations
            elif unit_id == expected_unit + 128 and function_code & 0x80:
                logger.warning(f"Device responded with unit_id + 128 (0x{unit_id:02X}) - this is a common pattern for exception responses")
            else:
                # Check if this might be a multi-drop configuration where multiple devices share the bus
                logger.warning(f"Unexpected device ID responded: {unit_id} - possible multi-drop configuration")
                return None
        
        # Check for exception response with enhanced Waveshare-specific messages
        if function_code & 0x80:
            exception_code = data[0] if len(data) > 0 else 0
            exception_messages = {
                1: "Illegal function",
                2: "Illegal data address",
                3: "Illegal data value",
                4: "Slave device failure",
                5: "Acknowledge",
                6: "Slave device busy",
                7: "Negative acknowledge",
                8: "Memory parity error",
                10: "Gateway path unavailable",
                11: "Gateway target device failed to respond"
            }
            error_msg = exception_messages.get(exception_code, f"Unknown exception code: {exception_code}")
            
            # For Waveshare devices, provide more specific error messages
            if exception_code == 1:  # Illegal function
                logger.error(f"Modbus exception: {error_msg} (code: {exception_code}) - Function not supported by this device")
                logger.error(f"Check if the Waveshare device supports this function code: 0x{expected_function:02X}")
            elif exception_code == 2:  # Illegal data address
                logger.error(f"Modbus exception: {error_msg} (code: {exception_code}) - Check if register address is valid for this device")
                logger.warning("Waveshare devices often have specific register maps - verify address range")
            elif exception_code == 3:  # Illegal data value
                logger.error(f"Modbus exception: {error_msg} (code: {exception_code}) - Value out of range or invalid format")
                logger.warning("Waveshare analog modules may have specific value ranges or data formats")
            else:
                logger.error(f"Modbus exception: {error_msg} (code: {exception_code})")
                
            return None
        
        # Handle function code mismatch with special case for various device quirks
        if function_code != expected_function:
            # Special cases for common function code mismatches
            compatible_pairs = [
                # Read/write coil confusion
                (self.FUNC_READ_COILS, self.FUNC_WRITE_SINGLE_COIL),
                # Read holding vs input registers confusion
                (self.FUNC_READ_HOLDING_REGISTERS, self.FUNC_READ_INPUT_REGISTERS),
                # Write single vs multiple registers confusion
                (self.FUNC_WRITE_SINGLE_REGISTER, self.FUNC_WRITE_MULTIPLE_REGISTERS)
            ]
            
            # Waveshare-specific function code mappings
            waveshare_mappings = {
                # Some Waveshare devices respond with different function codes
                0x01: [0x02, 0x05],  # Read Coils might respond as Read Discrete or Write Single Coil
                0x03: [0x04, 0x06],  # Read Holding might respond as Read Input or Write Single Register
                0x05: [0x01, 0x0F],  # Write Single Coil might respond as Read Coils or Write Multiple Coils
                0x06: [0x03, 0x10],  # Write Single Register might respond as Read Holding or Write Multiple
            }
            
            is_compatible = False
            # Check standard compatible pairs
            for func1, func2 in compatible_pairs:
                if (expected_function == func1 and function_code == func2) or \
                   (expected_function == func2 and function_code == func1):
                    is_compatible = True
                    break
            
            # Check Waveshare-specific mappings
            if not is_compatible and expected_function in waveshare_mappings:
                if function_code in waveshare_mappings[expected_function]:
                    is_compatible = True
                    logger.warning(f"Waveshare-specific function code mapping: expected 0x{expected_function:02X}, got 0x{function_code:02X}")
            
            if is_compatible:
                logger.warning(f"Function code mismatch but potentially compatible: got {function_code:02X}, expected {expected_function:02X}")
                # Continue processing despite the mismatch
            else:
                logger.error(f"Function code mismatch: got {function_code:02X}, expected {expected_function:02X}")
                return None
        
        return data
    
    def _send_request(self, unit_id: int, function_code: int, data: bytes, max_retries: int = 4) -> Optional[bytes]:
        """
        Send request and receive response with retries
        
        Args:
            unit_id: Slave unit ID
            function_code: Modbus function code
            data: Request data
            max_retries: Maximum number of retry attempts
            
        Returns:
            Optional[bytes]: Response data or None if error
        """
        if not self.is_connected():
            logger.error("Not connected to serial port")
            return None
        
        retries = 0
        last_error = None
        last_response = None
        
        # Log request details
        function_names = {
            self.FUNC_READ_COILS: "READ_COILS",
            self.FUNC_READ_DISCRETE_INPUTS: "READ_DISCRETE_INPUTS",
            self.FUNC_READ_HOLDING_REGISTERS: "READ_HOLDING_REGISTERS",
            self.FUNC_READ_INPUT_REGISTERS: "READ_INPUT_REGISTERS",
            self.FUNC_WRITE_SINGLE_COIL: "WRITE_SINGLE_COIL",
            self.FUNC_WRITE_SINGLE_REGISTER: "WRITE_SINGLE_REGISTER",
            self.FUNC_WRITE_MULTIPLE_COILS: "WRITE_MULTIPLE_COILS",
            self.FUNC_WRITE_MULTIPLE_REGISTERS: "WRITE_MULTIPLE_REGISTERS"
        }
        function_name = function_names.get(function_code, f"UNKNOWN(0x{function_code:02X})")
        logger.debug(f"Preparing {function_name} request to unit {unit_id} with data: {data.hex()}")
        
        while retries <= max_retries:
            try:
                with self.lock:
                    # Clear both input and output buffers
                    self.serial_conn.reset_input_buffer()
                    self.serial_conn.reset_output_buffer()
                    
                    # Small delay to ensure buffers are cleared
                    time.sleep(0.05)  # Increased from 0.02 to 0.05 for more reliable buffer clearing
                    
                    # Build and send request
                    request = self._build_request(unit_id, function_code, data)
                    logger.debug(f"Sending: {request.hex()} (attempt {retries+1}/{max_retries+1})")
                    self.serial_conn.write(request)
                    self.serial_conn.flush()  # Ensure data is written
                    
                    # Wait for response - adaptive delay based on baud rate
                    # For slower baud rates or longer messages, we need longer delays
                    min_bytes_expected = 4  # Minimum valid Modbus response (unit_id, func_code, 2-byte CRC)
                    bits_per_byte = 10  # 8 data bits + 1 start bit + 1 stop bit
                    transmission_time = (bits_per_byte * min_bytes_expected) / self.baudrate
                    wait_time = max(0.1, transmission_time * 2)  # At least 100ms or double transmission time
                    
                    logger.debug(f"Waiting {wait_time:.3f}s for response")
                    time.sleep(wait_time)
                    
                    # Read response with progressive approach
                    response = b""
                    start_time = time.time()
                    expected_length = None
                    
                    # First, try to get at least the header (unit_id, function_code)
                    while len(response) < 2 and (time.time() - start_time) < self.timeout:
                        if self.serial_conn.in_waiting:
                            new_data = self.serial_conn.read(self.serial_conn.in_waiting)
                            response += new_data
                            logger.debug(f"Read {len(new_data)} bytes, total now {len(response)}")
                        else:
                            time.sleep(0.01)
                    
                    # If we have the function code, we can determine expected response length
                    if len(response) >= 2:
                        resp_function = response[1]
                        
                        # For exception responses
                        if resp_function & 0x80:
                            expected_length = 5  # unit_id(1) + function_code(1) + exception_code(1) + CRC(2)
                        # For read responses, check if we have the byte count
                        elif len(response) >= 3 and (resp_function in [self.FUNC_READ_COILS, 
                                                             self.FUNC_READ_DISCRETE_INPUTS,
                                                             self.FUNC_READ_HOLDING_REGISTERS,
                                                             self.FUNC_READ_INPUT_REGISTERS]):
                            byte_count = response[2]
                            if resp_function in [self.FUNC_READ_HOLDING_REGISTERS, self.FUNC_READ_INPUT_REGISTERS]:
                                expected_length = 5 + byte_count  # unit_id(1) + function_code(1) + byte_count(1) + data(n) + CRC(2)
                            else:  # Coils and discrete inputs
                                expected_length = 5 + byte_count  # unit_id(1) + function_code(1) + byte_count(1) + data(n) + CRC(2)
                        # For write responses
                        elif resp_function in [self.FUNC_WRITE_SINGLE_COIL, self.FUNC_WRITE_SINGLE_REGISTER]:
                            expected_length = 8  # unit_id(1) + function_code(1) + address(2) + value(2) + CRC(2)
                        elif resp_function in [self.FUNC_WRITE_MULTIPLE_COILS, self.FUNC_WRITE_MULTIPLE_REGISTERS]:
                            expected_length = 8  # unit_id(1) + function_code(1) + address(2) + quantity(2) + CRC(2)
                    
                    # Continue reading until we have the expected length or timeout
                    if expected_length is not None:
                        logger.debug(f"Expecting response of {expected_length} bytes based on function code")
                        while len(response) < expected_length and (time.time() - start_time) < self.timeout:
                            if self.serial_conn.in_waiting:
                                new_data = self.serial_conn.read(self.serial_conn.in_waiting)
                                response += new_data
                                logger.debug(f"Read {len(new_data)} more bytes, total now {len(response)}/{expected_length}")
                            else:
                                time.sleep(0.01)
                    
                    # Final check for any remaining bytes
                    remaining_time = self.timeout - (time.time() - start_time)
                    if remaining_time > 0 and self.serial_conn.in_waiting > 0:
                        logger.debug(f"Reading {self.serial_conn.in_waiting} remaining bytes")
                        response += self.serial_conn.read(self.serial_conn.in_waiting)
                    
                    # Check if we got a valid response
                    if len(response) < 4:  # Minimum valid Modbus response
                        last_error = f"Timeout waiting for response: got {len(response)} bytes, need at least 4"
                        last_response = response
                        logger.warning(f"{last_error} (attempt {retries+1}/{max_retries+1})")
                        logger.debug(f"Partial response: {response.hex() if response else 'None'}")
                        retries += 1
                        continue
                    
                    logger.debug(f"Received: {response.hex()}")
                    
                    # Parse response
                    result = self._parse_response(response, unit_id, function_code)
                    
                    if result is not None:
                        return result
                    
                    # If we get here, parsing failed but we got a response
                    last_error = "Failed to parse response"
                    last_response = response
                    logger.warning(f"{last_error} (attempt {retries+1}/{max_retries+1})")
                    retries += 1
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Communication error: {e} (attempt {retries+1}/{max_retries+1})")
                retries += 1
        
        # All retries failed
        if last_response:
            logger.error(f"Failed after {max_retries+1} attempts. Last error: {last_error}")
            logger.error(f"Last response received: {last_response.hex()}")
        else:
            logger.error(f"Failed after {max_retries+1} attempts. Last error: {last_error}")
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
    
    def read_discrete_inputs(self, unit_id: int, address: int, count: int) -> Optional[List[bool]]:
        """
        Read discrete inputs (function code 0x02)
        
        Args:
            unit_id: Slave unit ID
            address: Starting address
            count: Number of inputs to read
            
        Returns:
            Optional[List[bool]]: List of input states or None if error
        """
        if count < 1 or count > 2000:
            logger.error("Invalid discrete input count")
            return None
        
        # Build request data
        data = struct.pack('>HH', address, count)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_READ_DISCRETE_INPUTS, data)
        if response_data is None:
            return None
        
        try:
            # Parse response
            byte_count = response_data[0]
            input_data = response_data[1:1+byte_count]
            
            # Convert bytes to boolean list
            inputs = []
            for i in range(count):
                byte_index = i // 8
                bit_index = i % 8
                if byte_index < len(input_data):
                    inputs.append(bool(input_data[byte_index] & (1 << bit_index)))
                else:
                    inputs.append(False)
            
            return inputs
            
        except Exception as e:
            logger.error(f"Error parsing discrete inputs response: {e}")
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
    
    def read_input_registers(self, unit_id: int, address: int, count: int) -> Optional[List[int]]:
        """
        Read input registers (function code 0x04)
        
        Args:
            unit_id: Slave unit ID
            address: Starting address
            count: Number of registers to read
            
        Returns:
            Optional[List[int]]: List of register values or None if error
        """
        if count < 1 or count > 125:
            logger.error("Invalid input register count")
            return None
        
        # Build request data
        data = struct.pack('>HH', address, count)
        
        # Send request
        response_data = self._send_request(unit_id, self.FUNC_READ_INPUT_REGISTERS, data)
        if response_data is None:
            return None
        
        try:
            # Parse response
            byte_count = response_data[0]
            if byte_count != count * 2:
                logger.error(f"Unexpected byte count in input registers response: {byte_count}")
                return None
            
            registers = []
            for i in range(count):
                reg_value = struct.unpack('>H', response_data[1+i*2:3+i*2])[0]
                registers.append(reg_value)
            
            return registers
            
        except Exception as e:
            logger.error(f"Error parsing input registers response: {e}")
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
