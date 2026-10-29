"""Fast repository/package validation without Home Assistant installed."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
required = [
    ROOT / "hacs.json",
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "custom_components/google_calendar_colors/manifest.json",
    ROOT / "custom_components/google_calendar_colors/strings.json",
    ROOT / "custom_components/google_calendar_colors/translations/en.json",
    ROOT / "custom_components/google_calendar_colors/www/week-planner-card.js",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
for path in required:
    if path.suffix == ".json" and path.is_file():
        json.loads(path.read_text())
if missing:
    print("Missing: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
print("HACS structure is complete")

