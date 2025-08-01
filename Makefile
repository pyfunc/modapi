.PHONY: install dev test lint clean build publish publish-test check-version run-rest run-mqtt run-cli help

# Default target
help:
	@echo "modapi Makefile (Poetry)"
	@echo ""
	@echo "Dostępne komendy:"
	@echo "  make install    - Instalacja paczki modapi"
	@echo "  make dev        - Instalacja zależności developerskich"
	@echo "  make test       - Uruchomienie testów jednostkowych"
	@echo "  make lint       - Sprawdzenie kodu pod kątem błędów stylistycznych"
	@echo "  make clean      - Usunięcie plików tymczasowych i artefaktów"
	@echo "  make build      - Zbudowanie paczki do dystrybucji"
	@echo "  make publish    - Publikacja paczki w PyPI"
	@echo "  make check-version - Sprawdzenie czy wersja paczki jest unikalna w PyPI"
	@echo "  make run-rest   - Uruchomienie serwera REST API"
	@echo "  make run-mqtt   - Uruchomienie serwera MQTT"
	@echo "  make run-cli    - Uruchomienie interfejsu CLI"

# Instalacja paczki
install:
	poetry install --only main

# Instalacja zależności developerskich
dev:
	poetry install --with dev

# Uruchomienie testów jednostkowych
test:
	poetry run pytest tests/

# Sprawdzenie kodu pod kątem błędów stylistycznych
lint:
	poetry run flake8 modapi/
	poetry run pylint modapi/

# Usunięcie plików tymczasowych i artefaktów
clean:
	poetry run python -m pip cache purge
	poetry env remove --all
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -f .coverage
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} +

# Sprawdzenie wersji
version:
	@echo "Aktualna wersja:"
	@poetry version

# Inkrementacja wersji patch
bump-patch:
	poetry version patch

# Inkrementacja wersji minor
bump-minor:
	poetry version minor

# Inkrementacja wersji major
bump-major:
	poetry version major

# Zbudowanie paczki do dystrybucji
build: clean
	pip install -e .
	poetry build

# Sprawdzenie czy wersja jest gotowa do publikacji
check-version:
	@echo "Sprawdzanie wersji..."
	@poetry version
	@echo "Upewnij się, że wersja jest unikalna przed publikacją."

# Publikacja paczki w PyPI
publish: check-version bump-patch build
	@echo "Publikowanie w PyPI..."
	poetry publish

# Publikacja paczki w TestPyPI
publish-test: check-version build
	@echo "Publikowanie w TestPyPI..."
	poetry publish --build -r testpypi
	@echo "\nPaczka opublikowana w TestPyPI. Możesz ją zainstalować używając:"
	@echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple modapi"

# Uruchomienie serwera REST API
run-rest:
	python -m modapi.api

# Uruchomienie serwera MQTT
run-mqtt:
	python -m modapi.mqtt

# Uruchomienie interfejsu CLI
run-cli:
	python -m modapi.shell

# Uruchomienie testów integracyjnych
integration-test:
	bash ../test.sh
