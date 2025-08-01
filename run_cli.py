#!/usr/bin/env python
"""
Skrypt pomocniczy do uruchamiania CLI modapi.
Zapewnia kompatybilność między różnymi środowiskami Pythona.
"""

import os
import sys
import subprocess

def main():
    """
    Główna funkcja uruchamiająca CLI modapi z odpowiednim interpreterem.
    """
    # Ścieżka do interpretera Python z zainstalowanym pymodbus
    python_path = "/home/linuxbrew/.linuxbrew/opt/python@3.11/bin/python3.11"
    
    # Sprawdź, czy interpreter istnieje
    if not os.path.exists(python_path):
        print(f"Interpreter {python_path} nie istnieje.")
        print("Próba użycia domyślnego interpretera...")
        python_path = sys.executable
    
    # Katalog główny projektu (gdzie znajduje się pakiet modapi)
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Ścieżka do skryptu CLI w katalogu scripts
    script_path = os.path.join(project_root, "scripts", "modapi")
    
    # Sprawdź, czy skrypt istnieje
    if not os.path.exists(script_path):
        print(f"Skrypt {script_path} nie istnieje.")
        sys.exit(1)
    
    # Przekazanie argumentów do skryptu
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Uruchomienie skryptu CLI
    cmd = [python_path, script_path] + args
    print(f"Uruchamianie: {' '.join(cmd)}")
    
    # Dodanie katalogu projektu do PYTHONPATH
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = project_root
    
    try:
        result = subprocess.run(cmd, check=True, env=env)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"Błąd wykonania: {e}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
