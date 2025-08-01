# Waveshare Modbus RTU Implementation Notes

This document describes the non-standard aspects of Waveshare's Modbus RTU implementation and how our library handles them.

## Overview

Waveshare devices implement the Modbus RTU protocol with several non-standard behaviors that require special handling. This document outlines these behaviors and the workarounds implemented in our library.

## Non-Standard Behaviors

### 1. Function Code Variations

Waveshare devices sometimes use non-standard function codes:

- May use `0x43` instead of standard `0x03` for reading holding registers
- May respond to broadcast messages (unit ID 0) even though standard Modbus requires a specific unit ID

### 2. CRC Validation

- Some Waveshare devices send responses with non-standard CRC values
- Our library includes options to bypass strict CRC validation when needed

### 3. Response Timing

- Waveshare devices may require longer delays between operations due to their RS485 implementation
- Our library implements adaptive timing with increasing delays on retries

### 4. Response Format

- Some responses may have unexpected byte counts or data formats
- Our library includes robust parsing that can handle these variations

## Implementation Details

### Function Code Handling

When standard function codes fail, our library automatically tries Waveshare-specific alternatives:

```python
# Example from read_holding_registers method
request = build_read_request(unit_id, READ_HOLDING_REGISTERS, address, count)
response = self.send_request(request, unit_id, READ_HOLDING_REGISTERS)

if not response:
    # Try with Waveshare-specific function code
    request = build_read_request(unit_id, 0x43, address, count)
    response = self.send_request(request, unit_id, 0x43)
```

### CRC Validation

Our protocol parser includes options to bypass strict CRC validation:

```python
def parse_response(response, unit_id=None, function_code=None, check_crc=True):
    # CRC validation can be bypassed when needed for Waveshare devices
    if check_crc:
        # Validate CRC
        # ...
    else:
        # Skip CRC validation
        # ...
```

### RS485 Timing

We implement adaptive timing with increasing delays on retries:

```python
def send_request(self, request, unit_id, function_code, retry_count=2):
    # Try multiple times with increasing timeouts
    original_timeout = self.timeout
    
    for attempt in range(retry_count + 1):
        # Increase timeout for retries
        if attempt > 0:
            self.timeout = original_timeout * (1 + attempt * 0.5)
            # Add a longer delay between retries
            time.sleep(self.rs485_delay * 2)
```

## Device-Specific Quirks

### Waveshare IO 8CH

- 8-channel relay output module
- Supports function codes 0x01 (read coils) and 0x05 (write single coil)
- Default unit ID: 1
- Default baudrate: 9600

### Waveshare Analog Input 8CH

- 8-channel analog input module
- Supports function code 0x04 (read input registers)
- Default unit ID: 1
- Default baudrate: 9600
- Register mapping:
  - 0x0000-0x0007: Analog input values (0-4095)
  - 0x0008-0x000F: Voltage values (mV)

## Troubleshooting

If you encounter issues with Waveshare devices:

1. **Verify baudrate**: Waveshare devices often default to 9600 baud
2. **Check unit ID**: Default is usually 1, but can be changed
3. **Try broadcast address**: Some devices respond to unit ID 0
4. **Increase timeout**: Try longer timeouts for slow-responding devices
5. **Disable CRC checking**: If CRC validation fails consistently

## References

- [Waveshare IO 8CH Wiki](https://www.waveshare.com/wiki/Modbus_RTU_IO_8CH)
- [Waveshare Analog Input 8CH Wiki](https://www.waveshare.com/wiki/Modbus_RTU_Analog_Input_8CH)
- [Modbus RTU Specification](https://modbus.org/docs/Modbus_over_serial_line_V1_02.pdf)
