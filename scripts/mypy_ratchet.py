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


def measure() -> tuple[int, int]:
    """Return ``(errors, files)`` from a mypy run. Exits non-zero only on a crash."""
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", _TARGET],
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


def save_baseline(errors: int, files: int) -> None:
    _BASELINE.write_text(
        json.dumps(
            {
                "max_errors": errors,
                "files": files,
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

    errors, files = measure()
    baseline = load_baseline()

    if baseline is None:
        save_baseline(errors, files)
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
            save_baseline(errors, files)
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
