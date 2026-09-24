#!/usr/bin/env python3
"""Copy KDM Semantica deploy artifacts into upload/kdm/config/."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
UPLOAD_DIR = REPO / "upload" / "kdm" / "config"

ARTIFACTS: tuple[tuple[Path, str], ...] = (
    (REPO / "kdm" / "xunternehmen_kg_with_decisions.json", "xunternehmen_kg_with_decisions.json"),
    (REPO / "config" / "xunternehmen_business_rules.yaml", "xunternehmen_business_rules.yaml"),
    (REPO / "config" / "xunternehmen_r2rml_db_mapping.yaml", "xunternehmen_r2rml_db_mapping.yaml"),
)


def sync_upload_kdm_config() -> list[Path]:
    """Copy KDM config/KG files to upload/kdm/config. Returns written paths."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src, name in ARTIFACTS:
        if not src.is_file():
            raise FileNotFoundError(f"Missing KDM artifact to upload: {src}")
        dest = UPLOAD_DIR / name
        shutil.copy2(src, dest)
        written.append(dest)
    return written


def main() -> int:
    paths = sync_upload_kdm_config()
    print(f"Synced {len(paths)} file(s) to {UPLOAD_DIR}:")
    for p in paths:
        print(f"  {p}")
    print("\nMCP env (absolute paths on target host):")
    print(f"  SEMANTICA_KG_PATH={UPLOAD_DIR / 'xunternehmen_kg_with_decisions.json'}")
    print(f"  SEMANTICA_BUSINESS_RULES={UPLOAD_DIR / 'xunternehmen_business_rules.yaml'}")
    print(f"  SEMANTICA_MAPPING_CONFIG={UPLOAD_DIR / 'xunternehmen_r2rml_db_mapping.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
