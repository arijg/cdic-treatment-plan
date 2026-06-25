#!/usr/bin/env python3
"""Build a prefilled CDIC Treatment Plan link from a plan JSON.

The treatment-plan page reads ?plan=<base64url-encoded JSON> on load and fills
every field. This script takes the plan JSON, base64url-encodes it, and prints
the full URL.

The treatment catalog is the SINGLE SOURCE OF TRUTH and lives in
treatment-plan.html (the `const TREATMENTS = [...]` block). This script does NOT
carry its own price list:
  * The form itself fills in each catalog price at load time, so the link never
    needs to embed catalog prices — only custom (non-catalog) treatments need an
    explicit `price`.
  * For VALIDATION (warning about unknown treatment names), this script reads
    that same TREATMENTS block straight from the HTML, so prices/names can never
    drift out of sync. Resolution order:
        1. --html <path>            (explicit local file)
        2. $CDIC_TP_HTML            (env var)
        3. ./treatment-plan.html    (bundled next to this script, if present)
        4. ../../treatment-plan.html (repo layout)
        5. live URL (GitHub Pages)  (keeps the in-app skill in sync)
    If none can be read, the link is still built — name validation is just
    skipped with a notice (the form will still apply the correct prices).

Usage:
    python build_link.py '<json string>'
    python build_link.py --html /path/to/treatment-plan.html '<json>'
    python build_link.py --base http://localhost:8743/treatment-plan.html '<json>'
    echo '<json>' | python build_link.py

To test locally, point --base at a local server (and --html at the local file
so validation uses your working copy):
    python build_link.py \
        --base http://localhost:8743/treatment-plan.html \
        --html ../../treatment-plan.html '<json>'

Output: the full URL on stdout (any WARNINGs/notices go to stderr).
"""
import os
import re
import sys
import json
import base64
import urllib.request

BASE_URL = "https://arijg.github.io/cdic-treatment-plan/treatment-plan.html"
LIVE_HTML_URL = BASE_URL  # the form page also contains the catalog

NON_PCT_PRESETS = {"Free Extractions", "Courtesy X-Rays"}
FIXED_PRICE_PRESETS = {"Upper Arch $18,900 Special", "Lower Arch $18,900 Special"}


def _norm(s):
    """Lowercase + strip all whitespace — matches the form's name matching."""
    return "".join(str(s).lower().split())


# ── Catalog: parsed from treatment-plan.html (single source of truth) ──────────
def _read_html(explicit=None):
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        explicit,
        os.environ.get("CDIC_TP_HTML"),
        os.path.join(here, "treatment-plan.html"),
        os.path.join(here, "..", "..", "treatment-plan.html"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return f.read(), path
    try:
        with urllib.request.urlopen(LIVE_HTML_URL, timeout=10) as resp:
            return resp.read().decode("utf-8"), LIVE_HTML_URL
    except Exception as e:  # offline / sandboxed — caller degrades gracefully
        return None, f"unavailable ({e})"


def load_catalog(explicit=None):
    """Return ({canonical name: price}, source) parsed from the HTML, or (None, source)."""
    html, src = _read_html(explicit)
    if not html:
        return None, src
    block = re.search(r"const\s+TREATMENTS\s*=\s*\[(.*?)\]\s*;", html, re.S)
    if not block:
        return None, f"{src} (TREATMENTS block not found)"
    catalog = {
        name: int(price)
        for name, price in re.findall(
            r'name:\s*"([^"]*)"\s*,\s*price:\s*(\d+)', block.group(1)
        )
    }
    return (catalog or None), src


def validate(data, catalog, source):
    """Emit non-fatal warnings to stderr so the assistant can fix the plan."""
    warn = lambda m: print(f"WARNING: {m}", file=sys.stderr)

    if catalog is None:
        print(f"NOTE: could not load the treatment catalog from {source} — "
              f"skipping treatment-name validation. The form will still apply "
              f"current prices for catalog items at load time.", file=sys.stderr)
        norm_catalog = {}
    else:
        norm_catalog = {_norm(name): (name, price) for name, price in catalog.items()}

    for pr in data.get("procedures", []):
        name = pr.get("name", "")
        hit = norm_catalog.get(_norm(name))
        if catalog is not None and hit is None and pr.get("price") is None:
            warn(f'Treatment "{name}" is not in the catalog and has no price — '
                 f"fix the name to match the catalog, or add an explicit price.")
        elif hit is not None and pr.get("price") is not None and pr["price"] != hit[1]:
            warn(f'Treatment "{name}" has price {pr["price"]} but the catalog '
                 f"says {hit[1]}. Omit price to always use the live catalog price, "
                 f"or keep it only if this is a deliberate override.")
        teeth = str(pr.get("teeth", "")).strip().lower()
        if teeth in ("full arch", "") and not pr.get("arch"):
            warn(f'Procedure "{name}" uses Full Arch but no "arch" '
                 f'(upper/lower) was given — the form will skip it.')

    for ds in data.get("discounts", []):
        name = ds.get("name", "")
        is_preset_fixed = name in FIXED_PRICE_PRESETS or name in NON_PCT_PRESETS
        if not is_preset_fixed and ds.get("pct") is None:
            warn(f'Discount "{name}" is percentage-based but has no "pct".')


def parse_args(argv):
    html_path, base, positional = None, None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--html":
            html_path = argv[i + 1]; i += 2; continue
        if a.startswith("--html="):
            html_path = a.split("=", 1)[1]; i += 1; continue
        if a == "--base":
            base = argv[i + 1]; i += 2; continue
        if a.startswith("--base="):
            base = a.split("=", 1)[1]; i += 1; continue
        positional.append(a); i += 1
    return html_path, base, positional


def main():
    html_path, base, positional = parse_args(sys.argv[1:])
    base = base or os.environ.get("CDIC_TP_BASE") or BASE_URL
    raw = positional[0] if positional else sys.stdin.read()
    data = json.loads(raw)  # raises on invalid JSON — surfaces the problem

    catalog, source = load_catalog(html_path)
    validate(data, catalog, source)

    compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = base64.urlsafe_b64encode(compact).decode("ascii").rstrip("=")
    print(f"{base}?plan={token}")


if __name__ == "__main__":
    main()
