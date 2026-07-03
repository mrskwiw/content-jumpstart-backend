import os
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20)

import backend.utils as utils_mod


def test_lazy_exports_are_loaded_and_cached():
    utils_mod.__dict__.pop("db_monitor", None)
    utils_mod.__dict__.pop("query_profiler", None)

    db_monitor_first = utils_mod.db_monitor
    db_monitor_second = utils_mod.db_monitor
    profiler_first = utils_mod.query_profiler
    profiler_second = utils_mod.query_profiler

    assert db_monitor_first is db_monitor_second
    assert profiler_first is profiler_second
    assert db_monitor_first.__name__.endswith("db_monitor")
    assert profiler_first.__name__.endswith("query_profiler")


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError):
        getattr(utils_mod, "not_a_real_helper")
