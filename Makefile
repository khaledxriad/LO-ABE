# Convenience targets. Everything is also available as plain Python commands.
PY ?= python3

.PHONY: test data figures clean

test:            ## fast correctness tests (small lattice dimension)
	$(PY) tests/test_scheme.py
	$(PY) tests/test_data.py

data:            ## re-run the benchmarks (about 10 minutes); writes data/results.json
	$(PY) benchmarks/run_benchmarks.py --out data/results.json

figures:         ## PDF/PNG figures (matplotlib) and the two TikZ diagrams
	$(PY) figures/make_figures.py
	$(PY) figures/build_diagrams.py

clean:
	rm -rf figures/pdf
