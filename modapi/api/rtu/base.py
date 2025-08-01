"""
Base Modbus RTU Communication Module
Core implementation of ModbusRTU class with essential functionality
"""

import logging
import serial
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
    
    # Context manager methods
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
