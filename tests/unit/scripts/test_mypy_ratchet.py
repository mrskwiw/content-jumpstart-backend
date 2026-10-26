"""Tests for scripts/mypy_ratchet.py — the backend type-error ratchet.

BUGS #257: the ratchet compares an error COUNT, and different mypy versions report
different counts for the same code (1.8.0 → 795, 1.19.1 → 764 on the same commit).
The gate must refuse to compare a count measured with a different mypy than the one
the baseline was recorded with, instead of silently passing or failing.
"""

import importlib.util
import json
import pathlib

import pytest

_SCRIPT = pathlib.Path(__file__).resolve().parents[3] / "scripts" / "mypy_ratchet.py"


@pytest.fixture
def ratchet(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("mypy_ratchet", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_BASELINE", tmp_path / "mypy_baseline.json")
    monkeypatch.setattr("sys.argv", ["mypy_ratchet.py"])
    return module


def _write_baseline(ratchet, max_errors, version):
    data = {"max_errors": max_errors, "files": 80}
    if version is not None:
        data["mypy_version"] = version
    ratchet._BASELINE.write_text(json.dumps(data), encoding="utf-8")


class TestVersionMismatch:
    def test_same_version_is_ok(self, ratchet):
        assert ratchet.version_mismatch("1.19.1", "1.19.1") is None

    def test_different_version_reports_both(self, ratchet):
        msg = ratchet.version_mismatch("1.8.0", "1.19.1")
        assert msg is not None
        assert "1.8.0" in msg and "1.19.1" in msg

    def test_unpinned_baseline_is_a_mismatch(self, ratchet):
        # A baseline without a recorded version can't be compared safely either.
        assert ratchet.version_mismatch("1.19.1", None) is not None


class TestMainVersionGuard:
    def test_mismatch_exits_2_without_measuring(self, ratchet, monkeypatch, capsys):
        _write_baseline(ratchet, 782, "1.19.1")
        monkeypatch.setattr(ratchet, "mypy_version", lambda: "1.8.0")

        def _must_not_run():
            raise AssertionError("measure() ran despite a version mismatch")

        monkeypatch.setattr(ratchet, "measure", _must_not_run)
        assert ratchet.main() == 2
        assert "1.19.1" in capsys.readouterr().out

    def test_matching_version_under_ceiling_passes(self, ratchet, monkeypatch):
        _write_baseline(ratchet, 782, "1.19.1")
        monkeypatch.setattr(ratchet, "mypy_version", lambda: "1.19.1")
        monkeypatch.setattr(ratchet, "measure", lambda: (764, 78))
        assert ratchet.main() == 0

    def test_matching_version_over_ceiling_fails(self, ratchet, monkeypatch):
        _write_baseline(ratchet, 782, "1.19.1")
        monkeypatch.setattr(ratchet, "mypy_version", lambda: "1.19.1")
        monkeypatch.setattr(ratchet, "measure", lambda: (790, 80))
        assert ratchet.main() == 1


class TestBaselineRecordsVersion:
    def test_update_records_running_version(self, ratchet, monkeypatch):
        _write_baseline(ratchet, 782, "1.19.1")
        monkeypatch.setattr(ratchet, "mypy_version", lambda: "1.19.1")
        monkeypatch.setattr(ratchet, "measure", lambda: (764, 78))
        monkeypatch.setattr("sys.argv", ["mypy_ratchet.py", "--update"])
        assert ratchet.main() == 0
        saved = json.loads(ratchet._BASELINE.read_text(encoding="utf-8"))
        assert saved["max_errors"] == 764
        assert saved["mypy_version"] == "1.19.1"


class TestInterpreterSelection:
    """The pre-commit hook is `language: system`, so `python` is whatever is first on
    PATH — on a dev box that's a global interpreter without the project's packages,
    which undercounts (764 vs 779 under the same mypy). The script must measure with
    the repo venv when one exists, and fall back to its own interpreter (CI)."""

    def test_prefers_repo_venv_when_present(self, ratchet, tmp_path, monkeypatch):
        venv_py = tmp_path / "venv" / "Scripts" / "python.exe"
        venv_py.parent.mkdir(parents=True)
        venv_py.write_text("")
        monkeypatch.setattr(ratchet, "_ROOT", tmp_path)
        assert ratchet.measuring_python() == str(venv_py)

    def test_prefers_posix_venv_layout(self, ratchet, tmp_path, monkeypatch):
        venv_py = tmp_path / "venv" / "bin" / "python"
        venv_py.parent.mkdir(parents=True)
        venv_py.write_text("")
        monkeypatch.setattr(ratchet, "_ROOT", tmp_path)
        assert ratchet.measuring_python() == str(venv_py)

    def test_falls_back_to_current_interpreter(self, ratchet, tmp_path, monkeypatch):
        import sys

        monkeypatch.setattr(ratchet, "_ROOT", tmp_path)  # no venv/ here
        assert ratchet.measuring_python() == sys.executable


class TestMeasureIsCacheIndependent:
    def test_measure_disables_incremental_cache(self, ratchet, monkeypatch):
        # .mypy_cache is shared by every interpreter that runs mypy in the repo; a run
        # under a package-poor interpreter poisoned it and the venv then reported 756
        # instead of 778 for unchanged code (BUGS #257). A count gate can't use it.
        seen = {}

        class _Proc:
            stdout = "Found 5 errors in 2 files (checked 10 source files)\n"
            stderr = ""

        def _run(cmd, **kwargs):
            seen["cmd"] = cmd
            return _Proc()

        monkeypatch.setattr(ratchet.subprocess, "run", _run)
        assert ratchet.measure() == (5, 2)
        assert "--no-incremental" in seen["cmd"]


class TestMypyVersionParse:
    def test_parses_version_string(self, ratchet):
        assert ratchet.parse_mypy_version("mypy 1.19.1 (compiled: yes)\n") == "1.19.1"

    def test_unparseable_output_exits_2(self, ratchet):
        with pytest.raises(SystemExit) as exc:
            ratchet.parse_mypy_version("No module named mypy")
        assert exc.value.code == 2
