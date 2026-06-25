# CDIC Treatment Plan — reference

Canonical values for building a `?plan=` payload. Keep in sync with
`treatment-plan.html` (the `TREATMENTS`, `DISCOUNT_PRESETS`, doctor/
coordinator/location `<option>`s) and with `build_link.py`.

## JSON schema

All fields are optional. Omitted dropdowns fall back to the form's defaults.

```json
{
  "patient": {
    "firstName": "John",
    "lastName":  "Smith",
    "phone":     "2125550100",        // any format; the form reformats it
    "email":     "john@example.com",
    "dob":       "1980-03-03"          // YYYY-MM-DD or MM/DD/YYYY
  },
  "doctor":      "Dr. Dale Goldschlag", // fuzzy-matched; a last name works
  "coordinator": "Jackie",
  "location":    "central park",        // fuzzy substring is fine
  "procedures": [
    { "name": "Zirconia/Ceramic Implant Post & Crown", "teeth": "14, 15" },
    { "name": "Surgical Extractions", "teeth": "Full Arch", "arch": "upper" },
    { "name": "Custom one-off thing", "teeth": "8", "price": 1200 }
  ],
  "discounts": [
    { "name": "Senior Citizen Discount", "pct": 10 },
    { "name": "Free Extractions" }
  ],
  "discountDate": "2026-06-30"          // "valid through"; defaults to end of month
}
```

- **Procedure** = `name` + (`teeth` or a full arch). `price` is optional for
  catalog treatments (resolved automatically); **required** for anything not in
  the catalog below.
- **Full arch**: set `"teeth": "Full Arch"` and `"arch": "upper"` or `"lower"`.
  A full arch counts as **1 unit**. (Without `arch`, the form skips that line.)
- **Specific teeth**: comma-separated universal numbers, e.g. `"14, 15"`. Each
  tooth = 1 unit; the line total is `price × number of teeth`.
- Listing teeth from both arches in one procedure is fine — the form splits it
  into an upper line and a lower line automatically.

## Treatment catalog (exact names)

> **Prices below are illustrative.** The form fills in the live unit price for
> each catalog treatment at load time, so you should **omit `price`** for any
> treatment in this list — only include `price` for a *custom* treatment that
> isn't here. `build_link.py` reads the authoritative prices straight from
> `treatment-plan.html`.

| Treatment | Price (illustrative) |
|---|---|
| Surgical Extractions | $895 |
| Bone Graft | $785 |
| Ozone Therapy Post Extraction | $285 |
| Surgical Temporary Per Unit | $550 |
| Internal Sinus Lift With PRF & PRP | $2,500 |
| Titanium Implant Abutment | $785 |
| PRF & PRP | $685 |
| Zirconia Abutment Customization | $785 |
| Zirconia/Metal Free/Ceramic Crowns | $2,895 |
| Titanium Implant Abutment & Crown | $3,895 |
| Section Crown | $485 |
| Zirconia / Metal Free / Ceramic Implant | $3,000 |
| Zirconia/Ceramic Implant Post & Crown | $5,895 |
| Internal Sinus Lift | $1,250 |
| Fully Guided Implant Surgical Stent | $250 |
| Vitamin C | $240 |
| Surgical Implant Extraction | $785 |
| Prosthetic Temporary Per Unit | $555 |
| Laser-Assisted Bacterial Reduction | $375 |
| Full Arch Reconstruction | $18,900 |

**Auto-pairing:** any procedure whose name contains "extraction" automatically
gets a matching **Laser-Assisted Bacterial Reduction** (same teeth/units) added
by the form. Do **not** add it yourself.

**Surgical-temporary check:** if a plan has ≥ 4 implant units and no "Surgical
Temporary Per Unit", the form prompts the coordinator on review. You don't need
to handle this — just be aware the prompt may appear.

## Doctors
- Dr. Hedieh Samadi
- Dr. Robert Horowitz
- Dr. Dale Goldschlag  *(default)*

## Coordinators
- Jackie *(default)* · Yaya · Viola-Nile · Rodrigo · Meg · Essy

## Locations  (fuzzy match — a keyword like "central park" or "scarsdale" works)
- 120 Central Park South 1G — New York, NY 10019 — Tel: (212) 262-0950  *(default)*
- 2 Overhill Rd Suite 270 — Scarsdale, NY 10583 — Tel: (914) 358-4183

## Discount presets

| Preset | How it works | Needs `pct`? |
|---|---|---|
| Upper Arch $18,900 Special | Brings upper-arch procedures down to $18,900 | No |
| Lower Arch $18,900 Special | Brings lower-arch procedures down to $18,900 | No |
| Free Extractions | Deducts the full cost of all extraction lines | No |
| Courtesy X-Rays | $250 off | No |
| Senior Citizen Discount | Percentage off whole case | **Yes** |
| Military Appreciation Discount | Percentage off | **Yes** |
| Spring Renewal Special | Percentage off | **Yes** |
| Shine All Summer | Percentage off | **Yes** |
| The Fall Confidence Special | Percentage off | **Yes** |
| New Year, New Smile | Percentage off | **Yes** |

A custom percentage discount with any name is fine too — just include `pct`.
Discounts apply in the order listed.

## Tooth numbering (US Universal, 1–32)

- **Upper:** 1 = upper-right last molar → 16 = upper-left last molar.
- **Lower:** 17 = lower-left last molar → 32 = lower-right last molar.
- Quick anchors: upper-right canine **6**, upper-left canine **11**, the four
  upper incisors **8 & 9** (centrals), **7 & 10** (laterals); lower centrals
  **24 & 25**. First molars: upper-right **3**, upper-left **14**, lower-left
  **19**, lower-right **30**.
- If the user says a tooth name (e.g. "upper left first molar") convert it to
  the number (14). If a description is ambiguous, ask.

## Worked example

User (voice): *"New plan for John Smith, 212-555-0100, john@example.com, born
March 3rd 1980. Implant post and crown on 14 and 15, take out the whole upper
arch, senior discount 10%, and make extractions free."*

JSON:

```json
{
  "patient": {"firstName":"John","lastName":"Smith","phone":"2125550100","email":"john@example.com","dob":"1980-03-03"},
  "procedures": [
    {"name":"Zirconia/Ceramic Implant Post & Crown","teeth":"14, 15"},
    {"name":"Surgical Extractions","teeth":"Full Arch","arch":"upper"}
  ],
  "discounts": [
    {"name":"Senior Citizen Discount","pct":10},
    {"name":"Free Extractions"}
  ]
}
```

Then `python3 build_link.py '<that JSON>'` → a URL to give the user.
(The form will also auto-add Laser-Assisted Bacterial Reduction for the
extraction.)
