.PHONY: init-python precommit run-iot-mlops python-lock

# Setup Python toolchain globally using pipx
init-python:
	@echo "🔧 Installing Python tools with pipx..."
	@pipx --version >/dev/null 2>&1 || (echo "Installing pipx..." && brew install pipx && pipx ensurepath)
	@pipx list | grep 'uv' >/dev/null 2>&1 || pipx install uv
	@pipx list | grep 'poetry' >/dev/null 2>&1 || pipx install poetry
	@pipx list | grep 'ruff' >/dev/null 2>&1 || pipx install ruff
	@pipx list | grep 'pre-commit' >/dev/null 2>&1 || pipx install pre-commit

# Run format & pre-commit hooks
precommit:
	@echo "🎨 Formatting TOML files with taplo (if installed)..."
	@command -v taplo >/dev/null 2>&1 && taplo format || echo "⚠️  taplo not installed, skipping formatting"
	@echo "🔍 Running pre-commit hooks..."
	@pre-commit run --all-files

# Run the full IoT MLOps stack
run-iot-mlops:
	@echo "🚀 Running IoT MLOps Docker Compose..."
	docker compose -f docker/iot-mlops/compose.yaml up --build

# Lock all Python dependencies (uv + poetry)
python-lock:
	@echo "🔒 Locking dependencies for all Python packages..."
	@for dir in python/apps/* python/common ; do \
		if [ -f "$$dir/pyproject.toml" ]; then \
			echo "📦 Locking in $$dir..."; \
			(cd $$dir && uv lock && poetry lock) || true; \
		else \
			echo "⏭️  Skipping $$dir (no pyproject.toml)"; \
		fi \
	done
