#!/usr/bin/env python3
"""
Rebuild lambda_package/ from the current source tree.

infra/failure_propagation_infra/stack.py deploys the Analyzer Lambda from
<repo>/lambda_package (see `lambda_package_dir`), NOT directly from lambdas/.
That folder is gitignored, so it goes stale whenever lambdas/ or engine/ change.
Run this after editing either, then `cdk synth` / `cdk deploy` from infra/.

Handler is "lambdas.failure_propagation.handler.lambda_handler", so the package
root needs:

    lambda_package/
      lambdas/__init__.py
      lambdas/failure_propagation/__init__.py
      lambdas/failure_propagation/handler.py
      engine/__init__.py
      engine/{analysis,health_rules,impact,propagation}.py

boto3 (the only entry in lambdas/failure_propagation/requirements.txt) is
provided by the Lambda runtime; engine/ is stdlib-only. Any *other* requirement
added later is pip-installed into the package here.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPO_ROOT / "lambda_package"
SOURCE_DIRS = ("lambdas", "engine")

# Not needed at runtime.
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", "test_*.py", "*_test.py"
)

# Provided by the Lambda runtime - never vendor these.
RUNTIME_PROVIDED = {"boto3", "botocore"}


def extra_requirements() -> list[str]:
    req = REPO_ROOT / "lambdas" / "failure_propagation" / "requirements.txt"
    if not req.exists():
        return []
    extras = []
    for raw in req.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = line.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
        if name not in RUNTIME_PROVIDED:
            extras.append(line)
    return extras


def main() -> int:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    for name in SOURCE_DIRS:
        src = REPO_ROOT / name
        if not src.is_dir():
            print(f"error: missing source dir {src}", file=sys.stderr)
            return 1
        shutil.copytree(src, PACKAGE_DIR / name, ignore=IGNORE)

    extras = extra_requirements()
    if extras:
        print(f"pip installing extra deps: {extras}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps",
             "-t", str(PACKAGE_DIR), *extras],
            check=True,
        )

    print(f"\nBuilt {PACKAGE_DIR.relative_to(REPO_ROOT)}/:")
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(PACKAGE_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
