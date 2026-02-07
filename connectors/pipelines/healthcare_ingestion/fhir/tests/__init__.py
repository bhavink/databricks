"""
FHIR Pipeline Tests

Comprehensive test suite for FHIR ingestion pipeline.
Tests follow TDD approach: tests are written BEFORE implementation.

Test Categories:
- Unit tests: Individual function testing
- Schema validation tests: FHIR R4 compliance
- Error handling tests: Quarantine logic
- Integration tests: End-to-end pipeline validation

Run tests:
    pytest -v tests/
    pytest -v tests/ --cov=transformations --cov-report=html
"""
