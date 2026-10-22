#!/usr/bin/env python3
"""
generate_library_manifest.py

Scans libraries/<platform>/*.zip (each with its <name>-<version>.meta.json beside it) and
writes libraries.json, the hot-update manifest HueForge reads (LibraryUpdateManifest.cpp).
Run from the repo root (the pre-commit hook does this automatically):

    python generate_library_manifest.py
    python generate_library_manifest.py --base-url https://version.thehueforge.com/libraries --out libraries.json

Payload zips are produced by Tools/release/publish_library.py in the HueForge repo, which
also checks them against libraries/contracts/<hostVersion>/. Never edit libraries.json by hand.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.parse
import zipfile


BASE_URL_DEFAULT = "https://version.thehueforge.com/libraries"
LIBRARIES_DIR = "libraries"
MANIFEST_DEFAULT = "libraries.json"
SCHEMA_VERSION = 1
NON_PLATFORM_DIRS = {"contracts"}
META_KEYS = ("abiVersion", "minHostVersion", "maxHostVersion", "notes", "published")


class ManifestError(RuntimeError):
    pass


def sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def version_key(v):
    """'1.10.0-rc-2' -> ((1, 10, 0), tail): numeric compare, a tail sorts below its release."""
    head, _, tail = str(v).partition("-")
    nums = tuple(int(p) if p.isdigit() else 0 for p in head.split("."))
    while len(nums) > 1 and nums[-1] == 0:
        nums = nums[:-1]
    return nums, (0 if tail else 1), tail


def read_library_json(zip_path: pathlib.Path) -> dict:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            data = json.loads(zf.read("library.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise ManifestError(f"{zip_path}: cannot read library.json ({e})")
    for key in ("name", "dllFileName", "version", "abiVersion", "sha256"):
        if key not in data:
            raise ManifestError(f"{zip_path}: library.json has no '{key}'")
    return data


def build_manifest(repo_root, base_url=BASE_URL_DEFAULT) -> dict:
    """Pure scan of <repo_root>/libraries/<platform>/ -> the libraries.json object."""
    root = pathlib.Path(repo_root) / LIBRARIES_DIR
    base_url = base_url.rstrip("/")
    entries = []
    if root.is_dir():
        for plat_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if plat_dir.name in NON_PLATFORM_DIRS:
                continue
            for z in sorted(plat_dir.glob("*.zip")):
                lib = read_library_json(z)
                expected = f"{lib['name']}-{lib['version']}.zip"
                if z.name != expected:
                    raise ManifestError(f"{z}: library.json says {expected}")
                meta_path = z.with_name(z.name[:-len(".zip")] + ".meta.json")
                if not meta_path.is_file():
                    raise ManifestError(f"{z}: no {meta_path.name} beside it")
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                missing = [k for k in META_KEYS if k not in meta]
                if missing:
                    raise ManifestError(f"{meta_path}: missing {', '.join(missing)}")
                if int(meta["abiVersion"]) != int(lib["abiVersion"]):
                    raise ManifestError(f"{meta_path}: abiVersion {meta['abiVersion']} "
                                        f"disagrees with library.json {lib['abiVersion']}")
                entries.append({
                    "name":           lib["name"],
                    "platform":       plat_dir.name,
                    "version":        lib["version"],
                    "abiVersion":     int(lib["abiVersion"]),
                    "minHostVersion": meta["minHostVersion"],
                    "maxHostVersion": meta["maxHostVersion"],
                    "url":            f"{base_url}/{plat_dir.name}/{urllib.parse.quote(z.name)}",
                    "sha256":         sha256_of_file(z),
                    "size":           z.stat().st_size,
                    "notes":          meta["notes"],
                    "published":      meta["published"],
                    "dllSha256":      str(lib["sha256"]).lower(),
                })
    # Name ascending, then version descending (platform breaks remaining ties).
    entries.sort(key=lambda e: e["platform"])
    entries.sort(key=lambda e: version_key(e["version"]), reverse=True)
    entries.sort(key=lambda e: e["name"])
    return {"schemaVersion": SCHEMA_VERSION, "libraries": entries}


def write_manifest(repo_root, base_url=BASE_URL_DEFAULT, out=MANIFEST_DEFAULT) -> dict:
    manifest = build_manifest(repo_root, base_url)
    out_path = pathlib.Path(out)
    if not out_path.is_absolute():
        out_path = pathlib.Path(repo_root) / out_path
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate libraries.json manifest")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT,
                        help=f"Base URL where payloads are hosted (default: {BASE_URL_DEFAULT})")
    parser.add_argument("--out", default=MANIFEST_DEFAULT,
                        help=f"Output manifest filename (default: {MANIFEST_DEFAULT})")
    parser.add_argument("--root", default=".", help="Repo root (default: current directory)")
    args = parser.parse_args()

    try:
        manifest = write_manifest(args.root, args.base_url, args.out)
    except (ManifestError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    for e in manifest["libraries"]:
        print(f"  [{e['platform']:12s}]  {e['name']:16s} {e['version']:12s} ABI {e['abiVersion']}  "
              f"hosts {e['minHostVersion']}..{e['maxHostVersion']}  {e['size']} bytes")
    print(f"\nWrote {len(manifest['libraries'])} entries to {args.out}")


if __name__ == "__main__":
    main()
