PY ?= python
DST_ROOT ?= ../dontstarvetogether_dedicated_server

.PHONY: all resindex catalog catalog-sqlite catalog-index i18n farming-defs mechanism-index icons quality webcraft snap clean index-manifest

all: resindex catalog catalog-index i18n farming-defs quality

resindex:
	$(PY) devtools/build_resource_index.py --dst-root $(DST_ROOT)

catalog:
	$(PY) devtools/build_catalog_v2.py --dst-root $(DST_ROOT)

catalog-sqlite:
	$(PY) devtools/build_catalog_sqlite.py

catalog-index:
	$(PY) devtools/build_catalog_index.py

i18n:
	$(PY) devtools/build_i18n_index.py --dst-root $(DST_ROOT)

farming-defs:
	$(PY) devtools/build_farming_defs.py --dst-root $(DST_ROOT)

mechanism-index:
	$(PY) devtools/build_mechanism_index.py --dst-root $(DST_ROOT)

index-manifest:
	$(PY) devtools/build_index_manifest.py

icons:
	$(PY) devtools/build_icons.py --dst-root $(DST_ROOT) --all-elements --overwrite

quality:
	$(PY) devtools/quality_gate.py

webcraft:
	$(PY) devtools/serve_webcraft.py --host 0.0.0.0 --port 20000 --reload-catalog

snap:
	$(PY) devtools/snapshot.py --mode llm

clean:
	@echo "Nothing to clean; data/ artifacts are managed by build scripts."
