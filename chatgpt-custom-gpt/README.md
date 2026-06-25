# CDIC Treatment Plan — ChatGPT Custom GPT (mobile-safe)

The ChatGPT equivalent of the Claude voice Skill. Staff dictate a patient +
treatment into a Custom GPT and get back a prefilled link to the same
`treatment-plan.html` form, which they review and send to GHL themselves.

**Why this design:** instead of Code Interpreter (whose availability on the
ChatGPT phone app is uncertain), the GPT calls a **GPT Action** — an HTTPS
endpoint that returns the link. Actions run wherever the GPT runs, **including
mobile**, so the phone is not a question mark. The endpoint is one small route
added to your existing Cloudflare worker.

```
voice in ChatGPT → GPT maps it to fields → Action POST /build-link
   → worker base64url-encodes the plan → returns the prefilled URL
   → staff open it, review, Send to GHL
```

The token the worker produces is **byte-identical** to the Claude skill's
`build_link.py`, so links from either platform open the same form identically.

## Files
- `instructions.md` — paste into the GPT's **Instructions** field.
- `openapi-action.yaml` — the Action schema (import into the GPT's Action).
- Knowledge file — reuse `../skills/cdic-treatment-plan/reference.md` (catalog
  names, presets, tooth numbering, schema). No separate copy needed.

## Setup

### 1. Deploy the worker route (one time)
The route lives in `../cloudflare-worker.js` (`POST /build-link`). Redeploy the
worker so it's live:
- Cloudflare dashboard → your `cdic-ghl-upload` worker → paste the updated
  `cloudflare-worker.js` → **Deploy**, or `wrangler deploy` if you use Wrangler.

Verify it works:
```bash
curl -s -X POST https://cdic-ghl-upload.ariel-5fb.workers.dev/build-link \
  -H 'Content-Type: application/json' \
  -d '{"patient":{"firstName":"Test","lastName":"Patient"},"procedures":[{"name":"Bone Graft","teeth":"8, 9"}]}'
# → {"url":"https://arijg.github.io/cdic-treatment-plan/treatment-plan.html?plan=..."}
```
Open the returned URL — it should land on the prefilled form.

### 2. Create the GPT
On a computer: ChatGPT → **Explore GPTs → Create** (or `chatgpt.com/gpts/editor`)
→ **Configure** tab.
1. **Name / Description / Conversation starters** — see the bottom of
   `instructions.md`.
2. **Instructions** — paste all of `instructions.md`.
3. **Knowledge** — upload `../skills/cdic-treatment-plan/reference.md`.
4. **Capabilities** — Web Search / Canvas / Image / Code Interpreter are not
   needed; you can leave them off.
5. **Actions → Create new action** → set Authentication to **None** → paste the
   contents of `openapi-action.yaml` into the schema box. Confirm the server URL
   shows `https://cdic-ghl-upload.ariel-5fb.workers.dev` and the
   `buildTreatmentPlanLink` operation is listed.
6. **Save** (top right). Share to staff via "Anyone with the link" if you want
   others to use it (each person needs a ChatGPT account).

### 3. Test on your phone
Open the GPT in the ChatGPT iPhone app and say:
> "Treatment plan for Test Patient, bone graft on 8 and 9, senior discount 10%."

If it replies with a summary and a `arijg.github.io/...?plan=...` link that opens
the prefilled form → it works on mobile.

## Privacy note
The Action sends the plan (which includes PHI: name, DOB, phone) to your worker
over HTTPS, same as the existing GHL flow. The `/build-link` route only encodes
and returns the URL — it makes no GHL calls and does not log or store the body.
The data also passes through OpenAI, same as anything typed/dictated into ChatGPT
— confirm that's acceptable for the practice.

## Keep in sync
- The worker's `/build-link` hard-codes the form's base URL
  (`arijg.github.io/cdic-treatment-plan/treatment-plan.html`). Update it there if
  the form ever moves.
- The knowledge file (`reference.md`) lists treatment **names**, dropdown
  options, and discount presets. If those change in `treatment-plan.html`, update
  `reference.md` (prices are applied by the form automatically and don't need
  syncing). The Claude-side reminder hook flags this when the HTML changes.
