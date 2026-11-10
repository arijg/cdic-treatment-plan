# Plan: log every printed treatment plan to a Google Sheet

Status: **built and deployed 2026-11-08.** The Sheet and its bound Apps Script (web app,
version 1, Execute as ariel@cdic.com, access Anyone) are in ariel@cdic.com's Drive, and `LOG_URL`
in `treatment-plan.html` points at it. Remaining: set `STAFF_PIN`, push to `main`, first real print.

## 1. Decisions so far

- **No PDF.** Save the prefill link plus a few summary fields.
- **Destination:** a Google Sheet owned by ariel@cdic.com.
- **Write path:** a Google Apps Script web app that runs as ariel@cdic.com, deployed with
  access "Anyone", protected by a staff PIN.
- **Trigger:** the existing Print button, plus any other way of printing. No new button.

## 2. Data flow

```
treatment-plan.html (GitHub Pages)
  staff taps "Print"  (or Cmd+P / browser menu / iOS Share > Print)
    |- logPlan(): build the summary row + #plan= link, start one POST, don't wait for it
    |     > https://script.google.com/macros/s/<id>/exec   (Apps Script, runs as ariel@cdic.com)
    |         > check PIN > de-duplicate > append row to the "Treatment Plan Log" Sheet
    |- window.print() opens straight away
    |- a small status chip then shows "Logged to Sheet" or "Not logged - tap to retry"
```

Everything after the browser is Google. Apps Script and Sheets are both on Google's HIPAA
Included Functionality list, so the data stays under the Workspace BAA. Compared with the
earlier draft this needs **no Google Cloud project, no OAuth client, no staff Google sign-in**,
and nothing goes through Cloudflare.

## 3. Sheet columns (tab `Plans`)

| Col | Header | Source in the form |
|---|---|---|
| A | Date | Set by the script (Google server time) |
| B | Patient | `patientFirstName` + `patientLastName` |
| C | Phone | `patientPhone` (already formatted `(XXX) XXX-XXXX`) |
| D | Case total | upper + lower + X-ray, same math as the printed plan |
| E | Discount | sum of `computeDiscountAmounts(...)` |
| F | Net total | D minus E |
| G | Coordinator | `coordinator` dropdown. The only "who did it" signal, since the script runs as Ariel |
| H | Location | `location` dropdown |
| I | Plan link | `.../treatment-plan.html#plan=<base64url JSON>`, opens the plan prefilled |
| J | Plan ID | short hash used for de-duplication (hide this column) |
| K | Date of birth | `patientDOB`, when entered. The report uses it to recognize the same patient across plans (added 2026-11-10) |

D to F are numbers formatted as currency; format column C as plain text. Easy extras for
later: doctor, discount valid-through date, ceramic flag.

## 4. Why Print works as the trigger

- **Both print paths are hooked.** The Print button calls `logPlan()` then `window.print()`.
  A `beforeprint` listener also calls `logPlan()`, which covers Cmd+P, the browser menu and
  iOS Share > Print. A per-page "already sent this Plan ID" guard stops the double fire.
- **Only real plans are logged.** Only from Step 3 (the preview), and only with a patient
  name and at least one procedure. Printing a blank form logs nothing.
- **Print is never blocked.** The request is started before the dialog opens and the page
  does not wait for it. If Google is slow, the device is offline or the PIN is wrong, the print
  dialog still opens normally.
- **No duplicate rows.** Plan ID = hash of (plan JSON + today's date). Reprinting the same plan
  the same day adds nothing. Changing anything (a discount, a tooth) and reprinting adds a new
  row, which is the right history of what was quoted. The script re-checks column J under a
  lock, so two offices printing the same plan can't double-log.
- **Visible result.** A small chip next to the buttons (hidden on paper) shows
  "Logged to Sheet", "Not logged - tap to retry" or "PIN rejected". On desktop Chrome it
  updates once the print dialog closes.
- **Known limit.** The page can't tell if someone pressed Cancel in the print dialog, so
  opening the dialog counts as printed.

## 5. The PIN

- The first time someone prints on a device, the page asks for the staff PIN once and keeps it
  on that device (`localStorage`, wrapped in try/catch). The PIN is never in the GitHub repo.
- The script compares it with a Script Property `STAFF_PIN`. Changing that value rotates the
  PIN for everyone; staff re-enter it on their next print.
- A wrong PIN makes the script answer `bad pin`. The page forgets the stored PIN, shows
  "PIN rejected", and printing still goes ahead.
- In the `beforeprint` path (Cmd+P etc.) the page never pops a prompt. With no stored PIN it
  skips logging and the chip offers "tap to enter PIN".
- Use 8 or more characters, not 4 digits. Optional hardening: count failures in
  `CacheService` and refuse all writes for an hour after about 20 bad PINs.

## 6. Apps Script

The final script is [`google-apps-script/Code.gs`](google-apps-script/Code.gs). Compared with the
earlier sketch it also has: a `doGet` health check, a `checkSetup` function to run once from the
editor, a lockout after 20 wrong PINs (refuses writes for an hour; printing still works), Net total
written as a formula (`=D-E` per row), and `@OnlyCurrentDoc` so its only Google permission is
the sheet it lives in. It is unit-tested against mocked Google services (22 checks: PIN, lockout, duplicates,
formula injection, link validation, write-only replies).

## 7. Page changes (`treatment-plan.html`)

1. `LOG_URL` constant next to `WORKER_URL`. The `/exec` URL is fine to be public.
2. `planTotals()` helper: one function for case total, discount and net, used by the printed
   plan, Send to GHL and the log so they can never disagree. Today the same math is duplicated
   in `renderTreatmentPlan` and `uploadToGHL`.
3. `serializePlan()` + `strToB64url()` for the `#plan=` link (see section 9).
4. `planId()`: a small synchronous string hash (e.g. cyrb53) of plan JSON + date. Synchronous
   on purpose, so the request is already on its way before `window.print()` runs.
5. `logPlan()`: guard (Step 3, has patient + procedure, not already sent), get or ask for the
   PIN, then `fetch(LOG_URL, { method: 'POST', body: JSON.stringify(row) })`.
   **Do not set `Content-Type: application/json`**: that triggers a CORS preflight that Apps
   Script cannot answer. A plain string body is sent as `text/plain` and the JSON reply is
   readable. Update the chip from the reply; on `bad pin` clear the stored PIN.
6. Print button: `onclick="printPlan()"`, where `printPlan()` runs `logPlan()` then
   `window.print()`. Plus `window.addEventListener('beforeprint', logPlan)`.
7. Status chip element with the existing `.no-print` class next to the Step 3 buttons.
8. Loader: also read `#plan=` from `location.hash`; keep `?plan=` working for existing
   voice-skill links.

The repo's PostToolUse hook will remind you to re-run the prefill smoke test after editing
the HTML. The new serializer must round-trip through it.

## 8. Google setup

The **Treatment Plan Log** Sheet was created through the Drive and Sheets connectors as
ariel@cdic.com: tab `Plans`, the section 3 headers, New York time zone, currency and date formats,
frozen header row, banding, and a header note explaining the columns. It is private to Ariel.

What is left (about 10 minutes) is pasting the script, setting `STAFF_PIN`, deploying, and putting
the `/exec` URL into `LOG_URL`. Step-by-step: [`google-apps-script/README.md`](google-apps-script/README.md).

## 9. The plan link

Built differently from the first draft, so a saved link reproduces the printed plan exactly:

- `serializePlan()` writes an **exact snapshot** (`"exact": true`): every procedure line with its
  price, units and section as they are on the plan, and every discount in its stored form
  (`pct`, `fixedAmount`, `fixedPrice` + `arch`, `extractionsFree`, or `courtesyOf` = index of the
  comped procedure).
- The loader restores snapshots directly instead of re-running the entry logic, so a laser line
  staff deleted stays deleted, edited prices stay, the order stays, and courtesy discounts stay
  linked to their procedure. Voice links (no `exact`) still go through the old entry logic.
- A saved link opens straight on Step 3 (the plan preview) with a "Saved plan reopened" banner.
- `#plan=` keeps the payload away from GitHub's servers. If a URL has both, the `#plan=` wins.
- Text from a link has `<` and `>` stripped before it reaches the page (both link types), so a
  crafted link can't inject script and read the stored PIN.

## 10. Risks and how they're handled

| Risk | Handling |
|---|---|
| Anyone with URL + PIN can add rows | Write-only endpoint, long PIN, optional lockout, rotate via Script Property |
| No per-person audit trail | Coordinator column; Sheet history shows Ariel for every row (accepted trade-off) |
| Logging fails without anyone noticing | Status chip with retry; print never blocked |
| Duplicate rows | Plan ID check on the page and again in the script |
| Formula injection from typed patient text | `txt()` forces plain text |
| Two offices printing at once | `LockService` |
| The link is full PHI | Sheet stays restricted; never paste links into email or SMS |

## 11. Test plan

1. Print a plan: a row appears and its numbers match the printed totals.
2. Print again: no new row. Change a discount and print: a new row.
3. Cmd+P on desktop, and Share > Print on iPhone Safari: the row is logged.
4. Wrong PIN: chip says PIN rejected, print still opens, next print asks again.
5. Airplane mode: chip says not logged, print still opens, retry works once back online.
6. Patient first name `=1+1`: stored as text, not calculated.
7. Open the Plan link from the Sheet: the form loads with the same totals.
8. Print from Step 1 or 2, or an empty plan: nothing is logged.

## 12. Open items (not blocking)

- Also log on Send to GHL? It's one extra `logPlan()` call and de-duplication makes it safe.
- Extra columns (doctor, valid-through date, ceramic flag).

## Sources

- Google, HIPAA Included Functionality: https://workspace.google.com/terms/2015/1/hipaa_functionality.html
- Google Cloud / Workspace HIPAA overview: https://docs.cloud.google.com/security/compliance/hipaa
- Apps Script web apps guide: https://developers.google.com/apps-script/guides/web
- Accountable, Google Sheets and HIPAA: https://www.accountablehq.com/post/is-google-sheets-hipaa-compliant-baa-phi-and-best-practices
