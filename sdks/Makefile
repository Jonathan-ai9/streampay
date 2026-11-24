PYTHON ?= python3
VECTORS_BUILDER := vectors/builder
TS_DIR := typescript
RUST_DIR := rust
PYTHON_DIR := python

.PHONY: help spec generate check check-spec vectors test test-python test-rust publish-dry-run clean

help:
	@echo "spec              re-derive spec/streampay.spec.json + FINGERPRINT from the contract"
	@echo "generate          run every language emitter whose package is present"
	@echo "check             schema guard + spec/vector/catalog tests + generated-output drift"
	@echo "check-spec        schema guard + tests only"
	@echo "vectors           rebuild conformance vectors (deterministic)"
	@echo "test              TypeScript SDK: typecheck, build, tests (incl. vectors)"
	@echo "test-python       Python SDK: install package + conformance/runtime tests"
	@echo "test-rust         Rust SDK: conformance vectors + doctests"
	@echo "publish-dry-run   npm pack --dry-run for the TypeScript SDK (no upload)"

spec:
	$(PYTHON) generator/check_contract_surface.py --write-spec

generate:
	$(PYTHON) generator/generate.py

check-spec:
	$(PYTHON) generator/check_contract_surface.py
	$(PYTHON) -m unittest discover -s generator -p "test_*.py" -v

check: check-spec
	$(PYTHON) generator/generate.py --check

vectors:
	cd $(VECTORS_BUILDER) && npm ci && node build-vectors.mjs

test:
	cd $(TS_DIR) && npm ci && npm run typecheck && npm test

test-python:
	$(PYTHON) -m pip install ./$(PYTHON_DIR)
	$(PYTHON) -m unittest discover -s $(PYTHON_DIR)/tests -v

test-rust:
	cd $(RUST_DIR) && cargo test

publish-dry-run:
	cd $(TS_DIR) && npm pack --dry-run

clean:
	rm -rf $(TS_DIR)/dist $(TS_DIR)/*.tgz $(PYTHON_DIR)/build $(PYTHON_DIR)/dist $(PYTHON_DIR)/*.egg-info $(PYTHON_DIR)/src/*.egg-info
