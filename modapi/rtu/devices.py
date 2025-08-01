"""
Device-Specific Modbus RTU Implementations
Specialized classes for Waveshare and other Modbus RTU devices
"""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple

from .base import ModbusRTU
from modapi.config import (
    READ_COILS, READ_DISCRETE_INPUTS,
    READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS,
    WRITE_SINGLE_COIL, WRITE_SINGLE_REGISTER,
    WRITE_MULTIPLE_COILS, WRITE_MULTIPLE_REGISTERS,
    MODE_NORMAL, MODE_LINKAGE, MODE_SINGLE, MODE_LOOP,
    TYPE_0_5V, TYPE_0_10V, TYPE_0_20MA, TYPE_4_20MA,
    DEFAULT_BAUDRATE
)
from .protocol import (
    build_read_request, build_write_single_coil_request,
    build_write_single_register_request, build_write_multiple_coils_request,
    build_write_multiple_registers_request, parse_read_coils_response,
    parse_read_registers_response
)

logger = logging.getLogger(__name__)

class WaveshareIO8CH(ModbusRTU):
    """
    Specialized class for Waveshare IO 8CH module
    
    Based on documentation from:
    http://www.waveshare.com/wiki/Modbus_RTU_IO_8CH
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = DEFAULT_BAUDRATE, timeout: float = 1.0):
        """Initialize Waveshare IO 8CH module connection"""
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        logger.info("Initialized Waveshare IO 8CH module interface")
    
    def read_output_status(self, unit_id: int = 1) -> Optional[List[bool]]:
        """
        Read status of all output channels
        
        Command: 01 01 00 00 00 08 3D CC
        
        Args:
            unit_id: Device unit ID
            
        Returns:
            Optional[List[bool]]: List of output states or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_COILS, 0x0000, 8)
        response = self._send_request(unit_id, FUNC_READ_COILS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        return parse_read_coils_response(response)
    
    def read_input_status(self, unit_id: int = 1) -> Optional[List[bool]]:
        """
        Read status of all input channels
        
        Command: 01 02 00 00 00 08 79 CC
        
        Args:
            unit_id: Device unit ID
            
        Returns:
            Optional[List[bool]]: List of input states or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_DISCRETE_INPUTS, 0x0000, 8)
        response = self._send_request(unit_id, FUNC_READ_DISCRETE_INPUTS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        return parse_read_coils_response(response)
    
    def control_output(self, channel: int, state: bool, unit_id: int = 1) -> bool:
        """
        Control single output channel
        
        Commands:
        - ON:  01 05 00 00 FF 00 8C 3A
        - OFF: 01 05 00 00 00 00 CD CA
        
        Args:
            channel: Output channel (0-7)
            state: True for ON, False for OFF
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= channel <= 7:
            logger.error(f"Invalid channel number: {channel}, must be 0-7")
            return False
        
        request = build_write_single_coil_request(unit_id, channel, state)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_COIL, request[2:-2], max_retries=3)
        
        return response is not None
    
    def control_all_outputs(self, state: bool, unit_id: int = 1) -> bool:
        """
        Control all output channels
        
        Commands:
        - All ON:  01 05 00 FF FF 00 BC 0A
        - All OFF: 01 05 00 FF 00 00 FD FA
        
        Args:
            state: True for all ON, False for all OFF
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        # Special address 0xFF for all channels
        request = build_write_single_coil_request(unit_id, 0xFF, state)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_COIL, request[2:-2], max_retries=3)
        
        return response is not None
    
    def toggle_output(self, channel: int, unit_id: int = 1) -> bool:
        """
        Toggle output channel state
        
        Command: 01 05 00 00 55 00 F2 9A
        
        Args:
            channel: Output channel (0-7)
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= channel <= 7:
            logger.error(f"Invalid channel number: {channel}, must be 0-7")
            return False
        
        # For toggle, use value 0x5500 instead of 0xFF00 or 0x0000
        request = build_request(unit_id, FUNC_WRITE_SINGLE_COIL, 
                               bytes([0x00, channel, 0x55, 0x00]))
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_COIL, request[2:-2], max_retries=3)
        
        return response is not None
    
    def flash_output(self, channel: int, on_time_100ms: int, unit_id: int = 1) -> bool:
        """
        Set output channel to flash ON/OFF
        
        Command: 01 05 02 00 00 07 8D B0 (700ms)
        
        Args:
            channel: Output channel (0-7)
            on_time_100ms: ON time in 100ms units (1-255)
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= channel <= 7:
            logger.error(f"Invalid channel number: {channel}, must be 0-7")
            return False
        
        if not 1 <= on_time_100ms <= 255:
            logger.error(f"Invalid ON time: {on_time_100ms}, must be 1-255")
            return False
        
        # Special register 0x0200 for flash ON
        request = build_request(unit_id, FUNC_WRITE_SINGLE_COIL, 
                               bytes([0x02, channel, 0x00, on_time_100ms]))
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_COIL, request[2:-2], max_retries=3)
        
        return response is not None
    
    def set_output_mode(self, channel: int, mode: int, unit_id: int = 1) -> bool:
        """
        Set output channel control mode
        
        Command: 01 06 10 00 00 01 4C CA (Linkage mode)
        
        Args:
            channel: Output channel (0-7)
            mode: Control mode (0=Normal, 1=Linkage, 2=Toggle, 3=Edge)
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= channel <= 7:
            logger.error(f"Invalid channel number: {channel}, must be 0-7")
            return False
        
        if not 0 <= mode <= 3:
            logger.error(f"Invalid mode: {mode}, must be 0-3")
            return False
        
        # Special register 0x1000 + channel for mode setting
        request = build_write_single_register_request(unit_id, 0x1000 + channel, mode)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
        return response is not None
    
    def read_output_modes(self, unit_id: int = 1) -> Optional[List[int]]:
        """
        Read output channel control modes
        
        Command: 01 03 10 00 00 08 40 CC
        
        Args:
            unit_id: Device unit ID
            
        Returns:
            Optional[List[int]]: List of mode values or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_HOLDING_REGISTERS, 0x1000, 8)
        response = self._send_request(unit_id, FUNC_READ_HOLDING_REGISTERS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        return parse_read_registers_response(response)
    
    def set_baudrate(self, baudrate: int, unit_id: int = 0) -> bool:
        """
        Set device baudrate
        
        Command: 00 06 20 00 00 05 43 D8 (115200)
        
        Args:
            baudrate: Baudrate (0=4800, 1=57600, 5=115200)
            unit_id: Device unit ID (usually 0 for config)
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        # Convert common baudrates to Waveshare codes
        baudrate_code = {
            4800: 0,
            57600: 1,
            115200: 5
        }.get(baudrate, baudrate)  # Use direct value if not in mapping
        
        request = build_write_single_register_request(unit_id, 0x2000, baudrate_code)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
        success = response is not None
        if success:
            # Update local baudrate setting if successful
            self.baudrate = baudrate
            if self.is_connected():
                self.disconnect()
                time.sleep(0.5)  # Allow device to change baudrate
                self.connect()
        
        return success


class WaveshareAnalogInput8CH(ModbusRTU):
    """
    Specialized class for Waveshare Analog Input 8CH module
    
    Based on documentation from:
    https://www.waveshare.com/wiki/Modbus_RTU_Analog_Input_8CH
    """
    
    # Analog input types are loaded from config
    # These will be added to constants.json in the next update
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 57600, timeout: float = 1.0):
        """Initialize Waveshare Analog Input 8CH module connection"""
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        logger.info("Initialized Waveshare Analog Input 8CH module interface")
    
    def read_analog_inputs(self, unit_id: int = 1) -> Optional[List[int]]:
        """
        Read all analog input values
        
        Command: 01 04 00 00 00 08 F1 CC
        
        Args:
            unit_id: Device unit ID
            
        Returns:
            Optional[List[int]]: List of analog values or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_INPUT_REGISTERS, 0x0000, 8)
        response = self._send_request(unit_id, FUNC_READ_INPUT_REGISTERS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        return parse_read_registers_response(response)
    
    def read_channel_types(self, unit_id: int = 1) -> Optional[List[int]]:
        """
        Read analog input channel types
        
        Command: 01 03 10 00 00 08 40 CC
        
        Args:
            unit_id: Device unit ID
            
        Returns:
            Optional[List[int]]: List of channel types or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_HOLDING_REGISTERS, 0x1000, 8)
        response = self._send_request(unit_id, FUNC_READ_HOLDING_REGISTERS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        return parse_read_registers_response(response)
    
    def set_channel_type(self, channel: int, input_type: int, unit_id: int = 1) -> bool:
        """
        Set analog input channel type
        
        Command: 01 06 10 00 00 03 CD 0B (4-20mA)
        
        Args:
            channel: Channel number (0-7)
            input_type: Input type (0=0-5V, 1=0-10V, 2=0-20mA, 3=4-20mA)
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= channel <= 7:
            logger.error(f"Invalid channel number: {channel}, must be 0-7")
            return False
        
        if not 0 <= input_type <= 3:
            logger.error(f"Invalid input type: {input_type}, must be 0-3")
            return False
        
        request = build_write_single_register_request(unit_id, 0x1000 + channel, input_type)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
        return response is not None
    
    def set_all_channel_types(self, input_type: int, unit_id: int = 1) -> bool:
        """
        Set all analog input channel types to the same type
        
        Args:
            input_type: Input type (0=0-5V, 1=0-10V, 2=0-20mA, 3=4-20mA)
            unit_id: Device unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 0 <= input_type <= 3:
            logger.error(f"Invalid input type: {input_type}, must be 0-3")
            return False
        
        # Set all 8 channels to the same type
        values = [input_type] * 8
        request = build_write_multiple_registers_request(unit_id, 0x1000, values)
        response = self._send_request(unit_id, FUNC_WRITE_MULTIPLE_REGISTERS, request[2:-2], max_retries=3)
        
        return response is not None
    
    def set_baudrate(self, baudrate: int, unit_id: int = 0) -> bool:
        """
        Set device baudrate
        
        Command: 00 06 20 00 00 05 43 D8 (115200)
        
        Args:
            baudrate: Baudrate (0=4800, 1=57600, 5=115200)
            unit_id: Device unit ID (usually 0 for config)
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        # Convert common baudrates to Waveshare codes
        baudrate_code = {
            4800: 0,
            57600: 1,
            19200: 2,
            38400: 3,
            57600: 4,
            115200: 5
        }.get(baudrate, baudrate)  # Use direct value if not in mapping
        
        request = build_write_single_register_request(unit_id, 0x2000, baudrate_code)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
        success = response is not None
        if success:
            # Update local baudrate setting if successful
            self.baudrate = baudrate
            if self.is_connected():
                self.disconnect()
                time.sleep(0.5)  # Allow device to change baudrate
                self.connect()
        
        return success
    
    def set_device_address(self, address: int, unit_id: int = 0) -> bool:
        """
        Set device address (unit ID)
        
        Command: 00 06 40 00 00 01 5C 1B (address 1)
        
        Args:
            address: New device address (1-247)
            unit_id: Current device unit ID (usually 0 for config)
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        if not 1 <= address <= 247:
            logger.error(f"Invalid device address: {address}, must be 1-247")
            return False
        
        request = build_write_single_register_request(unit_id, 0x4000, address)
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
        return response is not None
    
    def read_device_address(self, unit_id: int = 0) -> Optional[int]:
        """
        Read device address (unit ID)
        
        Command: 00 03 40 00 00 01 90 1B
        
        Args:
            unit_id: Current device unit ID (usually 0 for broadcast)
            
        Returns:
            Optional[int]: Device address or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_HOLDING_REGISTERS, 0x4000, 1)
        response = self._send_request(unit_id, FUNC_READ_HOLDING_REGISTERS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        registers = parse_read_registers_response(response)
        if registers and len(registers) > 0:
            return registers[0]
        
        return None
    
    def read_software_version(self, unit_id: int = 0) -> Optional[str]:
        """
        Read device software version
        
        Command: 00 03 80 00 00 01 AC 1B
        
        Args:
            unit_id: Device unit ID (usually 0 for broadcast)
            
        Returns:
            Optional[str]: Software version or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_HOLDING_REGISTERS, 0x8000, 1)
        response = self._send_request(unit_id, FUNC_READ_HOLDING_REGISTERS, request[2:-2], max_retries=3)
        
        if response is None:
            return None
        
        registers = parse_read_registers_response(response)
        if registers and len(registers) > 0:
            version_code = registers[0]
            major = version_code // 100
            minor = version_code % 100
            return f"V{major}.{minor:02d}"
        
        return None
