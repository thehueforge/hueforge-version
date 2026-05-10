# hueforge-version

Version manifest server for HueForge. Hosted via GitHub Pages at `version.thehueforge.com`.

## Files

| File | Purpose |
|------|---------|
| `version.json` | App version, beta version, plugin versions |
| `external_links.json` | External link registry |
| `filament_libraries.json` | Vendor filament library manifest (auto-generated — do not edit by hand) |
| `filaments/*.json` | Vendor filament library files served to HueForge clients |

## Updating vendor filament libraries

1. Add or update `.json` files in `filaments/`
2. Commit — the pre-commit hook regenerates `filament_libraries.json` automatically

The manifest captures the SHA-256 of each file and the filament count. HueForge clients compare the SHA-256 against their local copy to detect updates.

## Setup (one time per clone)

```bash
git config core.hooksPath .githooks
```

This activates the pre-commit hook that auto-regenerates `filament_libraries.json`.

## Manual manifest regeneration

```bash
python generate_filament_manifest.py
# or with custom paths:
python generate_filament_manifest.py --dir filaments --base-url https://version.thehueforge.com/filaments --out filament_libraries.json
```
