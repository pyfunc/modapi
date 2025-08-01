"""
Modbus Device State Module
Maintains virtual representation of Modbus device states
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ModbusDeviceState:
    """
    Virtual representation of a Modbus device's state
    Stores coil states, register values, and communication metadata
    """
    # Device identification
    unit_id: int
    port: str
    baudrate: int
    
    # Last successful communication timestamp
    last_updated: float = field(default_factory=time.time)
    
    # State storage
    coils: Dict[int, bool] = field(default_factory=dict)
    discrete_inputs: Dict[int, bool] = field(default_factory=dict)
    holding_registers: Dict[int, int] = field(default_factory=dict)
    input_registers: Dict[int, int] = field(default_factory=dict)
    
    # Communication statistics
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    crc_error_count: int = 0
    
    # Last error information
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    
    def update_coil(self, address: int, value: bool) -> None:
        """Update coil state"""
        self.coils[address] = value
        self._update_timestamp()
        
    def update_coils(self, start_address: int, values: List[bool]) -> None:
        """Update multiple coils starting from start_address"""
        for i, value in enumerate(values):
            self.coils[start_address + i] = value
        self._update_timestamp()
        
    def update_discrete_input(self, address: int, value: bool) -> None:
        """Update discrete input state"""
        self.discrete_inputs[address] = value
        self._update_timestamp()
        
    def update_discrete_inputs(self, start_address: int, values: List[bool]) -> None:
        """Update multiple discrete inputs starting from start_address"""
        for i, value in enumerate(values):
            self.discrete_inputs[start_address + i] = value
        self._update_timestamp()
        
    def update_holding_register(self, address: int, value: int) -> None:
        """Update holding register value"""
        self.holding_registers[address] = value
        self._update_timestamp()
        
    def update_holding_registers(self, start_address: int, values: List[int]) -> None:
        """Update multiple holding registers starting from start_address"""
        for i, value in enumerate(values):
            self.holding_registers[start_address + i] = value
        self._update_timestamp()
        
    def update_input_register(self, address: int, value: int) -> None:
        """Update input register value"""
        self.input_registers[address] = value
        self._update_timestamp()
        
    def update_input_registers(self, start_address: int, values: List[int]) -> None:
        """Update multiple input registers starting from start_address"""
        for i, value in enumerate(values):
            self.input_registers[start_address + i] = value
        self._update_timestamp()
    
    def record_request(self) -> None:
        """Record a request attempt"""
        self.request_count += 1
    
    def record_success(self) -> None:
        """Record a successful request"""
        self.success_count += 1
        self._update_timestamp()
    
    def record_error(self, error_message: str) -> None:
        """Record a communication error"""
        self.error_count += 1
        self.last_error = error_message
        self.last_error_time = time.time()
    
    def record_timeout(self) -> None:
        """Record a timeout error"""
        self.timeout_count += 1
        self.record_error("Communication timeout")
    
    def record_crc_error(self) -> None:
        """Record a CRC validation error"""
        self.crc_error_count += 1
        self.record_error("CRC validation failed")
    
    def _update_timestamp(self) -> None:
        """Update the last_updated timestamp"""
        self.last_updated = time.time()
    
    def get_age(self) -> float:
        """Get age of the state in seconds"""
        return time.time() - self.last_updated
    
    def is_stale(self, max_age_seconds: float = 60.0) -> bool:
        """Check if the state is stale (no recent updates)"""
        return self.get_age() > max_age_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert timestamp to human-readable format
        data['last_updated_iso'] = datetime.fromtimestamp(data['last_updated']).isoformat()
        if data['last_error_time']:
            data['last_error_time_iso'] = datetime.fromtimestamp(data['last_error_time']).isoformat()
        return data
    
    def to_json(self, pretty: bool = True) -> str:
        """Convert to JSON string"""
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent)
    
    def dump_to_file(self, filename: str) -> None:
        """Save state to a JSON file"""
        try:
            with open(filename, 'w') as f:
                f.write(self.to_json())
            logger.info(f"Device state saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save device state to {filename}: {e}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModbusDeviceState':
        """Create instance from dictionary"""
        # Remove non-constructor fields
        if 'last_updated_iso' in data:
            del data['last_updated_iso']
        if 'last_error_time_iso' in data:
            del data['last_error_time_iso']
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModbusDeviceState':
        """Create instance from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def load_from_file(cls, filename: str) -> Optional['ModbusDeviceState']:
        """Load state from a JSON file"""
        try:
            with open(filename, 'r') as f:
                return cls.from_json(f.read())
        except Exception as e:
            logger.error(f"Failed to load device state from {filename}: {e}")
            return None


class ModbusDeviceStateManager:
    """
    Manages multiple Modbus device states
    """
    def __init__(self):
        self.devices: Dict[str, ModbusDeviceState] = {}
    
    def get_device_key(self, port: str, unit_id: int) -> str:
        """Generate a unique key for a device"""
        return f"{port}_{unit_id}"
    
    def add_device(self, device: ModbusDeviceState) -> None:
        """Add or update a device state"""
        key = self.get_device_key(device.port, device.unit_id)
        self.devices[key] = device
        logger.info(f"Added device state for unit {device.unit_id} on {device.port}")
    
    def get_device(self, port: str, unit_id: int) -> Optional[ModbusDeviceState]:
        """Get a device state by port and unit ID"""
        key = self.get_device_key(port, unit_id)
        return self.devices.get(key)
    
    def remove_device(self, port: str, unit_id: int) -> bool:
        """Remove a device state"""
        key = self.get_device_key(port, unit_id)
        if key in self.devices:
            del self.devices[key]
            logger.info(f"Removed device state for unit {unit_id} on {port}")
            return True
        return False
    
    def get_all_devices(self) -> List[ModbusDeviceState]:
        """Get all device states"""
        return list(self.devices.values())
    
    def dump_all_devices(self, directory: str) -> None:
        """Save all device states to files"""
        import os
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for key, device in self.devices.items():
            filename = f"{directory}/device_{device.port.replace('/', '_')}_{device.unit_id}_{timestamp}.json"
            device.dump_to_file(filename)
    
    def dump_device(self, port: str, unit_id: int, directory: str) -> bool:
        """Save a specific device state to file"""
        device = self.get_device(port, unit_id)
        if device:
            import os
            os.makedirs(directory, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{directory}/device_{port.replace('/', '_')}_{unit_id}_{timestamp}.json"
            device.dump_to_file(filename)
            return True
        return False


# Global instance for easy access
device_manager = ModbusDeviceStateManager()
