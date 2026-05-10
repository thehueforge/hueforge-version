#!/usr/bin/env python3
"""
generate_filament_manifest.py

Run from the root of the hueforge-version repo after copying (or symlinking)
vendor library JSON files into a subfolder:

    python generate_filament_manifest.py [--dir filaments] [--base-url https://version.thehueforge.com/filaments]

Outputs filament_libraries.json in the current directory.
"""

import argparse
import hashlib
import json
import pathlib
import sys


BASE_URL_DEFAULT = "https://version.thehueforge.com/filaments"
VENDOR_DIR_DEFAULT = "filaments"


def sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def filament_count(path: pathlib.Path) -> int:
    try:
        data = json.loads(path.read_bytes())
        return len(data.get("Filaments", []))
    except Exception:
        return 0


def vendor_name(path: pathlib.Path) -> str:
    # Use the stem (filename without extension) as the display name.
    # e.g. "3D-Fuel Filaments.json" → "3D-Fuel Filaments"
    return path.stem


def main():
    parser = argparse.ArgumentParser(description="Generate filament_libraries.json manifest")
    parser.add_argument(
        "--dir", default=VENDOR_DIR_DEFAULT,
        help=f"Directory containing vendor library JSON files (default: {VENDOR_DIR_DEFAULT})"
    )
    parser.add_argument(
        "--base-url", default=BASE_URL_DEFAULT,
        help=f"Base URL where files will be hosted (default: {BASE_URL_DEFAULT})"
    )
    parser.add_argument(
        "--out", default="filament_libraries.json",
        help="Output manifest filename (default: filament_libraries.json)"
    )
    args = parser.parse_args()

    vendor_dir = pathlib.Path(args.dir)
    if not vendor_dir.is_dir():
        print(f"ERROR: directory not found: {vendor_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(vendor_dir.glob("*.json"))
    if not files:
        print(f"No .json files found in {vendor_dir}", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url.rstrip("/")
    libraries = []
    for f in files:
        filename = f.name
        libraries.append({
            "name": vendor_name(f),
            "filename": filename,
            "url": f"{base_url}/{filename}",
            "sha256": sha256_of_file(f),
            "filament_count": filament_count(f),
        })
        print(f"  {filename:40s}  {filament_count(f):4d} filaments")

    manifest = {"version": 1, "libraries": libraries}
    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(libraries)} entries to {out_path}")


if __name__ == "__main__":
    main()
