# CDIC Treatment Plan — voice Skill

A Claude Skill that turns a spoken/typed description of a patient and their
dental treatment into a **prefilled link** to the CDIC Treatment Plan form.
Staff dictate the plan into the Claude app on their phone and get back one
tappable link that opens the form with everything filled in — they review each
step and tap **Send to GHL** themselves. Nothing is submitted automatically.

## How it works

```
voice in Claude app → Claude maps it to canonical fields → build_link.py
   → https://arijg.github.io/cdic-treatment-plan/treatment-plan.html?plan=<base64url JSON>
   → form reads ?plan= and fills itself → staff review → Send to GHL
```

The form-side support lives in `treatment-plan.html` (the `?plan=` loader near
the bottom of the script). It reuses the form's own `addProcedure` /
`addDiscount` logic, so prefilled plans behave exactly like manually entered
ones (mixed-arch splitting, laser auto-pairing, totals, surgical-temp check).

## Files

- `SKILL.md` — instructions Claude follows (has the YAML frontmatter).
- `reference.md` — canonical treatments/prices, doctors, coordinators,
  locations, discount presets, tooth numbering, JSON schema, worked example.
- `build_link.py` — encodes a plan JSON into the final URL (and warns about
  unknown treatments / malformed full-arch entries).

## Install in the Claude app

1. Zip this folder so `SKILL.md` is at the top level of the archive:

   ```bash
   cd skills && zip -r cdic-treatment-plan.zip cdic-treatment-plan
   ```

2. In the Claude app: **Settings → Capabilities → Skills → Upload skill**, and
   choose `cdic-treatment-plan.zip`. (Skills require a plan/workspace where
   Skills + code execution are enabled.)
3. Each staff member who needs it installs it the same way.

To use it: open Claude on your phone, tap the mic, and say e.g.
*"New treatment plan for Jane Doe, implant post and crown on tooth 8, senior
discount 10 percent."* Claude replies with a summary and the link.

## Keep in sync

`reference.md` and `build_link.py` both hard-code the treatment prices and the
doctor/coordinator/location/discount lists. If these change in
`treatment-plan.html`, update them here too (the `TREATMENTS` dict in
`build_link.py` and the tables in `reference.md`).

## Deployment note

The `?plan=` loader must be live on the hosted form for links to work. The form
is served by GitHub Pages from the **`main`** branch
(`https://arijg.github.io/cdic-treatment-plan/`). The loader was added on the
`voice-skill-prefill` branch — **merge it to `main`** before rolling the Skill
out to staff. Until then, test against a local copy of `treatment-plan.html`.
