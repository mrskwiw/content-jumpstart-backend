#!/usr/bin/env python3
"""Type-error ratchet for ``backend/`` — the count may fall, never rise.

Why a ratchet and not a clean gate: ``backend/`` accumulated 796 mypy errors while
the quality gate only ever ran ``mypy src/``, so demanding zero would mean either a
huge blocking cleanup or (far more likely) the gate being switched off again. A
ratchet makes the debt *strictly decreasing* from day one, which is the property
that actually matters.

About 69% of the baseline is a single false-positive class: the models use legacy
``Column()` declarations rather than SQLAlchemy 2.0 ``Mapped[]``, so every
``obj.field = value`` looks like assigning ``str`` to ``Column[str]``. Those are not
bugs, and this tool does not pretend otherwise — it counts them so the number is
honest, and migrating the models is what will actually retire them.

The count is only meaningful against the mypy version that produced the baseline:
the same commit reports 795 errors under mypy 1.8.0 and 764 under 1.19.1 (BUGS #257).
So the baseline records its mypy version, and a run under any other version exits 2
rather than comparing incomparable numbers. CI pins the version in quality-gates.yml;
requirements.txt must pin the same one.

Usage:
    python scripts/mypy_ratchet.py            # check against the baseline
    python scripts/mypy_ratchet.py --update   # accept a NEW LOWER baseline
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_BASELINE = _ROOT / "scripts" / "mypy_baseline.json"
_TARGET = "backend/"
_SUMMARY = re.compile(r"Found (\d+) errors? in (\d+) files?")
_VERSION = re.compile(r"mypy (\d+(?:\.\d+)+)")


def measuring_python() -> str:
    """Return the interpreter whose mypy and packages define the count.

    The pre-commit hook runs as ``language: system``, so ``sys.executable`` is whatever
    ``python`` is first on PATH. On a dev box that is often a global interpreter without
    the project's packages, and mypy then treats those imports as ``Any`` and reports
    fewer errors (764 vs 779 under the same mypy; BUGS #257). Prefer the repo venv when
    it exists; CI has none and installs requirements.txt into its own interpreter.
    """
    for candidate in (_ROOT / "venv" / "Scripts" / "python.exe", _ROOT / "venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def parse_mypy_version(output: str) -> str:
    """Extract the version from ``mypy --version`` output. Exits 2 if there is none."""
    match = _VERSION.search(output)
    if match is None:
        print("Could not determine the mypy version:\n", output[-500:])
        raise SystemExit(2)
    return match.group(1)


def mypy_version() -> str:
    """Return the version of the mypy this interpreter would run."""
    proc = subprocess.run(
        [measuring_python(), "-m", "mypy", "--version"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    return parse_mypy_version(proc.stdout + proc.stderr)


def version_mismatch(running: str, pinned: str | None) -> str | None:
    """Return an explanation if ``running`` can't be compared to the baseline, else None."""
    if pinned is None:
        return (
            f"The baseline does not record a mypy version, so a count from mypy {running} "
            'cannot be compared to it. Add "mypy_version" to scripts/mypy_baseline.json.'
        )
    if running != pinned:
        return (
            f"mypy {running} is running, but the baseline was measured with mypy {pinned}. "
            "Different versions report different counts for the same code, so the "
            f"comparison would be meaningless. Install mypy=={pinned} "
            f"(e.g. `{measuring_python()} -m pip install mypy=={pinned}`) and rerun."
        )
    return None


def measure() -> tuple[int, int]:
    """Return ``(errors, files)`` from a mypy run. Exits non-zero only on a crash."""
    proc = subprocess.run(
        [measuring_python(), "-m", "mypy", "--no-incremental", _TARGET],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    if "Success: no issues found" in out:
        return 0, 0
    match = _SUMMARY.search(out)
    if match is None:
        # No summary line and no success line ⇒ mypy itself failed. Fail loudly
        # rather than reporting a misleading "0 errors".
        print("mypy did not produce a summary — it likely crashed:\n", out[-2000:])
        raise SystemExit(2)
    return int(match.group(1)), int(match.group(2))


def load_baseline() -> int | None:
    if not _BASELINE.exists():
        return None
    return int(json.loads(_BASELINE.read_text(encoding="utf-8"))["max_errors"])


def load_pinned_version() -> str | None:
    """Return the mypy version the baseline was measured with, if recorded."""
    if not _BASELINE.exists():
        return None
    version = json.loads(_BASELINE.read_text(encoding="utf-8")).get("mypy_version")
    return str(version) if version else None


def save_baseline(errors: int, files: int, version: str) -> None:
    _BASELINE.write_text(
        json.dumps(
            {
                "max_errors": errors,
                "files": files,
                "mypy_version": version,
                "note": (
                    "Ratchet ceiling for `mypy backend/`. May only ever decrease. "
                    "~69% of the original 796 are SQLAlchemy Column[...] false "
                    "positives from legacy Column() declarations; migrating the "
                    "models to Mapped[] is what retires them in bulk."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="accept a new lower baseline")
    args = parser.parse_args()

    running = mypy_version()
    baseline = load_baseline()

    if baseline is not None:
        problem = version_mismatch(running, load_pinned_version())
        if problem is not None:
            print(f"FAIL: {problem}")
            return 2

    errors, files = measure()

    if baseline is None:
        save_baseline(errors, files, running)
        print(f"Baseline created: {errors} errors in {files} files.")
        return 0

    if errors > baseline:
        print(
            f"FAIL: mypy backend/ has {errors} errors, ceiling is {baseline} "
            f"(+{errors - baseline}).\n"
            "Fix the new errors, or — if you genuinely lowered the count elsewhere — "
            "run: python scripts/mypy_ratchet.py --update"
        )
        return 1

    if errors < baseline:
        if args.update:
            save_baseline(errors, files, running)
            print(f"Baseline lowered: {baseline} -> {errors} errors ({files} files). Nice.")
            return 0
        # Not an automatic update: lowering the ceiling should be a deliberate,
        # reviewable change, or a lucky local environment silently ratchets it to
        # a level CI cannot reach.
        print(
            f"OK: {errors} errors, under the {baseline} ceiling. "
            f"Run with --update to lock in the improvement (-{baseline - errors})."
        )
        return 0

    print(f"OK: {errors} errors, exactly at the {baseline} ceiling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
