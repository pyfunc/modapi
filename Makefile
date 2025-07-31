.PHONY: install dev-install test lint clean build publish publish-test check-version run-rest run-mqtt run-cli help

# Default target
help:
	@echo "ModbusAPI Makefile"
	@echo ""
	@echo "Dostępne komendy:"
	@echo "  make install       - Instalacja paczki modbusapi"
	@echo "  make dev-install   - Instalacja paczki w trybie developerskim"
	@echo "  make test          - Uruchomienie testów jednostkowych"
	@echo "  make lint          - Sprawdzenie kodu pod kątem błędów stylistycznych"
	@echo "  make clean         - Usunięcie plików tymczasowych i artefaktów"
	@echo "  make build         - Zbudowanie paczki do dystrybucji"
	@echo "  make publish       - Publikacja paczki w PyPI"
	@echo "  make publish-test  - Publikacja paczki w TestPyPI"
	@echo "  make check-version - Sprawdzenie czy wersja paczki jest unikalna w PyPI"
	@echo "  make run-rest      - Uruchomienie serwera REST API"
	@echo "  make run-mqtt      - Uruchomienie serwera MQTT"
	@echo "  make run-cli       - Uruchomienie interfejsu CLI"
	@echo "  make integration-test - Uruchomienie testów integracyjnych"

# Instalacja paczki
install:
	pip install .

# Instalacja paczki w trybie developerskim
dev-install:
	pip install -e ".[dev]"

# Uruchomienie testów jednostkowych
test:
	pytest modbusapi/tests/

# Sprawdzenie kodu pod kątem błędów stylistycznych
lint:
	flake8 modbusapi/
	pylint modbusapi/

# Usunięcie plików tymczasowych i artefaktów
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} +

# Zbudowanie paczki do dystrybucji
build: clean
	python setup.py sdist bdist_wheel

# Sprawdzenie czy wersja paczki jest unikalna w PyPI
check-version:
	@echo "Sprawdzanie wersji paczki..."
	@python -c "import requests, json, pkg_resources; pkg = pkg_resources.get_distribution('modbusapi'); current = pkg.version; resp = requests.get('https://pypi.org/pypi/modbusapi/json'); versions = list(json.loads(resp.text)['releases'].keys()) if resp.status_code == 200 else []; print(f'Aktualna wersja: {current}'); print(f'Wersje w PyPI: {versions}'); exit(1 if current in versions else 0)" || (echo "BŁĄD: Wersja już istnieje w PyPI. Zaktualizuj wersję w setup.py." && exit 1)
	@echo "Wersja jest unikalna, można publikować."

# Publikacja paczki w TestPyPI
publish-test: build
	@echo "Publikowanie w TestPyPI..."
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
	@echo "Paczka opublikowana w TestPyPI. Możesz ją zainstalować używając:"
	@echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple modbusapi"

# Publikacja paczki w PyPI
publish: check-version build
	@echo "Publikowanie w PyPI..."
	twine upload dist/*
	@echo "Paczka opublikowana w PyPI. Możesz ją zainstalować używając:"
	@echo "pip install modbusapi"

# Uruchomienie serwera REST API
run-rest:
	python -m modbusapi.api

# Uruchomienie serwera MQTT
run-mqtt:
	python -m modbusapi.mqtt

# Uruchomienie interfejsu CLI
run-cli:
	python -m modbusapi.shell

# Uruchomienie testów integracyjnych
integration-test:
	bash ../test.sh
