#!/usr/bin/env python
"""
Skrypt pomocniczy do uruchamiania CLI modbusapi.
Zapewnia kompatybilność między różnymi środowiskami Pythona.
"""

import os
import sys
import subprocess

def main():
    """
    Główna funkcja uruchamiająca CLI modbusapi z odpowiednim interpreterem.
    """
    # Ścieżka do interpretera Python z zainstalowanym pymodbus
    python_path = "/home/linuxbrew/.linuxbrew/opt/python@3.11/bin/python3.11"
    
    # Sprawdź, czy interpreter istnieje
    if not os.path.exists(python_path):
        print(f"Interpreter {python_path} nie istnieje.")
        print("Próba użycia domyślnego interpretera...")
        python_path = sys.executable
    
    # Ścieżka do modułu shell.py
    module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              "modbusapi", "shell.py")
    
    # Sprawdź, czy moduł istnieje
    if not os.path.exists(module_path):
        print(f"Moduł {module_path} nie istnieje.")
        sys.exit(1)
    
    # Przekazanie argumentów do skryptu
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Uruchomienie skryptu z odpowiednim interpreterem
    cmd = [python_path, module_path] + args
    print(f"Uruchamianie: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"Błąd wykonania: {e}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
