.PHONY: check contracts
check:
	uv run --locked python -m unittest discover -s tests -v
	uv run --locked python -m eu_compliance_guard.schema --check
	npm --prefix frontend run types:check
	npm --prefix frontend run check
contracts:
	uv run --locked python -m eu_compliance_guard.schema
	npm --prefix frontend run types
