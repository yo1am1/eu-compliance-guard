.PHONY: check contracts plugin-check verify-hosts eval
check:
	uv run --locked python -m unittest discover -s tests -v
	uv run --locked python -m eu_compliance_guard.schema --check
contracts:
	uv run --locked python -m eu_compliance_guard.schema
semantic-check:
	uv run --locked --extra semantic python -m eu_compliance_guard semantic setup
	EUCG_SEMANTIC=on uv run --locked --extra semantic python -m unittest discover -s tests -p 'test_semantic.py' -v
	EUCG_SEMANTIC=on uv run --locked --extra semantic python -m eu_compliance_guard.evaluation
plugin-check:
	claude plugin validate .
	claude plugin test .
verify-hosts:
	uv run --locked --no-dev python scripts/verify_hosts.py --consent
eval:
	uv run --locked python -m eu_compliance_guard.evaluation
