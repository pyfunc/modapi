#!/usr/bin/env python3
"""
Przykład użycia nowego modułu api.rtu
Zastępuje funkcjonalność client.py i output.py
"""

import logging
import time
from modapi.api.rtu import ModbusRTU, create_rtu_client, test_rtu_connection


def example_basic_usage():
    """Podstawowe użycie modułu RTU"""
    print("=== Podstawowe użycie modułu RTU ===")
    
    # Szybki test połączenia
    success, result = test_rtu_connection('/dev/ttyACM0', 9600, 1)
    if success:
        print(f"Połączenie OK: {result}")
    else:
        print(f"Błąd połączenia: {result}")
    
    # Utworzenie klienta RTU
    client = create_rtu_client('/dev/ttyACM0', 9600, 1.0)
    
    if client.connect():
        print("Połączono z urządzeniem Modbus")
        
        # Odczyt cewek
        coils = client.read_coils(1, 0, 8)
        if coils:
            print(f"Cewki 0-7: {coils}")
        
        # Zapis pojedynczej cewki
        if client.write_single_coil(1, 0, True):
            print("Ustawiono cewkę 0 na TRUE")
        
        client.disconnect()
    else:
        print("Nie udało się połączyć")


def example_auto_detection():
    """Przykład automatycznego wykrywania konfiguracji"""
    print("=== Automatyczne wykrywanie konfiguracji ===")
    
    client = ModbusRTU()
    
    # Auto-wykrywanie z domyślnymi portami i prędkościami
    config = client.auto_detect()
    
    if config:
        print(f"Znaleziono konfigurację: {config}")
        
        # Użyj znalezionej konfiguracji
        unit_id = config['unit_id']
        
        # Test operacji
        coils = client.read_coils(unit_id, 0, 4)
        print(f"Pierwsze 4 cewki: {coils}")
        
    else:
        print("Nie znaleziono działającej konfiguracji")


def example_context_manager():
    """Przykład użycia z context managerem"""
    print("=== Context Manager ===")
    
    with ModbusRTU('/dev/ttyACM0', 9600) as client:
        # Test połączenia
        success, info = client.test_connection(1)
        if success:
            print("Połączenie OK, wykonuję operacje...")
            
            # Odczyt i zapis cewek
            original_coils = client.read_coils(1, 0, 4)
            print(f"Oryginalne stany cewek: {original_coils}")
            
            # Ustaw wszystkie cewki na przeciwny stan
            if original_coils:
                for i, state in enumerate(original_coils):
                    client.write_single_coil(1, i, not state)
                    
                # Sprawdź zmiany
                new_coils = client.read_coils(1, 0, 4)
                print(f"Nowe stany cewek: {new_coils}")
                
                # Przywróć oryginalne stany
                for i, state in enumerate(original_coils):
                    client.write_single_coil(1, i, state)
                    
        else:
            print(f"Błąd połączenia: {info}")
    # Automatyczne rozłączenie przy wyjściu z bloku


def example_monitoring():
    """Przykład monitorowania cewek"""
    print("=== Monitorowanie cewek ===")
    
    client = ModbusRTU('/dev/ttyACM0', 9600)
    
    if client.connect():
        print("Rozpoczynam monitorowanie cewek (Ctrl+C aby przerwać)")
        
        try:
            previous_states = None
            
            while True:
                # Odczytaj stany cewek
                current_states = client.read_coils(1, 0, 8)
                
                if current_states:
                    # Sprawdź czy są zmiany
                    if previous_states != current_states:
                        print(f"{time.strftime('%H:%M:%S')} - Cewki: {current_states}")
                        
                        # Pokaż które cewki się zmieniły
                        if previous_states:
                            for i, (prev, curr) in enumerate(zip(previous_states, current_states)):
                                if prev != curr:
                                    status = "ON" if curr else "OFF"
                                    print(f"  Cewka {i}: {status}")
                        
                        previous_states = current_states
                
                time.sleep(1)  # Odczyt co sekundę
                
        except KeyboardInterrupt:
            print("\nPrzerwano monitorowanie")
            
        finally:
            client.disconnect()


def example_advanced_operations():
    """Zaawansowane operacje Modbus"""
    print("=== Zaawansowane operacje ===")
    
    with ModbusRTU('/dev/ttyACM0', 9600) as client:
        # Test połączenia z różnymi unit ID
        for unit_id in [1, 2, 3]:
            success, result = client.test_connection(unit_id)
            if success:
                print(f"Jednostka {unit_id}: OK")
                
                # Test różnych operacji
                print(f"  Testowanie operacji dla jednostki {unit_id}")
                
                # Odczyt cewek
                coils = client.read_coils(unit_id, 0, 8)
                if coils:
                    print(f"  Cewki 0-7: {coils}")
                
                # Próba odczytu rejestrów (może nie działać na wszystkich urządzeniach)
                registers = client.read_holding_registers(unit_id, 0, 4)
                if registers:
                    print(f"  Rejestry 0-3: {registers}")
                else:
                    print("  Rejestry: niedostępne (błąd Modbus)")
                
                # Test zapisu rejestru
                if client.write_single_register(unit_id, 0, 1234):
                    print("  Zapis rejestru: OK")
                else:
                    print("  Zapis rejestru: BŁĄD")
                    
            else:
                print(f"Jednostka {unit_id}: BRAK")


def example_error_handling():
    """Przykład obsługi błędów"""
    print("=== Obsługa błędów ===")
    
    # Test z nieistniejącym portem
    client = ModbusRTU('/dev/ttyNONEXISTENT', 9600)
    
    if not client.connect():
        print("Oczekiwany błąd: nie udało się połączyć z nieistniejącym portem")
    
    # Test z istniejącym portem
    client = ModbusRTU('/dev/ttyACM0', 9600)
    
    if client.connect():
        # Test z nieprawidłowym unit ID
        success, result = client.test_connection(99)  # Prawdopodobnie nieistniejący
        if not success:
            print(f"Oczekiwany błąd dla unit ID 99: {result['error']}")
        
        # Test odczytu zbyt dużej liczby cewek
        coils = client.read_coils(1, 0, 5000)  # Za dużo
        if coils is None:
            print("Oczekiwany błąd: zbyt duża liczba cewek")
        
        client.disconnect()


if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO)
    
    print("Demonstracja nowego modułu api.rtu")
    print("Zastępuje client.py i output.py z pymodbus\n")
    
    # Uruchom przykłady
    example_basic_usage()
    print()
    
    example_auto_detection()
    print()
    
    example_context_manager()
    print()
    
    example_advanced_operations()
    print()
    
    example_error_handling()
    print()
    
    print("Dostępne jest również monitorowanie:")
    print("python examples/rtu_usage.py --monitor")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--monitor':
        example_monitoring()
