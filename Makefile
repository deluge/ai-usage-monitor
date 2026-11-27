.PHONY: help correct check tests coverage coverage-html devinstall esp32 clean

help:
	@echo "correct                    - Format python code with ruff"
	@echo "check                      - Check python code style without changing files"
	@echo "tests                      - Run tests"
	@echo "coverage                   - Run tests with coverage enabled"
	@echo "coverage-html              - Run tests with coverage html export enabled"
	@echo "devinstall                 - Install all packages required for development"
	@echo "esp32                      - Compile the ESP32 code to .mpy files in build/esp32 (needs mpy-cross)"
	@echo "clean                      - Clean build related files"


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
	uv pip install -e ".[develop]"


esp32:
	rm -fr build/esp32/
	for file in $$(find display_usage -name '*.py' -not -path '*/pizerow/*'); do \
		mkdir -p build/esp32/$$(dirname $$file) && \
		mpy-cross -o build/esp32/$${file%.py}.mpy $$file || exit 1; \
	done
	@echo "Copy to the board with: mpremote cp -r build/esp32/display_usage :"


clean:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr htmlcov/
