# modapi

🚀 **Direct Modbus RTU Communication API** - Bezpośrednia komunikacja z urządzeniami Modbus przez port szeregowy.

## ✨ Kluczowe cechy

- **🔧 Direct RTU Module** - Bezpośrednia komunikacja Modbus RTU bez PyModbus
- **📡 Verified Hardware Support** - Przetestowane z rzeczywistym sprzętem `/dev/ttyACM0`
- **🔍 Smart Auto-detection** - Automatyczne wykrywanie działających urządzeń i konfiguracji
- **🌐 Web Interface** - Nowoczesny interfejs web do sterowania cewkami
- **⚡ Multiple APIs**:
  - **REST API** - HTTP API dla aplikacji web
  - **Direct RTU** - Bezpośrednia komunikacja szeregowa
  - **Shell CLI** - Interfejs linii poleceń
- **🧪 Fully Tested** - Kompletne testy jednostkowe i integracyjne
- **📋 Production Ready** - Gotowe do użycia produkcyjnego

## 🆚 Dlaczego nowa wersja?

| Aspekt | Stara wersja (PyModbus) | **Nowa wersja (RTU)** |
|--------|-------------------------|----------------------|
| **Komunikacja z sprzętem** | ❌ Nie działała | ✅ **Działa niezawodnie** |
| **Auto-detekcja** | ❌ Zwracała błędy | ✅ **Znajduje urządzenia** |
| **Odczyt/zapis cewek** | ❌ Błędy komunikacji | ✅ **100% sprawne** |
| **Logowanie** | ❌ Niejasne błędy | ✅ **Szczegółowe logi** |
| **Testy** | ❌ Zawodne | ✅ **Wszystkie przechodzą** |
| **Dokumentacja** | ❌ Nieaktualna | ✅ **Kompletna + przykłady** |

## 🔧 Szybki start

### Wymagania
- Python 3.8+
- Urządzenie Modbus RTU podłączone do `/dev/ttyACM0` lub `/dev/ttyUSB0`
- Uprawnienia do portów szeregowych (dodaj użytkownika do grupy `dialout`)

### Instalacja

```bash
# Sklonuj repozytorium
git clone https://github.com/yourusername/modapi.git
cd modapi

# Utwórz środowisko wirtualne
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows

# Zainstaluj zależności
pip install -r requirements.txt
# lub użyj Poetry:
poetry install && poetry shell
```

### ⚡ Natychmiastowe uruchomienie

**1. Test komunikacji RTU:**
```bash
python -c "from api.rtu import ModbusRTU; client = ModbusRTU(); print('Config:', client.auto_detect())"
```

**2. Uruchom serwer web:**
```bash
python run_rtu_output.py
# Otwórz http://localhost:5005 w przeglądarce
```

**3. Przykłady użycia:**
```bash
python examples/rtu_usage.py
```

## 🧪 Development i testowanie

### Uruchom testy
```bash
# Wszystkie testy RTU
python -m pytest tests/test_rtu.py -v

# Z pokryciem kodu
python -m pytest tests/test_rtu.py --cov=api.rtu

# Test z rzeczywistym sprzętem (opcjonalny)
python -c "from tests.test_rtu import TestIntegration; TestIntegration().test_real_hardware_connection()"
```

### Debugowanie komunikacji
```bash
# Szczegółowe logi komunikacji
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from api.rtu import ModbusRTU
client = ModbusRTU()
config = client.auto_detect()
print('Debug config:', config)
"
```

### Budowanie i publikacja
```bash
# Budowa pakietu
poetry build

# Publikacja do PyPI
poetry publish --build
```

## 🔍 Troubleshooting

### Problem: Nie można znaleźć urządzenia
```bash
# Sprawdź dostępne porty szeregowe
ls -la /dev/tty{ACM,USB}*

# Sprawdź uprawnienia (dodaj użytkownika do grupy dialout)
sudo usermod -a -G dialout $USER
# Wyloguj się i zaloguj ponownie

# Test ręczny z różnymi prędkościami
python -c "
from api.rtu import ModbusRTU
for baud in [9600, 19200, 38400]:
    client = ModbusRTU('/dev/ttyACM0', baud)
    if client.connect():
        success, result = client.test_connection(1)
        print(f'{baud} baud: {success} - {result}')
        client.disconnect()
"
```

### Problem: Błędy komunikacji
```bash
# Sprawdź parametry szeregowe urządzenia w dokumentacji
# Typowe ustawienia: 8N1 (8 bitów danych, bez parzystości, 1 bit stopu)
# Może wymagać innych ustawień: 8E1, 8O1, itp.
```

   The simulator will start with these test values:
   - Coils 0-3: `[1, 0, 1, 0]`
   - Holding Registers 0-2: `[1234, 5678, 9012]`

4. Configure your `.env` file to use the virtual port:
   ```ini
   MODBUS_PORT=/tmp/ttyp0
   MODBUS_BAUDRATE=9600
   MODBUS_TIMEOUT=0.1
   ```

5. You can now run the API server or CLI commands to interact with the simulator.

## Usage

### Command Line Interface

The modapi CLI supports multiple subcommands:

```bash
# Direct command execution
modapi cmd wc 0 1       # Write value 1 to coil at address 0
modapi cmd rc 0 8       # Read 8 coils starting at address 0
modapi cmd rh 0 5       # Read 5 holding registers starting at address 0
modapi cmd wh 0 42      # Write value 42 to holding register at address 0

# Interactive shell
modapi shell

# REST API server
modapi rest --host 0.0.0.0 --port 5005

# MQTT client
modapi mqtt --broker localhost --port 1883

# Scan for Modbus devices
modapi scan

# With options
modapi cmd --verbose rc 0 8    # Verbose mode
modapi cmd --modbus-port /dev/ttyACM0 wc 0 1  # Specify port
```

For backward compatibility, you can also use the direct command format:
```bash
# These are automatically converted to the new format
./run_cli.py wc 0 1       # Equivalent to: modapi cmd wc 0 1
./run_cli.py rc 0 8       # Equivalent to: modapi cmd rc 0 8
```

### REST API

```python
from modapi.api.rest import create_rest_app

# Create and run Flask app
app = create_rest_app(port='/dev/ttyACM0', api_port=5005)
```

### 🌐 REST API Server

```bash
# Uruchom serwer RTU
python run_rtu_output.py

# API endpoints:
# GET  /status              - status połączenia RTU
# GET  /coil/<address>      - odczyt cewki
# POST /coil/<address>      - zapis cewki (JSON: {"state": true})
# GET  /coils               - odczyt wszystkich cewek 0-15
# GET  /registers/<address> - odczyt rejestru
```

### 📁 Przykłady curl

```bash
# Sprawdź status
curl http://localhost:5005/status

# Odczytaj cewkę 0
curl http://localhost:5005/coil/0

# Ustaw cewkę 0 na TRUE
curl -X POST http://localhost:5005/coil/0 \
     -H "Content-Type: application/json" \
     -d '{"state": true}'

# Odczytaj wszystkie cewki
curl http://localhost:5005/coils
```

### 🔧 Zaawansowane użycie

```python
from api.rtu import ModbusRTU
import time

# Niestandardowa konfiguracja
client = ModbusRTU(
    port='/dev/ttyACM0',
    baudrate=19200,
    timeout=2.0,
    parity='E',  # Even parity
    stopbits=1
)

if client.connect():
    # Monitorowanie zmian cewek
    previous_states = None
    
    for _ in range(10):  # Monitoruj przez 10 iteracji
        current_states = client.read_coils(1, 0, 4)
        
        if current_states and current_states != previous_states:
            print(f"{time.strftime('%H:%M:%S')} - Zmiana: {current_states}")
            previous_states = current_states
            
        time.sleep(1)
    
    client.disconnect()
```

### MQTT API

```python
from modapi.api.mqtt import start_mqtt_broker

# Start MQTT client
start_mqtt_broker(
    port='/dev/ttyACM0',
    broker='localhost',
    mqtt_port=1883,
    topic_prefix='modbus'
)
```

#### MQTT Topics

- Subscribe to `modbus/command/#` to send commands
- Subscribe to `modbus/request/#` to send requests
- Publish to `modbus/command/write_coil` with payload `{"address": 0, "value": true}` to write to a coil
- Publish to `modbus/request/read_coils` with payload `{"address": 0, "count": 8}` to read coils
- Results are published to `modbus/result/<command>` and `modbus/response/<request>`

### Direct API Usage

```python
from modapi.api.cmd import execute_command
from modapi.api.shell import interactive_mode

# Execute a command directly
success, response = execute_command('wc', ['0', '1'], port='/dev/ttyACM0')
print(response)

# Start interactive mode
interactive_mode(port='/dev/ttyACM0', verbose=True)
```

## Project Structure

```
modapi/
├── api/
│   ├── __init__.py    # Exports main API functions
│   ├── cmd.py         # Direct command execution
│   ├── mqtt.py        # MQTT broker client
│   ├── rest.py        # REST API Flask app
│   └── shell.py       # Interactive shell
├── client.py          # Modbus client implementation
├── __main__.py        # CLI entry point
└── ...
```



## Output Moduł [output.py]

Moduł [output](modapi/output.py:296:4-332:54) odpowiada za wizualizację i przetwarzanie stanów wyjść cyfrowych (cewek) w systemie Modbus. Zapewnia funkcje do parsowania i wyświetlania stanów wyjść w formie interaktywnego widżetu SVG.


### [parse_coil_status(text: str) -> Tuple[Optional[int], Optional[bool]]](modapi/output.py:18:0-33:21)
**Opis**:  
Parsuje wiadomość o stanie cewki i zwraca jej adres oraz status.

**Parametry**:
- `text` - Tekst wiadomości (np. 'Coil 0 set to ON' lub 'Coil 5 set to OFF')

**Zwraca**:
- Krotkę zawierającą:
  - `address` (int) - Adres cewki
  - [status](modapi/output.py:18:0-33:21) (bool) - Stan cewki (True = WŁĄCZONA, False = WYŁĄCZONA)

- [(None, None)](modapi/output.py:403:4-405:54) w przypadku błędu parsowania

**Przykład użycia**:
```python
address, status = parse_coil_status("Coil 3 set to ON")
# address = 3, status = True



## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.
