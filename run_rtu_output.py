#!/usr/bin/env python3
"""
Nowy Output Server używający api.rtu zamiast problematycznego pymodbus
Zastępuje run_output.py który nie działał z rzeczywistym sprzętem
"""

import os
import sys
import logging
from flask import Flask, jsonify, request, render_template_string
from modapi.api.rtu import ModbusRTU
import time

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globalna konfiguracja RTU
RTU_CONFIG = None
app = Flask(__name__)

# HTML template dla interfejsu web
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RTU Output Controller</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        .coil { margin: 10px; padding: 10px; border: 1px solid #ccc; }
        .coil.on { background-color: #90EE90; }
        .coil.off { background-color: #FFB6C1; }
        button { padding: 5px 10px; margin: 5px; }
        .status { margin: 20px 0; padding: 10px; background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>RTU Output Controller</h1>
    <div class="status">
        <h3>Status połączenia:</h3>
        <p>Port: {{ config.port if config else 'Nie skonfigurowany' }}</p>
        <p>Prędkość: {{ config.baudrate if config else 'N/A' }} baud</p>
        <p>Unit ID: {{ config.unit_id if config else 'N/A' }}</p>
        <p>Status: {{ 'Połączony' if config else 'Błąd' }}</p>
    </div>
    
    <h3>Sterowanie cewkami (0-7):</h3>
    <div id="coils">
        <!-- Cewki będą załadowane przez JavaScript -->
    </div>
    
    <script>
        async function loadCoils() {
            for (let i = 0; i < 8; i++) {
                try {
                    const response = await fetch(`/coil/${i}`);
                    const data = await response.json();
                    updateCoilDisplay(i, data.state || false);
                } catch (error) {
                    console.error('Błąd odczytu cewki', i, error);
                    updateCoilDisplay(i, false, true);
                }
            }
        }
        
        function updateCoilDisplay(coilId, state, error = false) {
            const coilsDiv = document.getElementById('coils');
            let coilDiv = document.getElementById(`coil-${coilId}`);
            
            if (!coilDiv) {
                coilDiv = document.createElement('div');
                coilDiv.id = `coil-${coilId}`;
                coilDiv.className = 'coil';
                coilsDiv.appendChild(coilDiv);
            }
            
            if (error) {
                coilDiv.innerHTML = `<strong>Cewka ${coilId}:</strong> BŁĄD`;
                coilDiv.className = 'coil';
            } else {
                coilDiv.className = `coil ${state ? 'on' : 'off'}`;
                coilDiv.innerHTML = `
                    <strong>Cewka ${coilId}:</strong> ${state ? 'ON' : 'OFF'}
                    <button onclick="setCoil(${coilId}, true)">ON</button>
                    <button onclick="setCoil(${coilId}, false)">OFF</button>
                `;
            }
        }
        
        async function setCoil(coilId, state) {
            try {
                const response = await fetch(`/coil/${coilId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ state: state })
                });
                
                const data = await response.json();
                if (data.success) {
                    updateCoilDisplay(coilId, state);
                } else {
                    alert(`Błąd ustawiania cewki ${coilId}: ${data.error}`);
                }
            } catch (error) {
                alert(`Błąd komunikacji: ${error}`);
            }
        }
        
        // Załaduj stany cewek przy starcie
        loadCoils();
        
        // Odświeżaj co 5 sekund
        setInterval(loadCoils, 5000);
    </script>
</body>
</html>
"""


# Helper function to auto-detect RTU devices
def auto_detect(ports):
    """Auto-detect Modbus RTU device on specified ports"""
    baudrates = [9600, 115200, 19200, 4800, 38400, 57600]
    unit_ids = [1, 2, 3, 4]
    
    for port in ports:
        for baudrate in baudrates:
            for unit_id in unit_ids:
                try:
                    client = ModbusRTU(port, baudrate)
                    logger.info(f"Testing configuration: port={port}, baudrate={baudrate}, unit_id={unit_id}")
                    
                    # Próbuj odczytać rejestry
                    logger.debug(f"Attempting to read holding registers with unit_id={unit_id}")
                    response = client.read_holding_registers(0, 1, unit_id)
                    if response is not None:
                        logger.info(f"✅ Auto-detect success with holding registers: port={port}, baudrate={baudrate}, unit_id={unit_id}, response={response}")
                        client.disconnect()
                        return {
                            'port': port,
                            'baudrate': baudrate,
                            'unit_id': unit_id
                        }
                    else:
                        logger.debug(f"No response from holding registers with unit_id={unit_id}")
                    
                    # Próbuj odczytać cewki
                    logger.debug(f"Attempting to read coils with unit_id={unit_id}")
                    response = client.read_coils(0, 8, unit_id)
                    if response is not None:
                        logger.info(f"✅ Auto-detect success with coils: port={port}, baudrate={baudrate}, unit_id={unit_id}, response={response}")
                        client.disconnect()
                        return {
                            'port': port,
                            'baudrate': baudrate,
                            'unit_id': unit_id
                        }
                    else:
                        logger.debug(f"No response from coils with unit_id={unit_id}")
                    
                    client.disconnect()
                except Exception as e:
                    # Log connection errors
                    logger.debug(f"Error testing {port} at {baudrate} baud with unit_id={unit_id}: {e}")
    
    logger.warning("No working configuration found")
    return None

def init_mock_mode():
    """Initialize mock mode for testing without hardware"""
    global RTU_CONFIG
    print("🔧 Uruchamiam w trybie MOCK (bez rzeczywistego urządzenia)")
    RTU_CONFIG = {
        'port': 'MOCK',
        'baudrate': 9600,
        'unit_id': 1
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
    
    # Spróbuj auto-detekcji
    RTU_CONFIG = auto_detect(['/dev/ttyACM0', '/dev/ttyUSB0'])
    
    if RTU_CONFIG:
        logger.info(f"✅ Znaleziono działającą konfigurację RTU: {RTU_CONFIG}")
        return True
    else:
        logger.error("❌ Nie znaleziono działającej konfiguracji RTU!")
        
        # Spróbuj ręcznie z domyślnymi ustawieniami
        logger.info("Próbuję połączenia ręcznego z domyślnymi ustawieniami...")
        manual_client = ModbusRTU('/dev/ttyACM0', 9600)
        
        if manual_client.connect():
            # Implement test_connection directly
            result = {
                'port': '/dev/ttyACM0',
                'baudrate': 9600,
                'unit_id': 1,
                'success': False,
                'error': None
            }
            
            try:
                # Try to read a register to verify connection
                response = manual_client.read_holding_registers(0, 1, 1)
                if response is not None:
                    result['success'] = True
                else:
                    result['error'] = "No response from device"
                    
                # Try reading coils if registers didn't work
                if not result['success']:
                    response = manual_client.read_coils(0, 8, 1)
                    if response is not None:
                        result['success'] = True
                        result['error'] = None
            except Exception as e:
                result['error'] = str(e)
            
            success = result['success']
            if success:
                RTU_CONFIG = {
                    'port': '/dev/ttyACM0',
                    'baudrate': 9600, 
                    'unit_id': 1
                }
                logger.info(f"✅ Połączenie ręczne udane: {RTU_CONFIG}")
                manual_client.disconnect()
                return True
            manual_client.disconnect()
        
        return False


@app.route('/')
def index():
    """Główna strona z interfejsem sterowania"""
    return render_template_string(HTML_TEMPLATE, config=RTU_CONFIG)


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
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            coils = client.read_coils(RTU_CONFIG['unit_id'], address, 1)
            if coils is not None:
                return jsonify({
                    'address': address,
                    'state': coils[0],
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': 'Failed to read coil'}), 500
                
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
        
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            success = client.write_single_coil(RTU_CONFIG['unit_id'], address, state)
            if success:
                # Potwierdź zapis przez odczyt
                verification = client.read_coils(RTU_CONFIG['unit_id'], address, 1)
                actual_state = verification[0] if verification else None
                
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
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            coils = client.read_coils(RTU_CONFIG['unit_id'], 0, 16)
            if coils is not None:
                return jsonify({
                    'coils': coils,
                    'count': len(coils),
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': 'Failed to read coils'}), 500
                
    except Exception as e:
        logger.error(f"Błąd odczytu cewek: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/registers/<int:address>')
def get_register(address):
    """Odczytaj rejestr (może nie działać na wszystkich urządzeniach)"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    if address < 0 or address > 65535:
        return jsonify({'error': 'Invalid register address'}), 400
    
    try:
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            registers = client.read_holding_registers(RTU_CONFIG['unit_id'], address, 1)
            if registers is not None:
                return jsonify({
                    'address': address,
                    'value': registers[0],
                    'timestamp': time.time()
                })
            else:
                return jsonify({'error': 'Failed to read register (may not be supported)'}), 500
                
    except Exception as e:
        logger.error(f"Błąd odczytu rejestru {address}: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 RTU Output Server - Zastępuje problematyczny run_output.py")
    print("📡 Używa bezpośredniej komunikacji RTU zamiast PyModbus")
    
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
    print(f"✅ Uruchamiam serwer na http://localhost:5005/")
    app.run(host='0.0.0.0', port=5005, debug=False, use_reloader=False)
