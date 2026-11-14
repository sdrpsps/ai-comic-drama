DS ?= all

.PHONY: dev

dev:
	uv run langgraph dev --no-browser
