"""The screen: one page, no build step. It calls the same routes everyone else here calls
(POST /batches, GET /batches, GET /batches/{id}/shipments, POST /shipments/{id}/decide) -- there is
no shortcut it takes that a curl command could not also take."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CrossExam -- step 7: the screen</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; background: #f6f1e7; color: #1c2a3a; font: 15px/1.5 -apple-system, Segoe UI, Roboto, sans-serif; }
  header { padding: 20px 28px; background: #0f1b2d; color: #fff; }
  header h1 { margin: 0; font-size: 18px; font-weight: 600; }
  header p { margin: 4px 0 0; font-size: 13px; color: #9fb3c8; }
  main { max-width: 980px; margin: 0 auto; padding: 24px 28px 60px; }
  section { background: #fff; border: 1px solid #e3dac8; border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; }
  h2 { font-size: 14px; text-transform: uppercase; letter-spacing: .04em; color: #6b5b3e; margin: 0 0 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid #efe8d8; vertical-align: top; }
  th { color: #6b5b3e; font-weight: 600; font-size: 12px; text-transform: uppercase; }
  .route-auto_approve { color: #1a7a4c; font-weight: 600; }
  .route-investigate, .route-human_review { color: #a3401b; font-weight: 600; }
  button, input[type=submit] {
    background: #2459a6; color: #fff; border: none; border-radius: 6px; padding: 6px 14px;
    font-size: 13px; cursor: pointer;
  }
  button.reject { background: #a3401b; }
  select { font-size: 13px; padding: 4px; border-radius: 6px; border: 1px solid #c9bfa6; }
  input[type=file] { display: block; margin: 10px 0; }
  .muted { color: #7a7265; font-size: 13px; }
  .pill { display: inline-block; background: #eef1f6; border-radius: 10px; padding: 1px 8px; font-size: 12px; }
  .decide { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
</style>
</head>
<body>
<header>
  <h1>CrossExam &mdash; step 7: seeing inside</h1>
  <p>A shipment that is not a clean auto_approve now carries a real agent's plain-language finding, and waits
     for a person. Pick a role below and try to approve PO-40002 (678,300.00) as an AP executive, then as a
     finance manager.</p>
</header>
<main>
  <section>
    <h2>Upload papers</h2>
    <form id="upload">
      <input type="file" name="files" multiple required>
      <input type="submit" value="Upload and process">
    </form>
    <p class="muted" id="upload-status"></p>
  </section>
  <section>
    <h2>Batches</h2>
    <table id="batches"><thead><tr><th>Name</th><th>Status</th><th>Created</th><th></th></tr></thead><tbody></tbody></table>
  </section>
  <section>
    <h2 id="shipments-title">Shipments</h2>
    <table id="shipments">
      <thead><tr><th>PO</th><th>Status</th><th>Route</th><th>Pay</th><th>Debit note</th><th>Finding</th><th>Decide as</th></tr></thead>
      <tbody></tbody>
    </table>
    <p class="muted" id="decide-status"></p>
  </section>
</main>
<script>
async function loadBatches() {
  const rows = await (await fetch('/batches')).json();
  const body = document.querySelector('#batches tbody');
  body.innerHTML = '';
  for (const b of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${b.name}</td><td><span class="pill">${b.status}</span></td>` +
      `<td class="muted">${new Date(b.created_at).toLocaleString()}</td>` +
      `<td><button data-id="${b.id}">See shipments</button></td>`;
    body.appendChild(tr);
  }
  body.querySelectorAll('button').forEach(btn => btn.onclick = () => loadShipments(btn.dataset.id));
  if (rows.length) loadShipments(rows[0].id);
}

async function loadShipments(batchId) {
  const rows = await (await fetch(`/batches/${batchId}/shipments`)).json();
  document.querySelector('#shipments-title').textContent = `Shipments for this batch (${rows.length})`;
  const body = document.querySelector('#shipments tbody');
  body.innerHTML = '';
  for (const p of rows) {
    const tr = document.createElement('tr');
    const canDecide = p.status === 'awaiting_approval';
    const decideHtml = canDecide ? `
      <div class="decide">
        <select class="role"><option value="ap_executive">AP executive</option><option value="finance_manager">Finance manager</option></select>
        <button class="approve" data-id="${p.id}">Approve</button>
        <button class="reject" data-id="${p.id}">Reject</button>
      </div>` : '';
    tr.innerHTML = `<td>${p.po_number || '(no PO found)'}</td><td><span class="pill">${p.status}</span></td>` +
      `<td class="route-${p.route}">${p.route || '-'}</td>` +
      `<td>${Number(p.payable_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>` +
      `<td>${Number(p.debit_note_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>` +
      `<td class="muted">${p.finding}</td><td>${decideHtml}</td>`;
    body.appendChild(tr);
  }
  body.querySelectorAll('button.approve, button.reject').forEach(btn => btn.onclick = () => decide(btn, batchId));
}

async function decide(btn, batchId) {
  const row = btn.closest('tr');
  const role = row.querySelector('.role').value;
  const action = btn.classList.contains('reject') ? 'reject' : 'approve';
  const status = document.querySelector('#decide-status');
  const res = await fetch(`/shipments/${btn.dataset.id}/decide?decision=${action}&actor=recording&role=${role}`, { method: 'POST' });
  const body = await res.json().catch(() => ({}));
  status.textContent = res.ok
    ? `${role} ${action}d this shipment -- now ${body.status}.`
    : `${res.status}: ${body.detail || 'refused'}`;
  loadShipments(batchId);
}

document.querySelector('#upload').addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = document.querySelector('#upload-status');
  const files = e.target.files.files;
  if (!files.length) return;
  const form = new FormData();
  for (const f of files) form.append('files', f);
  status.textContent = `Reading ${files.length} paper(s) -- this calls the model, so it can take a few seconds...`;
  const res = await fetch('/batches', { method: 'POST', body: form });
  if (!res.ok) { status.textContent = `Something went wrong (${res.status}). See the API logs.`; return; }
  const body = await res.json();
  status.textContent = body.duplicate_files.length
    ? `${body.accepted} new, ${body.duplicate_files.length} already seen before (same file, no new work): ${body.duplicate_files.join(', ')}`
    : `${body.accepted} new paper(s) read, split, filled, checked, grouped and matched.`;
  loadBatches();
});

loadBatches();
setInterval(loadBatches, 5000);
</script>
</body>
</html>"""
