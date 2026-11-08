/** @OnlyCurrentDoc  (the script can only open the sheet it lives in) */

// CDIC Treatment Plan Log: Google Apps Script web app.
//
// Lives inside the "Treatment Plan Log" Google Sheet (Extensions > Apps Script).
// Each time a plan is printed, treatment-plan.html POSTs a one-row summary here.
// This script checks the staff PIN, skips a plan that was already logged today,
// and appends a row to the "Plans" tab.
//
// It is WRITE-ONLY: it never sends sheet data back. A leaked URL or PIN can at
// worst add junk rows; it cannot be used to read patient data.
//
// Script property (Project Settings > Script properties):
//   STAFF_PIN   the PIN staff type once per device (8+ characters).
//
// Deploy: Deploy > New deployment > Web app
//   Execute as: Me        Who has access: Anyone

const SHEET_NAME   = 'Plans';
const PLAN_ID_COL  = 10;   // column J
const MAX_BAD_PINS = 20;   // after this many wrong PINs, refuse all writes for an hour

// Health check: open the /exec URL in a browser to confirm the deployment works.
function doGet() {
  return json_({ ok: true, service: 'cdic-treatment-plan-log' });
}

function doPost(e) {
  let d;
  try {
    d = JSON.parse(e.postData.contents);
  } catch (_) {
    return json_({ ok: false, error: 'bad json' });
  }

  const props = PropertiesService.getScriptProperties();
  const pin = props.getProperty('STAFF_PIN');
  if (!pin) return json_({ ok: false, error: 'not configured' });

  const cache = CacheService.getScriptCache();
  const badPins = Number(cache.get('badPins') || 0);
  if (badPins >= MAX_BAD_PINS) return json_({ ok: false, error: 'locked' });
  if (String(d.pin || '') !== pin) {
    cache.put('badPins', String(badPins + 1), 3600);
    return json_({ ok: false, error: 'bad pin' });
  }

  const patient = text_(d.patient);
  if (!patient) return json_({ ok: false, error: 'missing patient' });
  const planId = text_(d.planId, 40);
  const link = /^https?:\/\/[^\s"<>]+$/.test(String(d.link || '')) && String(d.link).length <= 45000
    ? String(d.link)
    : '';

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sh = sheet_();
    const last = sh.getLastRow();
    if (planId && last > 1 &&
        sh.getRange(2, PLAN_ID_COL, last - 1, 1)
          .createTextFinder(planId).matchEntireCell(true).findNext()) {
      return json_({ ok: true, duplicate: true });
    }
    sh.appendRow([
      new Date(),               // A Date
      patient,                  // B Patient
      text_(d.phone, 40),       // C Phone
      money_(d.caseTotal),      // D Case total
      money_(d.discount),       // E Discount
      '',                       // F Net total (formula, set below)
      text_(d.coordinator, 60), // G Coordinator
      text_(d.location, 60),    // H Location
      link,                     // I Plan link
      planId,                   // J Plan ID
    ]);
    const row = sh.getLastRow();
    sh.getRange(row, 6).setFormulaR1C1('=RC[-2]-RC[-1]');
    sh.getRange(row, 1).setNumberFormat('M/d/yyyy h:mm am/pm');
    sh.getRange(row, 4, 1, 3).setNumberFormat('$#,##0.00');
    return json_({ ok: true });
  } finally {
    lock.releaseLock();
  }
}

// Run this once from the editor (select it, then Run) to grant access and check setup.
function checkSetup() {
  const pin = PropertiesService.getScriptProperties().getProperty('STAFF_PIN');
  const sh = sheet_();
  Logger.log('Sheet tab found: %s', sh ? sh.getName() : 'NO, check SHEET_NAME');
  Logger.log('STAFF_PIN set: %s', pin ? 'yes (' + pin.length + ' characters)' : 'NO, add it in Project Settings');
}

function sheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
}

// Plain text only: drop control characters, cap the length, and stop a value
// that starts with = + - @ from being read as a formula.
function text_(v, max) {
  const s = String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max || 120);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function money_(v) {
  const n = Number(v);
  return isFinite(n) ? Math.round(n * 100) / 100 : 0;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
