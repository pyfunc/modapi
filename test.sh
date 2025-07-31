#!/bin/bash
# test.sh - Skrypt testowy dla ModbusAPI REST
# Testuje funkcjonalność przełączania (toggle) za pomocą curl

# Kolory do formatowania wyjścia
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Konfiguracja
API_URL="http://localhost:5000"
CHANNEL=0
TEST_COUNT=5
VERBOSE=true

# Funkcja do wyświetlania komunikatów
log() {
    local level=$1
    local message=$2
    
    case $level in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Funkcja do sprawdzania statusu API
check_api_status() {
    log "INFO" "Sprawdzanie statusu API..."
    
    local response=$(curl -s "$API_URL/status")
    
    if [[ $response == *"status"*"ok"* ]]; then
        log "SUCCESS" "API działa poprawnie: $response"
        return 0
    else
        log "ERROR" "API nie odpowiada poprawnie: $response"
        return 1
    fi
}

# Funkcja do odczytu stanu cewki
read_coil() {
    local channel=$1
    
    log "INFO" "Odczyt stanu cewki $channel..."
    
    local response=$(curl -s "$API_URL/coil/$channel")
    
    if [[ $VERBOSE == true ]]; then
        echo "Odpowiedź: $response"
    fi
    
    if [[ $response == *"value"* ]]; then
        local value=$(echo $response | grep -o '"value":[^,}]*' | cut -d':' -f2)
        log "SUCCESS" "Stan cewki $channel: $value"
        echo $value
    else
        log "ERROR" "Błąd odczytu cewki $channel: $response"
        echo "error"
    fi
}

# Funkcja do przełączania stanu cewki
toggle_coil() {
    local channel=$1
    
    log "INFO" "Przełączanie stanu cewki $channel..."
    
    local response=$(curl -s -X POST "$API_URL/toggle/$channel")
    
    if [[ $VERBOSE == true ]]; then
        echo "Odpowiedź: $response"
    fi
    
    if [[ $response == *"success"*"true"* ]]; then
        local prev_value=$(echo $response | grep -o '"previous_value":[^,}]*' | cut -d':' -f2)
        local new_value=$(echo $response | grep -o '"value":[^,}]*' | cut -d':' -f2)
        log "SUCCESS" "Przełączono cewkę $channel z $prev_value na $new_value"
        echo $new_value
    else
        log "ERROR" "Błąd przełączania cewki $channel: $response"
        echo "error"
    fi
}

# Funkcja do testowania przełączania
test_toggle() {
    local channel=$1
    local count=$2
    
    log "INFO" "Rozpoczynam test przełączania cewki $channel ($count iteracji)..."
    
    local success_count=0
    local initial_state=$(read_coil $channel)
    
    if [[ $initial_state == "error" ]]; then
        log "ERROR" "Nie można odczytać początkowego stanu cewki $channel"
        return 1
    fi
    
    log "INFO" "Początkowy stan cewki $channel: $initial_state"
    
    for ((i=1; i<=$count; i++)); do
        log "INFO" "Test $i z $count..."
        
        local before_toggle=$(read_coil $channel)
        local toggle_result=$(toggle_coil $channel)
        local after_toggle=$(read_coil $channel)
        
        if [[ $toggle_result != "error" && $before_toggle != "error" && $after_toggle != "error" ]]; then
            if [[ $before_toggle != $after_toggle ]]; then
                log "SUCCESS" "Test $i: Stan zmieniony z $before_toggle na $after_toggle"
                ((success_count++))
            else
                log "ERROR" "Test $i: Stan nie zmienił się ($before_toggle -> $after_toggle)"
            fi
        else
            log "ERROR" "Test $i: Błąd podczas testowania"
        fi
        
        # Krótka pauza między testami
        sleep 1
    done
    
    local success_rate=$(( $success_count * 100 / $count ))
    
    log "INFO" "Zakończono testy przełączania cewki $channel"
    log "INFO" "Udane testy: $success_count/$count ($success_rate%)"
    
    if [[ $success_rate -eq 100 ]]; then
        log "SUCCESS" "Wszystkie testy przełączania zakończone sukcesem!"
        return 0
    else
        log "WARNING" "Nie wszystkie testy przełączania zakończone sukcesem"
        return 1
    fi
}

# Funkcja do skanowania dostępnych urządzeń
scan_devices() {
    log "INFO" "Skanowanie dostępnych urządzeń Modbus..."
    
    local response=$(curl -s "$API_URL/scan")
    
    if [[ $response == *"devices"* ]]; then
        log "SUCCESS" "Znaleziono urządzenia: $response"
        return 0
    else
        log "ERROR" "Błąd skanowania urządzeń: $response"
        return 1
    fi
}

# Główna funkcja testowa
run_tests() {
    log "INFO" "Rozpoczynam testy ModbusAPI REST..."
    
    # Sprawdź status API
    if ! check_api_status; then
        log "ERROR" "API nie jest dostępne. Przerywam testy."
        exit 1
    fi
    
    # Skanuj dostępne urządzenia
    scan_devices
    
    # Testuj przełączanie
    test_toggle $CHANNEL $TEST_COUNT
    
    log "INFO" "Testy zakończone."
}

# Uruchom testy
run_tests
