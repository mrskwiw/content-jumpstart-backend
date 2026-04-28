"""Backend package bootstrap."""

from __future__ import annotations

import importlib
import sys


def _alias_legacy_package(name: str) -> None:
    module = importlib.import_module(f"backend.{name}")
    sys.modules.setdefault(name, module)


for _package_name in ("utils", "routers"):
    _alias_legacy_package(_package_name)
