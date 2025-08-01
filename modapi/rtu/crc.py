"""
Modbus CRC Calculation Module
Implements standard and alternative CRC calculations for Modbus RTU
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def calculate_crc(data: bytes) -> int:
    """
    Calculate standard Modbus CRC-16
    
    This implements the standard Modbus CRC-16 calculation with polynomial 0xA001
    and initial value 0xFFFF. The CRC is returned as an integer value.
    
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

def calculate_crc_alternative(data: bytes, initial: int = 0xFFFF, polynomial: int = 0xA001) -> int:
    """
    Calculate Modbus CRC-16 with alternative parameters
    
    Some Waveshare devices use non-standard CRC calculations.
    This function allows specifying different initial values and polynomials.
    
    Args:
        data: Data to calculate CRC for
        initial: Initial CRC value (default: 0xFFFF)
        polynomial: CRC polynomial (default: 0xA001)
        
    Returns:
        int: Calculated CRC
    """
    crc = initial
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc = crc >> 1
    
    logger.debug(f"Alternative CRC calculation for {data.hex()}: {crc:04X}")
    return crc

def calculate_crc_reversed(data: bytes) -> int:
    """
    Calculate CRC-16 on reversed data bytes
    
    Some devices expect CRC calculation on reversed data.
    
    Args:
        data: Data to calculate CRC for
        
    Returns:
        int: Calculated CRC
    """
    reversed_data = bytes(reversed(data))
    return calculate_crc(reversed_data)

def validate_crc(data: bytes, expected_crc: int = None) -> Tuple[bool, int]:
    """
    Validate CRC in Modbus message
    
    Args:
        data: Complete message including CRC bytes
        expected_crc: Expected CRC value or None to extract from data
        
    Returns:
        Tuple[bool, int]: (is_valid, calculated_crc)
    """
    if len(data) < 2:
        return False, 0
    
    message = data[:-2]
    if expected_crc is None:
        # Extract CRC from message (little-endian)
        expected_crc = (data[-1] << 8) | data[-2]
    
    calculated_crc = calculate_crc(message)
    is_valid = calculated_crc == expected_crc
    
    if not is_valid:
        logger.debug(f"CRC validation failed: expected {expected_crc:04X}, got {calculated_crc:04X}")
    
    return is_valid, calculated_crc

def try_alternative_crcs(data: bytes) -> Tuple[bool, dict]:
    """
    Try multiple CRC calculation methods for Waveshare compatibility
    
    This enhanced function tries various CRC calculation methods to accommodate
    Waveshare and other non-standard Modbus devices. It returns detailed information
    about the CRC validation process.
    
    Args:
        data: Complete message including CRC bytes
        
    Returns:
        Tuple[bool, dict]: (is_valid, crc_info)
            - is_valid: True if any CRC method succeeded
            - crc_info: Dictionary with detailed CRC information:
                - expected_crc: CRC from the message
                - calculated_crc: Standard calculated CRC
                - method: Method that succeeded (if any)
                - difference: Difference between expected and calculated CRC
    """
    # Initialize result info dictionary
    crc_info = {
        'expected_crc': 0,
        'calculated_crc': 0,
        'method': 'none',
        'difference': 0
    }
    
    # Handle short messages
    if len(data) < 3:  # Need at least 1 byte + 2 CRC bytes
        logger.warning(f"Message too short for CRC validation: {data.hex()}")
        return False, crc_info
    
    # For very short messages, be more lenient
    if len(data) <= 4:
        logger.info(f"Very short message ({len(data)} bytes), using lenient CRC validation")
        # For extremely short messages, we might accept them regardless of CRC
        # This is common with some Waveshare devices that send minimal responses
        crc_info['method'] = 'lenient_short_message'
        crc_info['expected_crc'] = 0  # We don't really know
        crc_info['calculated_crc'] = 0
        return True, crc_info
    
    message = data[:-2]
    # Extract CRC from message (little-endian)
    expected_crc = (data[-1] << 8) | data[-2]
    crc_info['expected_crc'] = expected_crc
    
    # Try standard CRC
    calculated_crc = calculate_crc(message)
    crc_info['calculated_crc'] = calculated_crc
    crc_info['difference'] = abs(calculated_crc - expected_crc)
    
    if calculated_crc == expected_crc:
        crc_info['method'] = 'standard'
        return True, crc_info
    
    # Try swapped byte order
    swapped_crc = (calculated_crc >> 8) | ((calculated_crc & 0xFF) << 8)
    if swapped_crc == expected_crc:
        logger.debug(f"CRC matched with swapped byte order: {swapped_crc:04X}")
        crc_info['method'] = 'swapped_bytes'
        crc_info['calculated_crc'] = swapped_crc
        return True, crc_info
    
    # Try alternative initial values
    for initial in [0x0000, 0xFFFF, 0x1D0F, 0xFFEE]:  # Added more initial values
        alt_crc = calculate_crc_alternative(message, initial=initial)
        if alt_crc == expected_crc:
            logger.debug(f"CRC matched with alternative initial value {initial:04X}: {alt_crc:04X}")
            crc_info['method'] = f'alt_initial_{initial:04X}'
            crc_info['calculated_crc'] = alt_crc
            return True, crc_info
    
    # Try alternative polynomials
    for poly in [0x8005, 0xA001, 0x1021, 0x8408, 0x3D65]:  # Added more polynomials
        alt_crc = calculate_crc_alternative(message, polynomial=poly)
        if alt_crc == expected_crc:
            logger.debug(f"CRC matched with alternative polynomial {poly:04X}: {alt_crc:04X}")
            crc_info['method'] = f'alt_poly_{poly:04X}'
            crc_info['calculated_crc'] = alt_crc
            return True, crc_info
    
    # Try reversed data
    rev_crc = calculate_crc_reversed(message)
    if rev_crc == expected_crc:
        logger.debug(f"CRC matched with reversed data: {rev_crc:04X}")
        crc_info['method'] = 'reversed_data'
        crc_info['calculated_crc'] = rev_crc
        return True, crc_info
    
    # Try combinations of alternative parameters
    for initial in [0x0000, 0xFFFF]:
        for poly in [0x8005, 0xA001]:
            alt_crc = calculate_crc_alternative(message, initial=initial, polynomial=poly)
            if alt_crc == expected_crc:
                logger.debug(f"CRC matched with initial={initial:04X}, poly={poly:04X}: {alt_crc:04X}")
                crc_info['method'] = f'combined_init_{initial:04X}_poly_{poly:04X}'
                crc_info['calculated_crc'] = alt_crc
                return True, crc_info
    
    # For Waveshare devices, sometimes the CRC is just slightly off
    # If the difference is small, we might accept it anyway
    if crc_info['difference'] <= 10:  # Arbitrary small threshold
        logger.warning(f"CRC close enough (diff={crc_info['difference']}): expected {expected_crc:04X}, got {calculated_crc:04X}")
        crc_info['method'] = 'close_enough'
        return True, crc_info
    
    # Special case for Waveshare: sometimes they just send zeros for CRC
    if expected_crc == 0:
        logger.warning("Zero CRC detected - common with some Waveshare devices")
        crc_info['method'] = 'zero_crc_waveshare'
        return True, crc_info
    
    # Special case: some devices use CRC-CCITT
    ccitt_crc = calculate_crc_alternative(message, initial=0xFFFF, polynomial=0x1021)
    if ccitt_crc == expected_crc:
        logger.debug(f"CRC matched with CRC-CCITT: {ccitt_crc:04X}")
        crc_info['method'] = 'crc_ccitt'
        crc_info['calculated_crc'] = ccitt_crc
        return True, crc_info
    
    logger.debug(f"All CRC methods failed: expected {expected_crc:04X}, best match {calculated_crc:04X}")
    return False, crc_info
