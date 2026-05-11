#!/usr/bin/env python3
"""
generate_filament_manifest.py

Scans filaments/vendor/ and filaments/community/ (if present) and writes
filament_libraries.json.  Run from the repo root:

    python generate_filament_manifest.py
    python generate_filament_manifest.py --dir filaments --base-url https://version.thehueforge.com/filaments --out filament_libraries.json
"""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.parse


BASE_URL_DEFAULT = "https://version.thehueforge.com/filaments"
FILAMENTS_DIR_DEFAULT = "filaments"
CATEGORIES = [
    ("vendor",    "Vendor Libraries"),
    ("community", "Community Libraries"),
]


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


def main():
    parser = argparse.ArgumentParser(description="Generate filament_libraries.json manifest")
    parser.add_argument("--dir", default=FILAMENTS_DIR_DEFAULT,
                        help=f"Base filaments directory (default: {FILAMENTS_DIR_DEFAULT})")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT,
                        help=f"Base URL where files are hosted (default: {BASE_URL_DEFAULT})")
    parser.add_argument("--out", default="filament_libraries.json",
                        help="Output manifest filename (default: filament_libraries.json)")
    args = parser.parse_args()

    base_dir = pathlib.Path(args.dir)
    if not base_dir.is_dir():
        print(f"ERROR: directory not found: {base_dir}", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url.rstrip("/")
    libraries = []

    for category_key, category_label in CATEGORIES:
        subdir = base_dir / category_key
        if not subdir.is_dir():
            continue
        files = sorted(subdir.glob("*.json"))
        for f in files:
            count = filament_count(f)
            libraries.append({
                "name":           f.stem,
                "filename":       f.name,
                "category":       category_key,
                "url":            f"{base_url}/{category_key}/{urllib.parse.quote(f.name)}",
                "sha256":         sha256_of_file(f),
                "filament_count": count,
            })
            print(f"  [{category_label:20s}]  {f.name:45s}  {count:4d} filaments")

    if not libraries:
        print(f"No .json files found under {base_dir}/vendor/ or {base_dir}/community/",
              file=sys.stderr)
        sys.exit(1)

    manifest = {"version": 1, "libraries": libraries}
    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(libraries)} entries to {out_path}")


if __name__ == "__main__":
    main()
