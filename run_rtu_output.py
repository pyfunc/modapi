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
        // Track the last update time for rate limiting
        let lastUpdateTime = 0;
        const MIN_UPDATE_INTERVAL = 500; // 2 requests per second (1000ms / 2 = 500ms)
        let updateQueue = [];
        let isProcessingQueue = false;

        // Process the update queue with rate limiting
        async function processUpdateQueue() {
            if (isProcessingQueue || updateQueue.length === 0) return;
            
            isProcessingQueue = true;
            const now = Date.now();
            const timeSinceLastUpdate = now - lastUpdateTime;
            
            // Wait if needed to maintain rate limit
            if (timeSinceLastUpdate < MIN_UPDATE_INTERVAL) {
                const delay = MIN_UPDATE_INTERVAL - timeSinceLastUpdate;
                await new Promise(resolve => setTimeout(resolve, delay));
            }
            
            // Process the next update in the queue
            const { coilId, state, error } = updateQueue.shift();
            await updateCoilDisplay(coilId, state, error);
            lastUpdateTime = Date.now();
            
            // Process next item in queue if any
            isProcessingQueue = false;
            if (updateQueue.length > 0) {
                processUpdateQueue();
            }
        }

        // Queue an update to be processed with rate limiting
        function queueCoilUpdate(coilId, state, error = false) {
            // Check if this coil already has a pending update
            const existingIndex = updateQueue.findIndex(item => item.coilId === coilId);
            if (existingIndex >= 0) {
                // Replace the existing queued update for this coil
                updateQueue[existingIndex] = { coilId, state, error };
            } else {
                // Add new update to the queue
                updateQueue.push({ coilId, state, error });
            }
            processUpdateQueue();
        }

        async function loadCoils() {
            const now = Date.now();
            // If we've updated recently, skip this load to prevent too many requests
            if (now - lastUpdateTime < MIN_UPDATE_INTERVAL) {
                return;
            }
            
            for (let i = 0; i < 8; i++) {
                try {
                    const response = await fetch(`/coil/${i}`);
                    const data = await response.json();
                    queueCoilUpdate(i, data.state || false);
                } catch (error) {
                    console.error('Błąd odczytu cewki', i, error);
                    queueCoilUpdate(i, false, true);
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


# Use the auto-detection logic from modapi.__main__ for consistency
def auto_detect():
    """Auto-detect Modbus RTU device on specified ports using the same logic as modapi scan"""
    # Użyj portów z konfiguracji
    ports = AUTO_DETECT_CONFIG.get('ports', ['/dev/ttyACM0', '/dev/ttyUSB0'])
    unit_ids = AUTO_DETECT_CONFIG.get('unit_ids', [0, 1, 2])
    
    logger.info(f"Scanning ports from config: {ports}")
    
    # Prioritize /dev/ttyACM0 if it's in the list
    if '/dev/ttyACM0' in ports:
        ports = ['/dev/ttyACM0'] + [p for p in ports if p != '/dev/ttyACM0']
    
    for port in ports:
        logger.info(f"Checking port: {port}")
        # Explicitly pass PRIORITIZED_BAUDRATES to ensure we use the correct order
        result = auto_detect_modbus_port(baudrates=PRIORITIZED_BAUDRATES, debug=True, unit_id=None)
        if result:
            logger.info(f"✅ Found Modbus device on {result['port']} at {result['baudrate']} baud")
            return result
    
    logger.warning("No working configuration found")
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
                    # Try to switch the device to the highest prioritized baudrate
                    if client.set_device_baudrate(unit_id=RTU_CONFIG['unit_id']):
                        logger.info(f"✅ Przełączono urządzenie na {HIGHEST_PRIORITIZED_BAUDRATE} baud")
                        # Update the configuration with the new baudrate
                        RTU_CONFIG['baudrate'] = HIGHEST_PRIORITIZED_BAUDRATE
                    else:
                        logger.warning(f"⚠️ Nie udało się przełączyć na {HIGHEST_PRIORITIZED_BAUDRATE} baud, pozostaję na {RTU_CONFIG['baudrate']}")
                    client.disconnect()
            except Exception as e:
                logger.error(f"❌ Błąd podczas przełączania prędkości: {e}")
        
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


@app.route('/toggle_coil_0', methods=['POST'])
def toggle_coil_0():
    """Przełącz stan pierwszej cewki (adres 0)"""
    if not RTU_CONFIG:
        return jsonify({'error': 'RTU not configured'}), 500
    
    try:
        with ModbusRTU(RTU_CONFIG['port'], RTU_CONFIG['baudrate']) as client:
            # Odczytaj aktualny stan cewki 0
            current_state = client.read_coils(RTU_CONFIG['unit_id'], 0, 1)
            if current_state is None or len(current_state) == 0:
                return jsonify({'error': 'Failed to read current coil state'}), 500
                
            new_state = not current_state[0]
            
            # Ustaw nowy stan
            success = client.write_single_coil(RTU_CONFIG['unit_id'], 0, new_state)
            if success:
                # Potwierdź zapis przez odczyt
                verification = client.read_coils(RTU_CONFIG['unit_id'], 0, 1)
                actual_state = verification[0] if verification else None
                
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
    print(f"✅ Uruchamiam serwer na http://localhost:{SERVER_PORT}/")
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False, use_reloader=False)
