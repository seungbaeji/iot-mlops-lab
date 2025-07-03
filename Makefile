.PHONY: init-python precommit run-iot-mlops python-lock

init-python:
	brew install pipx
	pipx ensurepath
	/bin/zsh -c "source ~/.zshrc"

	# install the tools
	pipx install uv
	pipx install poetry
	pipx install ruff
	pipx install pre-commit

precommit:
	@taplo format > /dev/null 2>&1 || true
	@pre-commit run --all-files

run-iot-mlops:
	docker compose -f docker/iot-mlops/compose.yaml up --build;

python-lock:
	@echo "Locking uv & poetry dependencies for all Python apps..."
	@for dir in python/apps/* python/common ; do \
		if [ -f "$$dir/pyproject.toml" ]; then \
			echo "🔒 Locking in $$dir..."; \
			(cd $$dir && uv lock && poetry lock); \
		else \
			echo "⏭️ Skipping $$dir (no pyproject.toml)"; \
		fi \
	done
