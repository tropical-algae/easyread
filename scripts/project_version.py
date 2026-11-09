"""Print the project version after verifying every release metadata file agrees."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def versions() -> dict[str, str]:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = re.search(r"^\[project\]\s*$([\s\S]*?)(?=^\[|\Z)", pyproject, re.MULTILINE)
    pyproject_version = project and re.search(r'^version\s*=\s*["\']([^"\']+)["\']', project.group(1), re.MULTILINE)
    if not pyproject_version:
        raise SystemExit("pyproject.toml does not define project.version")
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    init = (ROOT / "easyread" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init, re.MULTILINE)
    if not match:
        raise SystemExit("easyread/__init__.py does not define __version__")
    return {
        "pyproject.toml": pyproject_version.group(1),
        "easyread/__init__.py": match.group(1),
        "package.json": str(package["version"]),
        "package-lock.json": str(package_lock["version"]),
        "package-lock.json packages root": str(package_lock["packages"][""]["version"]),
    }


def main() -> None:
    found = versions()
    unique = set(found.values())
    if len(unique) != 1:
        detail = ", ".join(f"{name}={version}" for name, version in found.items())
        raise SystemExit(f"project versions do not match: {detail}")
    print(unique.pop())


if __name__ == "__main__":
    main()
