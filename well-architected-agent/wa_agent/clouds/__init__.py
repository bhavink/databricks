"""Cloud registry. Each cloud package provides:

- ``tfplan.collect(doc)``: facts from ``terraform show -json`` (plan or state)
- ``live.collect(workspace, run=..., databricks_profile=..., account_profile=...)``:
  facts from a deployed workspace, read-only
- ``COLLECTION_HINTS``: fact namespace -> how to collect it when missing

The engine, catalog loader, report and MCP server never import a cloud
directly; they go through this registry.
"""

from __future__ import annotations

import importlib

CLOUDS = ("azure", "gcp", "aws")
SOURCES = ("tfplan", "live")


def _module(cloud: str, name: str):
    if cloud not in CLOUDS:
        raise ValueError(f"cloud {cloud!r} is not supported yet; supported: {', '.join(CLOUDS)}")
    return importlib.import_module(f"wa_agent.clouds.{cloud}.{name}" if name else f"wa_agent.clouds.{cloud}")


def collector(cloud: str, source: str):
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}; choose from {SOURCES}")
    return _module(cloud, source)


def collection_hints(cloud: str) -> dict[str, str]:
    return getattr(_module(cloud, ""), "COLLECTION_HINTS", {})
