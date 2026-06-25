#!/usr/bin/env python3
"""Build a prefilled CDIC Treatment Plan link from a plan JSON.

The treatment-plan page reads ?plan=<base64url-encoded JSON> on load and
fills every field. This script takes the plan JSON, validates it lightly
against the catalog, base64url-encodes it, and prints the full URL.

Usage:
    python build_link.py '<json string>'
    echo '<json>' | python build_link.py

Output: the full https URL on stdout (plus any warnings on stderr).
"""
import sys
import json
import base64

BASE_URL = "https://arijg.github.io/cdic-treatment-plan/treatment-plan.html"

# Canonical catalog — keep in sync with TREATMENTS in treatment-plan.html.
TREATMENTS = {
    "surgical extractions": 895,
    "bone graft": 785,
    "ozone therapy post extraction": 285,
    "surgical temporary per unit": 550,
    "internal sinus lift with prf & prp": 2500,
    "titanium implant abutment": 785,
    "prf & prp": 685,
    "zirconia abutment customization": 785,
    "zirconia/metal free/ceramic crowns": 2895,
    "titanium implant abutment & crown": 3895,
    "section crown": 485,
    "zirconia / metal free / ceramic implant": 3000,
    "zirconia/ceramic implant post & crown": 5895,
    "internal sinus lift": 1250,
    "fully guided implant surgical stent": 250,
    "vitamin c": 240,
    "surgical implant extraction": 785,
    "prosthetic temporary per unit": 555,
    "laser-assisted bacterial reduction": 375,
    "full arch reconstruction": 18900,
}

NON_PCT_PRESETS = {"Free Extractions", "Courtesy X-Rays"}
FIXED_PRICE_PRESETS = {"Upper Arch $18,900 Special", "Lower Arch $18,900 Special"}


def _norm(s):
    return "".join(str(s).lower().split())


def validate(data):
    """Emit non-fatal warnings to stderr so the assistant can fix the plan."""
    warn = lambda m: print(f"WARNING: {m}", file=sys.stderr)
    norm_catalog = {_norm(k): k for k in TREATMENTS}

    for pr in data.get("procedures", []):
        name = pr.get("name", "")
        if _norm(name) not in norm_catalog and pr.get("price") is None:
            warn(f'Treatment "{name}" is not in the catalog and has no price — '
                 f"add a price or fix the name.")
        teeth = str(pr.get("teeth", "")).strip().lower()
        if teeth in ("full arch", "") and not pr.get("arch"):
            warn(f'Procedure "{name}" uses Full Arch but no "arch" '
                 f'(upper/lower) was given — it will be skipped by the form.')

    for ds in data.get("discounts", []):
        name = ds.get("name", "")
        is_preset_fixed = name in FIXED_PRICE_PRESETS or name in NON_PCT_PRESETS
        if not is_preset_fixed and ds.get("pct") is None:
            warn(f'Discount "{name}" is percentage-based but has no "pct".')


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    data = json.loads(raw)  # raises on invalid JSON — surfaces the problem
    validate(data)
    compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = base64.urlsafe_b64encode(compact).decode("ascii").rstrip("=")
    print(f"{BASE_URL}?plan={token}")


if __name__ == "__main__":
    main()
