.PHONY: help correct check devinstall clean

help:
	@echo "correct                    - Format python code with ruff"
	@echo "check                      - Check python code style without changing files"
	@echo "devinstall                 - Install all packages required for development"
	@echo "clean                      - Clean build related files"


correct:
	uv run ruff check --fix .
	uv run ruff format .


check:
	uv run ruff format --check --diff .
	uv run ruff check .


devinstall:
	uv pip install -e ".[develop]"


clean:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
