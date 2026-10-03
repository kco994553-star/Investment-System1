"""Producer Infrastructure v1. Contract, validation, freshness, assembly and persistence only.

This package performs no investment calculation. It validates, serializes and assembles
outputs that upstream owners produce, and fails closed when an output is missing,
synthetic-but-claimed-live, unverifiable, or not representable in the Web schema-1 contract.
See implementation/docs/producer_infrastructure/CONTRACT.md.
"""
