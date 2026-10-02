const $ = s => document.querySelector(s);
const el = (t, a = {}, ...k) => {
  const e = document.createElement(t);
  for (const [x, v] of Object.entries(a)) x.startsWith("on") ? e.addEventListener(x.slice(2), v) : (e[x] = v);
  e.append(...k); return e;
};  // textContent only, never innerHTML: server data can't inject markup
let lastImport = null, tok = sessionStorage.tok, role = sessionStorage.role, who = sessionStorage.who, sel = null;
const STAFF_NEXT = { submitted: [["in_progress", "Start"]], in_progress: [["delivered", "Deliver"]], rejected: [["in_progress", "Rework"]] };
const CLIENT_NEXT = { delivered: [["accepted", "Accept"], ["rejected", "Reject"]] };

function say(text, ok) {
  const m = $("#msg"); m.textContent = text; m.className = ok ? "ok" : "err"; m.style.display = "block";
  clearTimeout(say.t);
  if (ok) say.t = setTimeout(() => (m.style.display = "none"), 3000);  // errors stay until clicked
}
$("#msg").onclick = () => ($("#msg").style.display = "none");
window.addEventListener("error", e => say("Script error: " + e.message));
window.addEventListener("unhandledrejection", e => say("Error: " + (e.reason && e.reason.message || e.reason)));

async function api(path, opt = {}) {
  const r = await fetch(path, { ...opt, headers: { ...(opt.headers || {}), ...(tok ? { Authorization: "Bearer " + tok } : {}) } });
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && tok) logout();
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail || r.statusText));
  return d;
}
const post = (p, body) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const run = f => async (...a) => { try { await f(...a); } catch (e) { say(e.message); } };

function logout() { sessionStorage.clear(); tok = role = who = sel = lastImport = null; render(); }
$("#out").onclick = logout;

function loginView() {
  const email = el("input", { type: "email", placeholder: "email", required: true });
  const pw = el("input", { type: "password", placeholder: "password", required: true });
  return el("section", {}, el("h2", {}, "Log in"), el("form", {
    onsubmit: run(async e => {
      e.preventDefault();
      const d = await post("/login", { email: email.value, password: pw.value });
      tok = sessionStorage.tok = d.token; role = sessionStorage.role = d.role; who = sessionStorage.who = d.name;
      render();
    })
  }, email, pw, el("button", {}, "Log in")));
}

function requestsTable(rows, actions, onSelect) {
  const t = el("table", {}, el("tr", {}, ...["#", "Task", "Assigned/Req.", "Deadline", "Status", ""].map(h => el("th", {}, h))));
  for (const r of rows) {
    const acts = (actions[r.status] || []).map(([s, label]) =>
      el("button", { className: s === "rejected" && r.status === "delivered" ? "danger" : "", onclick: run(async () => { await post(`/requests/${r.id}/status`, { status: s }); say(`#${r.id} → ${s}`, true); refresh(); }) }, label));
    if (onSelect && !["delivered", "accepted"].includes(r.status))
      acts.push(el("button", { className: "ghost", onclick: () => { sel = r.id; refresh(); } }, "Assign episodes"));
    t.append(el("tr", { className: r.id === sel ? "sel" : "" },
      el("td", {}, r.id), el("td", {}, r.task_name), el("td", {}, `${r.assigned}/${r.episodes_requested}`),
      el("td", {}, r.deadline), el("td", {}, el("span", { className: "tag s-" + r.status }, r.status)), el("td", {}, ...acts)));
  }
  return t;
}

async function clientView() {
  const f = { task: el("input", { placeholder: "task name", required: true }),
    n: el("input", { type: "number", min: 1, value: 10, required: true, style: "width:70px" }),
    d: el("input", { type: "date", required: true }), notes: el("input", { placeholder: "notes" }) };
  const form = el("form", { onsubmit: run(async e => {
    e.preventDefault();
    const d = await post("/requests", { task_name: f.task.value, episodes_requested: +f.n.value, deadline: f.d.value, notes: f.notes.value });
    say(`Request #${d.id} created`, true); refresh();
  }) }, f.task, f.n, f.d, f.notes, el("button", {}, "Create"));
  const rows = await api("/requests");
  return [el("section", {}, el("h2", {}, "New request"), form),
    el("section", {}, el("h2", {}, `My requests (${rows.length})`), rows.length ? requestsTable(rows, CLIENT_NEXT) : "No requests yet.")];
}

async function staffView() {
  const rows = await api("/requests");
  const open = r => !["delivered", "accepted"].includes(r.status);
  if (sel && !rows.some(r => r.id === sel && open(r))) sel = null;  // panel only for assignable requests
  const out = [el("section", {}, el("h2", {}, `All requests (${rows.length})`), rows.length ? requestsTable(rows, STAFF_NEXT, true) : "No requests yet.")];
  const file = el("input", { type: "file", accept: ".csv", onchange: run(async () => {
    const d = await api("/import", { method: "POST", headers: { "Content-Type": "text/csv" }, body: await file.files[0].text() });
    lastImport = d;
    say(`Imported ${d.imported}, skipped ${Object.values(d.skipped).reduce((a, b) => a + b, 0)}`, true);
    file.value = ""; refresh();
  }) });
  out.push(el("section", {}, el("h2", {}, "Import episodes (CSV)"), file));
  if (lastImport) out.push(reportSection(lastImport));
  if (sel) out.push(await episodesPanel());
  return out;
}

function reportSection(d) {
  const reasons = Object.entries(d.skipped), skipped = reasons.reduce((a, [, n]) => a + n, 0);
  const t = el("table", {}, el("tr", {}, ...["Line", "Episode", "Reason"].map(h => el("th", {}, h))));
  for (const x of d.details) t.append(el("tr", {}, el("td", {}, x.line), el("td", {}, x.episode_id || "—"), el("td", {}, x.reason)));
  return el("section", {}, el("h2", {}, `Last import: ${d.rows} rows, ${d.imported} imported, ${skipped} skipped`),
    ...reasons.map(([r, n]) => el("div", {}, el("span", { className: "tag" }, n), " " + r)),
    d.details.length ? t : "", skipped > d.details.length ? el("p", {}, `Showing the first ${d.details.length} skipped rows.`) : "");
}

async function episodesPanel() {
  const task = el("input", { placeholder: "task name filter", value: episodesPanel.task || "" });
  const q = el("select", {}, ...["", "good", "usable", "bad"].map(v => el("option", { value: v, selected: v === (episodesPanel.q || "") }, v || "any quality")));
  const qs = new URLSearchParams({ unassigned: "true", limit: "200" });
  if (episodesPanel.task) qs.set("task_name", episodesPanel.task);
  if (episodesPanel.q) qs.set("quality", episodesPanel.q);
  const eps = await api("/episodes?" + qs);
  const boxes = [];
  const t = el("table", {}, el("tr", {}, ...["", "Episode", "Robot", "Task", "Quality"].map(h => el("th", {}, h))));
  for (const e of eps) {
    const cb = el("input", { type: "checkbox", value: e.episode_id }); boxes.push(cb);
    t.append(el("tr", {}, el("td", {}, cb), el("td", {}, e.episode_id), el("td", {}, e.robot_id), el("td", {}, e.task_name), el("td", {}, e.quality)));
  }
  return el("section", {}, el("h2", {}, `Assign episodes to request #${sel}`),
    task, q, el("button", { className: "ghost", onclick: () => { episodesPanel.task = task.value; episodesPanel.q = q.value; refresh(); } }, "Filter"),
    el("button", { onclick: run(async () => {
      const ids = boxes.filter(b => b.checked).map(b => b.value);
      if (!ids.length) return say("Select at least one episode");
      await post(`/requests/${sel}/episodes`, { episode_ids: ids });
      say(`Assigned ${ids.length}`, true); refresh();
    }) }, "Assign selected"), eps.length ? t : el("p", {}, "No unassigned episodes match."));
}

const refresh = run(async () => {
  const view = await (role === "client" ? clientView() : staffView());
  $("#app").replaceChildren(...view);
});
function render() {
  $("#who").textContent = who ? `${who} (${role})` : ""; $("#out").hidden = !tok;
  tok ? refresh() : $("#app").replaceChildren(loginView());
}
render();