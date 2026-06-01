// CDIC Treatment Plan — Cloudflare Worker
// 1. Verifies app access via PIN
// 2. Uploads PDF to GHL media library
// 3. Upserts contact (name, email, phone, DOB)
// 4. Creates or updates opportunity in the "Treatment Plan Given" pipeline, "First Visit" stage
//
// Secrets (Workers → Settings → Variables → Secrets):
//   GHL_API_KEY      — GHL Location API key
//   GHL_LOCATION_ID  — GHL Location ID
//   APP_PIN          — 4-digit PIN to access the app (optional — if not set, PIN is disabled)
//
// Required API key scopes:
//   contacts.write · contacts.notes.write · medias.write · opportunities.write

export default {
  async fetch(request, env) {

    if (request.method === 'OPTIONS') return cors(null, 204);
    if (request.method !== 'POST')    return cors(JSON.stringify({ error: 'Method not allowed' }), 405);

    // ── Route: PIN verification ───────────────────────────────────────
    const url = new URL(request.url);
    if (url.pathname === '/verify-pin') {
      // If no APP_PIN secret is configured, access is open
      if (!env.APP_PIN) {
        return cors(JSON.stringify({ success: true, token: 'open' }), 200);
      }
      try {
        const { pin } = await request.json();
        if (String(pin) === String(env.APP_PIN)) {
          // Generate a simple session token (random hex, valid this session only)
          const token = [...crypto.getRandomValues(new Uint8Array(16))]
            .map(b => b.toString(16).padStart(2, '0')).join('');
          return cors(JSON.stringify({ success: true, token }), 200);
        }
        return cors(JSON.stringify({ success: false, error: 'Incorrect PIN' }), 401);
      } catch (e) {
        return cors(JSON.stringify({ error: e.message }), 400);
      }
    }

    // ── Route: GHL upload (default) ───────────────────────────────────
    try {
      const {
        pdfBase64, fileName,
        firstName, lastName, email, phone, dateOfBirth,
        doctor, coordinator, caseTotal, discountAmount, discountExpiration, today: clientToday,
      } = await request.json();

      const HEADERS = {
        'Authorization': `Bearer ${env.GHL_API_KEY}`,
        'Version': '2021-07-28',
      };

      // ── 1. Upload PDF to GHL Media Library ──────────────────────────
      const pdfBytes = Uint8Array.from(atob(pdfBase64), c => c.charCodeAt(0));
      const formData = new FormData();
      formData.append('file', new Blob([pdfBytes], { type: 'application/pdf' }), fileName);

      const uploadRes  = await fetch('https://services.leadconnectorhq.com/medias/upload-file', {
        method: 'POST',
        headers: HEADERS,
        body: formData,
      });
      let uploadData;
      const rawText = await uploadRes.text();
      try { uploadData = JSON.parse(rawText); } catch { uploadData = { raw: rawText }; }

      if (!uploadRes.ok) {
        return cors(JSON.stringify({ error: 'GHL upload failed', status: uploadRes.status, details: uploadData }), 500);
      }

      const fileUrl = uploadData.fileUrl ?? uploadData.url ?? '';

      // ── 2. Upsert contact ────────────────────────────────────────────
      const contactPayload = {
        locationId: env.GHL_LOCATION_ID,
        firstName, lastName, email, phone,
      };
      if (dateOfBirth) contactPayload.dateOfBirth = dateOfBirth;

      const contactRes  = await fetch('https://services.leadconnectorhq.com/contacts/upsert', {
        method: 'POST',
        headers: { ...HEADERS, 'Content-Type': 'application/json' },
        body: JSON.stringify(contactPayload),
      });
      const contactData = await contactRes.json();
      const contactId   = contactData.contact?.id;

      // ── 3. Add note with PDF link ────────────────────────────────────
      if (contactId && fileUrl) {
        await fetch(`https://services.leadconnectorhq.com/contacts/${contactId}/notes`, {
          method: 'POST',
          headers: { ...HEADERS, 'Content-Type': 'application/json' },
          body: JSON.stringify({ body: `Treatment Plan PDF: ${fileUrl}` }),
        });
      }

      // ── 4. Look up pipeline ID + stage ID by name ────────────────────
      let pipelineId = null, stageId = null;
      const plRes  = await fetch(
        `https://services.leadconnectorhq.com/opportunities/pipelines?locationId=${env.GHL_LOCATION_ID}`,
        { headers: HEADERS }
      );
      const plData = await plRes.json();
      const pipeline = (plData.pipelines || []).find(
        p => p.name.toLowerCase() === 'treatment plan given'
      );
      if (pipeline) {
        pipelineId = pipeline.id;
        stageId    = (pipeline.stages || []).find(s => s.name.toLowerCase() === 'first visit')?.id ?? null;
      }

      // ── 5. Create or update opportunity ─────────────────────────────
      let opportunityId = null;
      if (contactId && pipelineId) {
        const today   = clientToday || new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
        const oppName = `${firstName} ${lastName} - ${today}`;

        // Custom fields — using the field keys from GHL
        const customFields = [];
        const addCF = (key, value) => {
          if (value !== undefined && value !== null && value !== '') {
            customFields.push({ key, field_value: String(value) });
          }
        };
        addCF('treatment_plant_link',    fileUrl);
        addCF('treating_doctor',         doctor);
        addCF('treatment_coordinator',   coordinator);
        addCF('discount_amount',         Number(discountAmount).toLocaleString('en-US'));
        addCF('discount_expiration',     discountExpiration);

        const oppBody = {
          pipelineId,
          locationId:    env.GHL_LOCATION_ID,
          name:          oppName,
          status:        'open',
          contactId,
          monetaryValue: parseFloat(caseTotal) || 0,
          ...(stageId             ? { pipelineStageId: stageId } : {}),
          ...(customFields.length ? { customFields }             : {}),
        };

        // Search for existing opportunity → update if found, create if not
        const searchRes  = await fetch(
          `https://services.leadconnectorhq.com/opportunities/search?location_id=${env.GHL_LOCATION_ID}&contact_id=${contactId}&pipeline_id=${pipelineId}`,
          { headers: HEADERS }
        );
        const searchData = await searchRes.json();
        const existing   = searchData.opportunities?.[0] ?? null;

        if (existing) {
          const updateRes = await fetch(`https://services.leadconnectorhq.com/opportunities/${existing.id}`, {
            method: 'PUT',
            headers: { ...HEADERS, 'Content-Type': 'application/json' },
            body: JSON.stringify(oppBody),
          });
          const updateData = await updateRes.json();
          opportunityId = existing.id;
        } else {
          const createRes  = await fetch('https://services.leadconnectorhq.com/opportunities/', {
            method: 'POST',
            headers: { ...HEADERS, 'Content-Type': 'application/json' },
            body: JSON.stringify(oppBody),
          });
          const createData = await createRes.json();
          opportunityId = createData.opportunity?.id ?? createData.id ?? null;
        }
      }

      return cors(JSON.stringify({ success: true, fileUrl, contactId, opportunityId }), 200);

    } catch (e) {
      return cors(JSON.stringify({ error: e.message, stack: e.stack }), 500);
    }
  },
};

function cors(body, status) {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
