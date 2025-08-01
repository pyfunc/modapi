#!/usr/bin/env python3
"""
Nowy Output Server używający api.rtu zamiast problematycznego pymodbus
Zastępuje run_output.py który nie działał z rzeczywistym sprzętem
"""

import os
import sys
import logging
from flask import Flask, jsonify, request, render_template_string
from modapi.rtu import ModbusRTU
from modapi.__main__ import auto_detect_modbus_port
from modapi.config import (
    DEFAULT_PORT, DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID,
    BAUDRATES, PRIORITIZED_BAUDRATES, HIGHEST_PRIORITIZED_BAUDRATE, AUTO_DETECT_UNIT_IDS,
    READ_COILS, WRITE_SINGLE_COIL,
    get_config_value, _load_constants
)
import time

from modapi.config import (
    READ_COILS, READ_DISCRETE_INPUTS,
    READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS,
    WRITE_SINGLE_COIL, WRITE_SINGLE_REGISTER,
    WRITE_MULTIPLE_COILS, WRITE_MULTIPLE_REGISTERS,
    BAUDRATES, PRIORITIZED_BAUDRATES
)
# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globalna konfiguracja RTU
RTU_CONFIG = None
app = Flask(__name__)

# Załaduj konfigurację z constants.json
CONSTANTS = _load_constants()

# Pobierz konfigurację auto-detekcji
AUTO_DETECT_CONFIG = CONSTANTS.get('auto_detect', {
    'ports': ['/dev/ttyACM0', '/dev/ttyUSB0'],
    'unit_ids': [0, 1, 2]
})

# Pobierz konfigurację mock
MOCK_CONFIG = CONSTANTS.get('mock', {
    'port': 'MOCK',
    'baudrate': 19200,
    'unit_id': 1
})

# Pobierz konfigurację serwera
SERVER_PORT = int(get_config_value('SERVER_PORT', 5007))

# Path to the HTML template file
HTML_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'examples', 'rtu_controller.html')

# Load the HTML template from file
try:
    with open(HTML_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        HTML_TEMPLATE = f.read()
except Exception as e:
    logger.error(f"Failed to load HTML template from {HTML_TEMPLATE_PATH}: {e}")
    raise


# Use the auto-detection logic from modapi.__main__ for consistency
def auto_detect():
    """Auto-detect Modbus RTU device on specified ports using the same logic as modapi scan"""
    # Użyj portów z konfiguracji
    ports = AUTO_DETECT_CONFIG.get('ports', ['/dev/ttyACM0', '/dev/ttyUSB0'])
    unit_ids = AUTO_DETECT_CONFIG.get('unit_ids', [0, 1])
    
    logger.info(f"Scanning ports from config: {ports}")
    logger.info(f"Using unit IDs: {unit_ids}")
    
    # Prioritize /dev/ttyACM0 if it's in the list
    if '/dev/ttyACM0' in ports:
        ports = ['/dev/ttyACM0'] + [p for p in ports if p != '/dev/ttyACM0']
    
    # First try auto_detect_modbus_port with our prioritized baudrates
    # This will use the improved port filtering from modapi.rtu.utils.find_serial_ports
    logger.info("Using auto_detect_modbus_port with prioritized baudrates")
    result = auto_detect_modbus_port(baudrates=PRIORITIZED_BAUDRATES, debug=True)
    if result:
        logger.info(f"✅ Found Modbus device on {result['port']} at {result['baudrate']} baud with unit ID {result.get('unit_id', 1)}")
        # Verify the connection by trying to read coils
        try:
            with ModbusRTU(result['port'], result['baudrate']) as client:
                unit_id = result.get('unit_id', 1)
                # Try multiple function codes for Waveshare compatibility
                success = False
                
                # Try reading coils (function code 1)
                logger.info(f"Trying READ_COILS (FC1) with unit ID {unit_id}")
                try:
                    coils = client.read_coils(unit_id, 0, 1)
                    if coils and len(coils) > 0:
                        logger.info(f"✅ Successfully verified connection with READ_COILS and unit ID {unit_id}")
                        success = True
                except Exception as e:
                    logger.warning(f"⚠️ READ_COILS failed: {e}")
                
                # Try reading discrete inputs (function code 2)
                if not success:
                    logger.info(f"Trying READ_DISCRETE_INPUTS (FC2) with unit ID {unit_id}")
                    try:
                        inputs = client.read_discrete_inputs(unit_id, 0, 1)
                        if inputs and len(inputs) > 0:
                            logger.info(f"✅ Successfully verified connection with READ_DISCRETE_INPUTS and unit ID {unit_id}")
                            success = True
                    except Exception as e:
                        logger.warning(f"⚠️ READ_DISCRETE_INPUTS failed: {e}")
                
                # Try reading holding registers (function code 3)
                if not success:
                    logger.info(f"Trying READ_HOLDING_REGISTERS (FC3) with unit ID {unit_id}")
                    try:
                        registers = client.read_holding_registers(unit_id, 0, 1)
                        if registers and len(registers) > 0:
                            logger.info(f"✅ Successfully verified connection with READ_HOLDING_REGISTERS and unit ID {unit_id}")
                            success = True
                    except Exception as e:
                        logger.warning(f"⚠️ READ_HOLDING_REGISTERS failed: {e}")
                
                # Try reading input registers (function code 4)
                if not success:
                    logger.info(f"Trying READ_INPUT_REGISTERS (FC4) with unit ID {unit_id}")
                    try:
                        registers = client.read_input_registers(unit_id, 0, 1)
                        if registers and len(registers) > 0:
                            logger.info(f"✅ Successfully verified connection with READ_INPUT_REGISTERS and unit ID {unit_id}")
                            success = True
                    except Exception as e:
                        logger.warning(f"⚠️ READ_INPUT_REGISTERS failed: {e}")
                
                if success:
                    result['unit_id'] = unit_id
                    return result
                else:
                    logger.warning(f"⚠️ Auto-detection found a device but couldn't communicate with unit ID {unit_id}")
        except Exception as e:
            logger.warning(f"⚠️ Auto-detection verification failed: {e}")
    
    # If that fails, try with each unit ID in our config
    for unit_id in unit_ids:
        logger.info(f"Trying with unit ID: {unit_id}")
        result = auto_detect_modbus_port(baudrates=PRIORITIZED_BAUDRATES, debug=True, unit_id=unit_id)
        if result:
            logger.info(f"✅ Found Modbus device on {result['port']} at {result['baudrate']} baud with unit ID {unit_id}")
            # Verify the connection by trying multiple function codes
            try:
                with ModbusRTU(result['port'], result['baudrate']) as client:
                    # Try multiple function codes for Waveshare compatibility
                    success = False
                    
                    # Try reading coils (function code 1)
                    logger.info(f"Trying READ_COILS (FC1) with unit ID {unit_id}")
                    try:
                        coils = client.read_coils(unit_id, 0, 1)
                        if coils and len(coils) > 0:
                            logger.info(f"✅ Successfully verified connection with READ_COILS and unit ID {unit_id}")
                            success = True
                    except Exception as e:
                        logger.warning(f"⚠️ READ_COILS failed: {e}")
                    
                    # Try reading discrete inputs (function code 2)
                    if not success:
                        logger.info(f"Trying READ_DISCRETE_INPUTS (FC2) with unit ID {unit_id}")
                        try:
                            inputs = client.read_discrete_inputs(unit_id, 0, 1)
                            if inputs and len(inputs) > 0:
                                logger.info(f"✅ Successfully verified connection with READ_DISCRETE_INPUTS and unit ID {unit_id}")
                                success = True
                        except Exception as e:
                            logger.warning(f"⚠️ READ_DISCRETE_INPUTS failed: {e}")
                    
                    # Try reading holding registers (function code 3)
                    if not success:
                        logger.info(f"Trying READ_HOLDING_REGISTERS (FC3) with unit ID {unit_id}")
                        try:
                            registers = client.read_holding_registers(unit_id, 0, 1)
                            if registers and len(registers) > 0:
                                logger.info(f"✅ Successfully verified connection with READ_HOLDING_REGISTERS and unit ID {unit_id}")
                                success = True
                        except Exception as e:
                            logger.warning(f"⚠️ READ_HOLDING_REGISTERS failed: {e}")
                    
                    # Try reading input registers (function code 4)
                    if not success:
                        logger.info(f"Trying READ_INPUT_REGISTERS (FC4) with unit ID {unit_id}")
                        try:
                            registers = client.read_input_registers(unit_id, 0, 1)
                            if registers and len(registers) > 0:
                                logger.info(f"✅ Successfully verified connection with READ_INPUT_REGISTERS and unit ID {unit_id}")
                                success = True
                        except Exception as e:
                            logger.warning(f"⚠️ READ_INPUT_REGISTERS failed: {e}")
                    
                    if success:
                        # Make sure unit_id is in the result
                        result['unit_id'] = unit_id
                        return result
                    else:
                        logger.warning(f"⚠️ Auto-detection found a device but couldn't communicate with unit ID {unit_id}")
            except Exception as e:
                logger.warning(f"⚠️ Auto-detection verification failed with unit ID {unit_id}: {e}")
    
    # Last resort: try all combinations of baudrates and unit IDs
    logger.info("Trying all combinations of baudrates and unit IDs as last resort")
    for port in ports:
        for baudrate in BAUDRATES:
            for unit_id in unit_ids:
                logger.info(f"Testing port {port} at {baudrate} baud with unit ID {unit_id}")
                try:
                    with ModbusRTU(port, baudrate) as client:
                        # Try multiple function codes for Waveshare compatibility
                        success = False
                        
                        # Try reading coils (function code 1)
                        try:
                            coils = client.read_coils(unit_id, 0, 1)
                            if coils and len(coils) > 0:
                                logger.info(f"✅ Success with READ_COILS! Found working configuration: port={port}, baudrate={baudrate}, unit_id={unit_id}")
                                return {'port': port, 'baudrate': baudrate, 'unit_id': unit_id}
                        except Exception:
                            pass
                        
                        # Try reading discrete inputs (function code 2)
                        try:
                            inputs = client.read_discrete_inputs(unit_id, 0, 1)
                            if inputs and len(inputs) > 0:
                                logger.info(f"✅ Success with READ_DISCRETE_INPUTS! Found working configuration: port={port}, baudrate={baudrate}, unit_id={unit_id}")
                                return {'port': port, 'baudrate': baudrate, 'unit_id': unit_id}
                        except Exception:
                            pass
                        
                        # Try reading holding registers (function code 3)
                        try:
                            registers = client.read_holding_registers(unit_id, 0, 1)
                            if registers and len(registers) > 0:
                                logger.info(f"✅ Success with READ_HOLDING_REGISTERS! Found working configuration: port={port}, baudrate={baudrate}, unit_id={unit_id}")
                                return {'port': port, 'baudrate': baudrate, 'unit_id': unit_id}
                        except Exception:
                            pass
                        
                        # Try reading input registers (function code 4)
                        try:
                            registers = client.read_input_registers(unit_id, 0, 1)
                            if registers and len(registers) > 0:
                                logger.info(f"✅ Success with READ_INPUT_REGISTERS! Found working configuration: port={port}, baudrate={baudrate}, unit_id={unit_id}")
                                return {'port': port, 'baudrate': baudrate, 'unit_id': unit_id}
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"Failed with {port}, {baudrate}, {unit_id}: {e}")
    
    logger.warning("No working configuration found after trying all combinations")
    return None

def init_mock_mode():
    """Initialize mock mode for testing without hardware"""
    global RTU_CONFIG
    print("🔧 Uruchamiam w trybie MOCK (bez rzeczywistego urządzenia)")
    
    # Użyj konfiguracji mock z constants.json
    RTU_CONFIG = {
        'port': MOCK_CONFIG.get('port', 'MOCK'),
        'baudrate': MOCK_CONFIG.get('baudrate', 19200),
        'unit_id': MOCK_CONFIG.get('unit_id', 1)
    }
    logger.info(f"✅ Używam konfiguracji MOCK: {RTU_CONFIG}")
    
    # Monkey patch ModbusRTU for mock mode
    def mock_read_coils(self, unit_id, address, count):
        logger.info(f"MOCK: Reading {count} coils from address {address} (unit_id={unit_id})")
        return [False] * count
        
    def mock_write_single_coil(self, unit_id, address, value):
        logger.info(f"MOCK: Writing coil at address {address} to {value} (unit_id={unit_id})")
        return True
        
    def mock_read_holding_registers(self, unit_id, address, count):
        logger.info(f"MOCK: Reading {count} registers from address {address} (unit_id={unit_id})")
        return [0] * count
    
    ModbusRTU.read_coils = mock_read_coils
    ModbusRTU.write_single_coil = mock_write_single_coil
    ModbusRTU.read_holding_registers = mock_read_holding_registers
    
    # Override connect and disconnect for mock mode
    ModbusRTU.connect = lambda self: True
    ModbusRTU.disconnect = lambda self: None
    
    print("✅ Mock RTU device ready")
    return True

def init_rtu():
    """Inicjalizuj RTU i znajdź działającą konfigurację"""
    global RTU_CONFIG
    
    logger.info("Inicjalizacja RTU...")
    
    # Użyj funkcji auto-detekcji z konfiguracją z constants.json
    RTU_CONFIG = auto_detect()
    
    if RTU_CONFIG:
        logger.info(f"✅ Znaleziono działającą konfigurację RTU: {RTU_CONFIG}")
        
        # Try to switch to higher baudrate after successful connection
        if HIGHEST_PRIORITIZED_BAUDRATE > RTU_CONFIG['baudrate']:
            logger.info(f"Próbuję przełączyć na wyższą prędkość: {HIGHEST_PRIORITIZED_BAUDRATE} baud")
            try:
                # Create a client with the detected configuration
                client = ModbusRTU(port=RTU_CONFIG['port'], baudrate=RTU_CONFIG['baudrate'])
                if client.connect():
                    # Try to switch both the device and client to the highest prioritized baudrate
                    if client.switch_baudrate(HIGHEST_PRIORITIZED_BAUDRATE):
                        logger.info(f"✅ Przełączono urządzenie i klienta na {HIGHEST_PRIORITIZED_BAUDRATE} baud")
                        # Update the configuration with the new baudrate
                        RTU_CONFIG['baudrate'] = HIGHEST_PRIORITIZED_BAUDRATE
                    else:
                        logger.warning(f"⚠️ Nie udało się przełączyć na {HIGHEST_PRIORITIZED_BAUDRATE} baud, pozostaję na {RTU_CONFIG['baudrate']}")
                    client.disconnect()
            except Exception as e:
                logger.error(f"❌ Błąd podczas przełączania prędkości: {e}")
                logger.debug(f"Szczegóły błędu: {str(e)}", exc_info=True)
        
        return True
    else:
        logger.error("❌ Nie znaleziono działającej konfiguracji RTU!")
        
        # Spróbuj ręcznie z domyślnymi ustawieniami z config.py
        logger.info(f"Próbuję połączenia ręcznego z domyślnymi ustawieniami: port={DEFAULT_PORT}, baudrate={DEFAULT_BAUDRATE}")
        manual_client = ModbusRTU(DEFAULT_PORT, DEFAULT_BAUDRATE)
        
        if manual_client.connect():
            # Implement test_connection directly
            result = {
                'port': DEFAULT_PORT,
                'baudrate': DEFAULT_BAUDRATE,
                'unit_id': DEFAULT_UNIT_ID,
                'success': False,
                'error': None
            }
            
            try:
                # Try to read a register to verify connection
                response = manual_client.read_holding_registers(0, 1, DEFAULT_UNIT_ID)
                if response is not None:
                    result['success'] = True
                else:
                    result['error'] = "No response from device"
                    
                # Try reading coils if registers didn't work
                if not result['success']:
                    response = manual_client.read_coils(0, 8, DEFAULT_UNIT_ID)
                    if response is not None:
                        result['success'] = True
                        result['error'] = None
            except Exception as e:
                result['error'] = str(e)
            
            success = result['success']
            if success:
                RTU_CONFIG = {
                    'port': DEFAULT_PORT,
                    'baudrate': DEFAULT_BAUDRATE, 
                    'unit_id': DEFAULT_UNIT_ID
                }
                logger.info(f"✅ Połączenie ręczne udane: {RTU_CONFIG}")
                manual_client.disconnect()
                return True
            manual_client.disconnect()
        
        return False


@app.route('/')
def index():
    """Główna strona z interfejsem sterowania"""
    try:
        return render_template_string(HTML_TEMPLATE, config=RTU_CONFIG)
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return f"Error loading template: {e}", 500


@app.route('/status')
def status():
    """Status połączenia RTU"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    # Test połączenia
    with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
        # Implement test_connection directly
        result = {
            'port': RTU_CONFIG['port'],
            'baudrate': RTU_CONFIG['baudrate'],
            'unit_id': RTU_CONFIG['unit_id'],
            'success': False,
            'error': None
        }
        
        try:
            # Try to read a register to verify connection
            response = client.read_holding_registers(0, 1, RTU_CONFIG['unit_id'])
            if response is not None:
                result['success'] = True
            else:
                result['error'] = "No response from device"
                
            # Try reading coils if registers didn't work
            if not result['success']:
                response = client.read_coils(0, 8, RTU_CONFIG['unit_id'])
                if response is not None:
                    result['success'] = True
                    result['error'] = None
        except Exception as e:
            result['error'] = str(e)
        
        success = result['success']
        
        return jsonify({
            'connected': success,
            'config': RTU_CONFIG,
            'test_result': result,
            'timestamp': time.time()
        })


@app.route('/coil/<int:address>')
def get_coil(address):
    """Odczytaj stan cewki"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    if address < 0 or address > 255:
        return jsonify({'error': 'Invalid coil address'}), 400
    
    try:
        unit_id = RTU_CONFIG.get('unit_id', DEFAULT_UNIT_ID)
        logger.debug(f"Reading coil {address} with unit_id={unit_id}")
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            coils = client.read_coils(unit_id, address, 1)
            if coils and len(coils) > 0:  # Check if list is not empty
                return jsonify({
                    'address': address,
                    'state': coils[0],
                    'unit_id': unit_id,
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': f'Failed to read coil or no response from device (unit_id={unit_id})'}), 500
                
    except Exception as e:
        logger.error(f"Błąd odczytu cewki {address}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/coil/<int:address>', methods=['POST'])
def set_coil(address):
    """Ustaw stan cewki"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    if address < 0 or address > 255:
        return jsonify({'error': 'Invalid coil address'}), 400
    
    try:
        data = request.get_json()
        if not data or 'state' not in data:
            return jsonify({'error': 'Missing state parameter'}), 400
        
        state = bool(data['state'])
        unit_id = RTU_CONFIG.get('unit_id', DEFAULT_UNIT_ID)
        logger.debug(f"Setting coil {address} to {state} with unit_id={unit_id}")
        
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            success = client.write_single_coil(unit_id, address, state)
            if success:
                # Potwierdź zapis przez odczyt
                verification = client.read_coils(unit_id, address, 1)
                actual_state = verification[0] if verification and len(verification) > 0 else None
                
                return jsonify({
                    'address': address,
                    'requested_state': state,
                    'actual_state': actual_state,
                    'success': True,
                    'verified': actual_state == state if actual_state is not None else False,
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': 'Failed to write coil'}), 500
                
    except Exception as e:
        logger.error(f"Błąd zapisu cewki {address}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/coils')
def get_all_coils():
    """Odczytaj wszystkie cewki (0-15)"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    try:
        unit_id = RTU_CONFIG.get('unit_id', DEFAULT_UNIT_ID)
        logger.debug(f"Reading all coils with unit_id={unit_id}")
        
        # Initialize all coils to False by default
        all_coils = [False] * 16
        success = False
        
        try:
            # First try to read all coils at once
            with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
                coils = client.read_coils(unit_id, 0, 16)
                if coils and len(coils) > 0:
                    # Update the states of the coils we successfully read
                    for i in range(min(len(coils), 16)):
                        all_coils[i] = bool(coils[i])
                    success = True
        except Exception as e:
            logger.warning(f"Błąd odczytu wszystkich cewek naraz: {e}")
            
        # If reading all coils at once failed, try reading them one by one
        if not success:
            with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
                for i in range(16):
                    try:
                        coil = client.read_coils(unit_id, i, 1)
                        if coil and len(coil) > 0:
                            all_coils[i] = bool(coil[0])
                    except Exception as e:
                        logger.warning(f"Błąd odczytu cewki {i}: {e}")
                        all_coils[i] = False
        
        return jsonify({
            'coils': all_coils,
            'count': len(all_coils),
            'unit_id': unit_id,
            'timestamp': time.time(),
            'success': True
        })
            
    except Exception as e:
        logger.error(f"Krytyczny błąd odczytu cewek: {e}")
        return jsonify({
            'error': f'Failed to read coils: {str(e)}',
            'success': False
        }), 500


@app.route('/registers/<int:address>')
def get_register(address):
    """Odczytaj rejestr (może nie działać na wszystkich urządzeniach)"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    if address < 0 or address > 65535:
        return jsonify({'error': 'Invalid register address'}), 400
    
    try:
        unit_id = RTU_CONFIG.get('unit_id', DEFAULT_UNIT_ID)
        logger.debug(f"Reading register {address} with unit_id={unit_id}")
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            registers = client.read_holding_registers(unit_id, address, 1)
            if registers and len(registers) > 0:  # Check if list is not empty
                return jsonify({
                    'address': address,
                    'value': registers[0],
                    'unit_id': unit_id,
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': f'Failed to read register or no response from device (unit_id={unit_id})'}), 500
                
    except Exception as e:
        logger.error(f"Błąd odczytu rejestru {address}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/toggle_coil_0', methods=['POST'])
def toggle_coil_0():
    """Przełącz stan pierwszej cewki (adres 0)"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    try:
        unit_id = RTU_CONFIG.get('unit_id', DEFAULT_UNIT_ID)
        logger.debug(f"Toggling coil 0 with unit_id={unit_id}")
        
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            # Odczytaj aktualny stan cewki 0
            current_state = client.read_coils(unit_id, 0, 1)
            if current_state is None or len(current_state) == 0:
                return jsonify({'error': f'Failed to read current coil state (unit_id={unit_id})'}), 500
                
            new_state = not current_state[0]
            
            # Ustaw nowy stan
            success = client.write_single_coil(unit_id, 0, new_state)
            if success:
                # Potwierdź zapis przez odczyt
                verification = client.read_coils(unit_id, 0, 1)
                actual_state = verification[0] if verification and len(verification) > 0 else None
                
                return jsonify({
                    'address': 0,
                    'previous_state': current_state[0],
                    'new_state': new_state,
                    'actual_state': actual_state,
                    'success': True,
                    'verified': actual_state == new_state if actual_state is not None else False,
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': 'Failed to write coil'}), 500
                
    except Exception as e:
        logger.error(f"Błąd przełączania cewki 0: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':

    # Import sys if not already imported
    import sys
    
    # Check for mock mode
    mock_mode = "--mock" in sys.argv
    
    if mock_mode:
        print("🧪 Wykryto flagę --mock, uruchamiam w trybie testowym bez sprzętu")
        init_success = init_mock_mode()
    else:
        # Inicjalizacja RTU
        print("🔌 Uruchamiam w trybie normalnym, szukam podłączonego sprzętu RTU")
        init_success = init_rtu()
        
    if not init_success:
        print("❌ Nie można uruchomić serwera bez działającej konfiguracji RTU")
        print("🔍 Sprawdź:")
        print("   - Czy urządzenie jest podłączone do /dev/ttyACM0 lub /dev/ttyUSB0")
        print("   - Czy urządzenie jest włączone")
        print("   - Czy masz uprawnienia do portu szeregowego")
        print("   - Czy nie używa niestandardowej prędkości lub unit ID")
        print("\n💡 Możesz uruchomić w trybie MOCK dla testów: python run_rtu_output.py --mock")
        sys.exit(1)
    
    # Uruchom serwer
    print(f"✅ Uruchamiam serwer na http://localhost:{SERVER_PORT}/")
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False, use_reloader=False)
