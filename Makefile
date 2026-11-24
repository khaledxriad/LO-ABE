# Convenience targets. Everything is also available as plain Python commands.
PY ?= python3

.PHONY: test data microbench clean

test:            ## fast correctness tests (small lattice dimension)
	$(PY) tests/test_scheme.py
	$(PY) tests/test_data.py

data:            ## re-run the benchmarks (about 10 minutes); writes data/results.json
	$(PY) benchmarks/run_benchmarks.py --out data/results.json

microbench:      ## native C timing of the device step and local decryption
	gcc -O2 -o device_microbench benchmarks/device_microbench.c
	./device_microbench 32 128 32 80 16 200
