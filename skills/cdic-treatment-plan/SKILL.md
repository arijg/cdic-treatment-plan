---
name: cdic-treatment-plan
description: Turn a spoken or typed description of a CDIC dental patient and their treatment into a prefilled CDIC Treatment Plan link. Use whenever the user wants to create, build, or "fill out" a treatment plan / TP for a patient by voice or text — e.g. "new treatment plan for Jane Doe…", "make a TP", "build a plan with implants on 14 and 15". The link opens the existing treatment-plan web form with every field filled in for the user to review and submit; nothing is sent automatically.
---

# CDIC Treatment Plan (voice/text → prefilled link)

You convert a natural-language description of a patient and their dental
treatment into a **prefilled link** to the CDIC Treatment Plan web form. The
form reads a `?plan=` parameter and fills itself in. The user (front-desk /
treatment coordinator) then reviews each step on their phone and taps
**"Send to GHL"** themselves. **You never submit anything** — you only build
the link.

This is designed for voice: the user dictates a plan into the Claude app and
gets back one tappable link.

## Workflow

1. **Read the catalog.** Load `reference.md` (same folder) — it has the exact
   treatment names + prices, doctors, coordinators, locations, discount
   presets, the tooth-numbering scheme, and the JSON schema. Always map the
   user's words to these canonical values; do not invent names or prices.

2. **Gather the plan.** From what the user said, extract:
   - Patient: first name, last name, phone, email, date of birth (any of
     these may be missing — that's fine).
   - Doctor / coordinator / location — **only if the user names them.** If they
     don't, omit them; the form already defaults to **Dr. Dale Goldschlag**,
     **Jackie**, and **Central Park South**.
   - Procedures: each treatment + which teeth (or a full arch).
   - Discounts: any discount/special mentioned.

3. **Map to canonical values** using `reference.md`:
   - Treatment names → exact catalog spelling (you may pass the name loosely;
     the form matches ignoring case/spacing, but prefer the catalog spelling).
     If a treatment is **not** in the catalog, include an explicit `price`.
   - Teeth → US universal numbers (see reference). A whole arch → `"teeth":
     "Full Arch"` **plus** `"arch": "upper"` or `"lower"`.
   - Discounts → preset names where possible. Percentage discounts need `pct`.
     The fixed presets ("Free Extractions", "Courtesy X-Rays", the two "$18,900
     Special"s) take no `pct`.

4. **Ask only about true blockers.** Build the link even if optional fields are
   missing. Only ask the user when something is genuinely ambiguous or unsafe
   to guess — e.g. a treatment that isn't in the catalog and has no price, or
   "extract the molar" with no tooth number. Don't interrogate them for email
   or DOB; the coordinator can add those on review.

5. **Build the link.** Assemble the JSON (schema in `reference.md`) and run:

   ```bash
   python3 build_link.py '<the JSON>'
   ```

   It prints the full URL and prints any `WARNING:` lines to stderr (e.g. an
   unknown treatment, or a Full Arch missing its arch). If you see a warning,
   fix the JSON and re-run before giving the user the link.

6. **Reply with a readable summary + the link.** Show the user what you
   captured so they can sanity-check it at a glance, then the tappable link.
   Always remind them it opens prefilled for **review**, and that they submit
   it themselves. Example:

   > **Treatment plan for John Smith** — Dr. Goldschlag, Central Park South
   > - Zirconia/Ceramic Implant Post & Crown — teeth 14, 15
   > - Surgical Extractions — full upper arch *(laser reduction auto-adds)*
   > - Discounts: Senior Citizen 10%, Free Extractions
   >
   > 👉 [Open prefilled plan](https://arijg.github.io/cdic-treatment-plan/treatment-plan.html?plan=…)
   >
   > Opens with everything filled in — review each step, then tap **Send to GHL**.

## Important rules

- **Never auto-submit.** You produce a link only. Submission to GHL is a human
  action in the browser.
- **Don't guess clinical specifics.** If teeth, a treatment, or a price is
  unclear, ask rather than assume.
- **Extractions auto-pair.** The form automatically adds a "Laser-Assisted
  Bacterial Reduction" for any extraction — do **not** add it yourself, just
  mention it auto-adds so the total isn't a surprise.
- **Patient data is PHI.** Only build plans the user explicitly asks for. Don't
  store, log, or reuse patient details beyond producing the requested link.
- **Mind the price list.** Prices live in `reference.md`. If the user says a
  price has changed, use the price they give for that line (pass it as
  `price`) and flag that the catalog may be out of date.
