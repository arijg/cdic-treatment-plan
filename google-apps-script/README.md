# Treatment Plan Log: Apps Script setup

Every time a treatment plan is printed from `treatment-plan.html`, the form sends a
one-row summary to this Apps Script, which appends it to the **Treatment Plan Log**
Google Sheet in ariel@cdic.com's Drive. Data goes from the browser straight to Google
(Apps Script + Sheets, both covered by the Workspace BAA). Nothing passes through
Cloudflare or GitHub.

Columns written: Date, Patient, Phone, Case total, Discount, Net total (formula),
Coordinator, Location, Plan link (reopens the plan in the form), Plan ID (stops the
same plan being logged twice on one day).

## One-time setup (about 10 minutes, signed in as ariel@cdic.com)

1. Open the **Treatment Plan Log** sheet in Google Drive.
2. **Extensions > Apps Script.** Rename the project (top left) to `Treatment Plan Log`.
3. Delete everything in `Code.gs` and paste in the contents of [`Code.gs`](Code.gs). Save.
4. **Project Settings** (gear icon, left bar) > **Script properties** > **Add script property**:
   - Property `STAFF_PIN`, value: the staff PIN you choose (8 or more characters).
   Save.
5. Back in the editor, pick `checkSetup` in the function dropdown and click **Run**.
   Google asks you to authorize the script. If it says "Google hasn't verified this
   app", click **Advanced > Go to Treatment Plan Log**. That warning appears because the
   script is your own and has not been published, which is expected. The log at the
   bottom should say the sheet tab was found and the PIN is set.
6. **Deploy > New deployment.** Click the gear next to "Select type" and pick **Web app**.
   - Description: `v1`
   - Execute as: **Me (ariel@cdic.com)**
   - Who has access: **Anyone**
   Click **Deploy** and copy the **Web app URL** (it ends in `/exec`).
   - If "Anyone" is not in the list, your Admin console blocks sharing outside cdic.com.
     In admin.google.com > Apps > Google Workspace > Drive and Docs > Sharing settings,
     allow sharing outside the domain for an organizational unit that contains only your
     account, then deploy again.
7. Paste the URL into a browser tab. You should see
   `{"ok":true,"service":"cdic-treatment-plan-log"}`.
8. Put the URL in `treatment-plan.html` as `LOG_URL`, commit and push to `main`.
   (Done for the current deployment, version 1 on 2026-11-08. Only a brand-new
   deployment changes the URL.)

## Day to day

- The first time someone prints on a device, the form asks for the staff PIN once and
  remembers it on that device.
- A small label under the buttons shows "Logged to Sheet", "Already in Sheet", or
  "Not logged, tap to retry". Printing never waits for the log.
- **Change the PIN:** edit `STAFF_PIN` in Project Settings. Staff are asked again on
  their next print.
- **Change the script:** Deploy > Manage deployments > pencil icon > Version: **New
  version** > Deploy. The URL stays the same. A brand-new deployment gets a new URL.
- After 20 wrong PINs the script refuses all writes for an hour. Printing still works.

## Keep the sheet private

The Plan link column is full patient data (base64 is encoding, not encryption). Share
the sheet only with people who need it, and don't paste plan links into email or SMS.
The script runs as you, so the sheet itself does not need to be shared with staff.
