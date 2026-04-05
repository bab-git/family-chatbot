SHELL := /bin/sh

.PHONY: help env sync ensure-key setup models run mock test check-uv check-venv check-ollama

help:
	@printf "%s\n" \
		"make setup   Create .env if needed, install dependencies, and generate a local LANGGRAPH_AES_KEY" \
		"make models  Pull the configured Ollama chat and guard models" \
		"make run     Start the app with Ollama" \
		"make mock    Start the app in mock mode" \
		"make test    Run the test suite"

check-uv:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "uv is not installed or not on PATH."; \
		exit 1; \
	fi

check-venv:
	@if [ ! -x .venv/bin/python ]; then \
		echo "Local virtual environment is missing. Run 'make setup' first."; \
		exit 1; \
	fi

check-ollama:
	@if ! command -v ollama >/dev/null 2>&1; then \
		echo "Ollama is not installed or not on PATH."; \
		exit 1; \
	fi

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	else \
		echo ".env already exists"; \
	fi

sync: check-uv
	uv sync

ensure-key: check-venv
	@key="$$(awk '/^LANGGRAPH_AES_KEY=/{ line = $$0; sub(/^[^=]*=/, "", line); print line }' .env)"; \
	if [ "$${#key}" -ne 16 ] && [ "$${#key}" -ne 24 ] && [ "$${#key}" -ne 32 ]; then \
		new_key="$$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(16))')"; \
		tmp_file="$$(mktemp)"; \
		awk -v new_key="$$new_key" 'BEGIN { updated = 0 } /^LANGGRAPH_AES_KEY=/ { print "LANGGRAPH_AES_KEY=" new_key; updated = 1; next } { print } END { if (!updated) print "LANGGRAPH_AES_KEY=" new_key }' .env > "$$tmp_file" && mv "$$tmp_file" .env; \
		echo "Generated a local LANGGRAPH_AES_KEY in .env"; \
	else \
		echo "LANGGRAPH_AES_KEY already looks valid"; \
	fi

setup:
	@$(MAKE) env
	@$(MAKE) sync
	@$(MAKE) ensure-key
	@printf "%s\n" "" "Setup complete." "Next steps:" "  make mock" "  make models" "  make run"

models: check-venv check-ollama
	@chat_model="$$(.venv/bin/python -c 'from family_chat.config import CHAT_MODEL; print(CHAT_MODEL)')"; \
	guard_model="$$(.venv/bin/python -c 'from family_chat.config import GUARD_MODEL; print(GUARD_MODEL)')"; \
		echo "Pulling $$chat_model..."; \
		ollama pull "$$chat_model"; \
		if [ -n "$$guard_model" ] && [ "$$guard_model" != "$$chat_model" ]; then \
			echo "Pulling $$guard_model..."; \
			ollama pull "$$guard_model"; \
		fi

run: check-venv
	.venv/bin/python -m family_chat.server

mock: check-venv
	FAMILY_CHAT_MOCK_OLLAMA=1 .venv/bin/python -m family_chat.server

test: check-venv
	.venv/bin/python -m unittest discover -s tests -v
