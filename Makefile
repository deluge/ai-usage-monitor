.PHONY: help correct check tests coverage coverage-html devinstall esp32 esp32-install esp32-update esp32-copy esp32-settings esp32-log clean

# Set MPREMOTE="mpremote connect /dev/cu.usbmodem1101" if more than one board is connected.
MPREMOTE ?= mpremote
# mpy-cross from your PATH, otherwise the one make devinstall put into .venv.
MPY_CROSS ?= $(if $(shell command -v mpy-cross),mpy-cross,uv run mpy-cross)

help:
	@echo "Development:"
	@echo "  devinstall       - Install all packages required for development into .venv"
	@echo "  correct          - Format python code with ruff"
	@echo "  check            - Check python code style without changing files"
	@echo "  tests            - Run tests (ARGS=\"-k monitor\" passes options to pytest)"
	@echo "  coverage         - Run tests with coverage enabled"
	@echo "  coverage-html    - Run tests with coverage html export enabled"
	@echo "  clean            - Clean build related files"
	@echo ""
	@echo "ESP32 (see README_ESP32_C3.md):"
	@echo "  esp32            - Compile the ESP32 code to .mpy files in build/esp32"
	@echo "  esp32-install    - First install: driver, code, main.py and settings.json"
	@echo "  esp32-update     - Copy the current code and main.py (keeps settings and credentials)"
	@echo "  esp32-settings   - Copy settings.json"
	@echo "  esp32-log        - Restart the board and show its log (Ctrl+] to exit)"


correct:
	uv run ruff check --fix .
	uv run ruff format .


check:
	uv run ruff format --check --diff .
	uv run ruff check .


tests:
	uv run py.test ${ARGS}


coverage:
	uv run py.test --cov ${ARGS}


coverage-html:
	uv run py.test --cov --cov-report=html ${ARGS}


devinstall:
	uv sync --locked --extra develop


# The ESP32 gets precompiled .mpy files: compiling .py files on the board needs
# memory that MicroPython never gives back, and then TLS runs out of memory.
esp32:
	rm -fr build/esp32/
	for file in $$(find display_usage -name '*.py' -not -path '*/pizerow/*'); do \
		mkdir -p build/esp32/$$(dirname $$file) && \
		$(MPY_CROSS) -o build/esp32/$${file%.py}.mpy $$file || exit 1; \
	done


# Your own files (see README_ESP32_C3.md): stop with a hint if one is missing.
main.py:
	@echo "main.py is missing: create it with the code from README_ESP32_C3.md (step 7)" >&2
	@exit 1


settings.json:
	@echo "settings.json is missing: copy settings.example.esp32.json and fill in your Wi-Fi (step 6)" >&2
	@exit 1


esp32-install: esp32 main.py settings.json
	$(MPREMOTE) mip install ssd1306
	$(MAKE) esp32-copy
	$(MPREMOTE) cp settings.json :settings.json + reset


esp32-update: esp32 main.py
	$(MAKE) esp32-copy
	$(MPREMOTE) reset


# Removes the old code first: MicroPython would load a leftover .py instead of the new .mpy.
esp32-copy:
	-$(MPREMOTE) rm -r :display_usage
	$(MPREMOTE) cp -r build/esp32/display_usage : + cp main.py :main.py


esp32-settings: settings.json
	$(MPREMOTE) cp settings.json :settings.json + reset


esp32-log:
	$(MPREMOTE) reset + repl


clean:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr htmlcov/
	rm -f .coverage
