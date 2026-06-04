#!/usr/bin/env python3
"""Build MCPB bundle for observability-mcp."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path


def create_mcpb_package() -> bool:
    project_root = Path(__file__).parent
    mcpb_dir = project_root / "mcpb"
    dist_dir = project_root / "dist"
    src_dir = project_root / "src"

    dist_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = mcpb_dir / "manifest.json"
    if not manifest_path.exists():
        print("[ERROR] mcpb/manifest.json missing")
        return False

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    package_name = manifest.get("name", "observability-mcp")
    version = manifest.get("version", "0.2.2")
    output_file = dist_dir / f"{package_name}-{version}.mcpb"

    print(f"[BUILD] {package_name}-{version}")

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        if not src_dir.exists():
            print("[ERROR] src/ missing")
            return False
        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith((".py", ".md", ".json", ".typed")):
                    file_path = Path(root) / file
                    zipf.write(str(file_path), str(file_path.relative_to(project_root)))
        for doc in ("README.md", "CHANGELOG.md", "llms.txt", "llms-full.txt", "LICENSE"):
            doc_path = project_root / doc
            if doc_path.exists():
                zipf.write(str(doc_path), doc)

    print(f"[SUCCESS] {output_file} ({os.path.getsize(output_file) / 1024:.1f} KB)")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if create_mcpb_package() else 1)
