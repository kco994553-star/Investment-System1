"""QGV Real Producer v1: per-company persistence and export of the existing QGV engine output.

No QGV calculation lives here. `capture` observes the engine; `record` defines QGV_COMPANY_RESULT v1; `batch` runs
the Frozen Universe through the unchanged engine; `exporter` validates and writes; `infra_boundary` connects to
Producer Infrastructure v1 (read-only dependency). See implementation/docs/qgv_producer/CONTRACT.md.
"""
