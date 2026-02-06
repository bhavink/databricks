# Connector Development Workflow

---

## Quick Start

```bash
# 1. Setup
cd connectors
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run tests
pytest sources/healthcare/test/ -v

# 3. Test in Databricks
# Upload notebooks/ to workspace and run
```

---

## Development Phases

| Phase | Output | Gate |
|-------|--------|------|
| 0. Planning | `DESIGN.md` | Scope approved |
| 1. Research | `{connector}_api_doc.md` | API documented |
| 2. Implement | `lakeflow_connect.py` | Tests pass |
| 3. Test | Databricks notebook | Works in cluster |
| 4. Document | `README.md` | User docs complete |

---

## Connector Status

| Connector | P0 | P1 | P2 | P3 | P4 | Status |
|-----------|----|----|----|----|-----|--------|
| healthcare | ✅ | ✅ | ✅ | ✅ | ⏳ | Ready for README |

---

## Testing Checklist

### Local
- [ ] `pytest sources/{connector}/test/ -v` passes
- [ ] No credentials committed

### Databricks
- [ ] Notebook runs without errors
- [ ] Data displays correctly
- [ ] UC Volumes accessible

---

## Key Files

| File | Purpose |
|------|---------|
| `sources/{connector}/lakeflow_connect.py` | Main connector code |
| `sources/{connector}/test/` | Pytest tests |
| `notebooks/` | Databricks test notebooks |
| `requirements.txt` | Python dependencies |
