#!/usr/bin/env python3
"""PostToolUse hook: remind Claude to re-test the voice-prefill feature whenever
treatment-plan.html is edited.

Reads the hook payload on stdin. If the edited file path ends with
treatment-plan.html, prints a JSON object whose hookSpecificOutput.additionalContext
is injected back into Claude's context. For any other file it prints nothing and
exits 0 (silent), so it never adds noise to unrelated edits.
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # malformed payload — stay silent

tool_input = data.get("tool_input") or {}
tool_response = data.get("tool_response") or {}
path = tool_input.get("file_path") or tool_response.get("filePath") or ""

if not str(path).endswith("treatment-plan.html"):
    sys.exit(0)  # not the treatment plan — stay silent

reminder = (
    "treatment-plan.html was just modified. Before treating this as done, verify the "
    "voice-prefill feature (the `?plan=` loader) and the voice Skill are still in sync:\n"
    "\n"
    "1. SKILL SYNC — skills/cdic-treatment-plan/reference.md is NOT auto-synced. If this "
    "edit changed any of these in the HTML, update reference.md to match:\n"
    "   • TREATMENTS names (prices ARE auto-read by build_link.py, names are not)\n"
    "   • doctor / coordinator / location <option> values\n"
    "   • DISCOUNT_PRESETS / FIXED_PRICE_PRESETS / NON_PCT_PRESETS\n"
    "\n"
    "2. LOADER SYNC — if field IDs or the addProcedure/addDiscount entry paths changed, "
    "check the prefill loader still matches (applyPrefill / setSelectFuzzy / findTreatment "
    "near the bottom of the <script>).\n"
    "\n"
    "3. SMOKE TEST — start a server and open a generated link:\n"
    "   python3 -m http.server 8743\n"
    "   python3 skills/cdic-treatment-plan/build_link.py \\\n"
    "     --base http://localhost:8743/treatment-plan.html --html treatment-plan.html \\\n"
    "     '{\"patient\":{\"firstName\":\"Test\",\"lastName\":\"Patient\"},"
    "\"procedures\":[{\"name\":\"Bone Graft\",\"teeth\":\"8, 9\"}],"
    "\"discounts\":[{\"name\":\"Senior Citizen Discount\",\"pct\":10}]}'\n"
    "   Open the URL and confirm fields, teeth, totals, and discounts populate with no "
    "console errors. Also re-run build_link.py and confirm no unexpected validation WARNINGs.\n"
    "\n"
    "Note: production links only work once changes reach main (GitHub Pages serves from main)."
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": reminder,
    }
}))
