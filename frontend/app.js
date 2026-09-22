"use strict";

/* Flux frontend — vanilla JS, no build step, no external dependencies.
 * All DOM wiring uses addEventListener (no inline handlers) per the
 * XSS-hardening requirement in the spec. */

const PAGE_SIZE = 25;
const POLL_INTERVAL_MS = 30000;
const ALERT_SCORE_THRESHOLD = 65;
const NOTIFIED_IDS_KEY = "flux.notifiedIds";
const ALERTS_ENABLED_KEY = "flux.alertsEnabled";

const state = {
  jobs: [],
  cvEvidence: [],
  cvEvidenceCount: 0,
  cvRoles: [],
  filterRole: null,
  lastScan: null,
  scanning: false,
  sources: [],
  page: 1,
  filters: { role: "all", band: "all", location: "all", posted: "all", type: "all", bookmarks: "all" },
  sort: "score",
};

const el = (id) => document.getElementById(id);

function safeLocalGet(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch (_) {
    return fallback;
  }
}

function safeLocalSet(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (_) {
    /* private browsing / storage disabled — alerts just won't dedupe across reloads */
  }
}

function fetchJson(url, options = {}) {
  return fetch(url, options).then(async (resp) => {
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);
    return data;
  });
}

function showToast(message, ms = 3500) {
  const toast = el("toast");
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast._t);
  showToast._t = window.setTimeout(() => { toast.hidden = true; }, ms);
}

// --- Data loading -----------------------------------------------------

function loadJobs() {
  return fetchJson("/api/jobs").then((data) => {
    const previousIds = new Set(state.jobs.map((j) => j.id));
    state.jobs = data.jobs || [];
    state.cvEvidence = data.cv_evidence || [];
    state.cvEvidenceCount = state.cvEvidence.length;
    state.cvRoles = data.cv_roles || [];
    state.filterRole = data.filter_role || null;
    state.lastScan = data.last_scan;
    state.scanning = !!data.scanning;
    state.sources = data.sources || [];
    maybeNotifyNewMatches(previousIds);
    renderCvPanel();
    renderStatusLine();
    render();
  });
}

function maybeNotifyNewMatches(previousIds) {
  if (!safeLocalGet(ALERTS_ENABLED_KEY, false)) return;
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const notified = new Set(safeLocalGet(NOTIFIED_IDS_KEY, []));
  let changed = false;
  for (const job of state.jobs) {
    const isNew = !previousIds.has(job.id) && previousIds.size > 0;
    const score = job.match ? job.match.score : 0;
    if (isNew && score >= ALERT_SCORE_THRESHOLD && !notified.has(job.id)) {
      new Notification(`New ${score}% match: ${job.title}`, {
        body: `${job.company} — ${job.location}`,
        tag: job.id,
      });
      notified.add(job.id);
      changed = true;
    }
  }
  if (changed) {
    // Keep the set from growing forever.
    safeLocalSet(NOTIFIED_IDS_KEY, Array.from(notified).slice(-500));
  }
}

// --- Filtering / sorting -----------------------------------------------

function minutesSince(iso) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return Infinity;
  return (Date.now() - then) / 60000;
}

function jobMatchesFilters(job) {
  const f = state.filters;
  if (f.role !== "all" && job.role !== f.role) return false;
  if (f.band !== "all" && (!job.match || job.match.band !== f.band)) return false;
  if (f.location !== "all" && job.location_category !== f.location) return false;
  if (f.posted !== "all" && minutesSince(job.posted_at) > Number(f.posted)) return false;
  if (f.type !== "all" && job.employment_category !== f.type) return false;
  if (f.bookmarks === "saved" && !job.bookmarked) return false;
  if (f.bookmarks === "unsaved" && job.bookmarked) return false;
  return true;
}

function sortJobs(jobs) {
  const copy = jobs.slice();
  copy.sort((a, b) => {
    if (state.sort === "latest") return new Date(b.posted_at) - new Date(a.posted_at);
    if (state.sort === "oldest") return new Date(a.posted_at) - new Date(b.posted_at);
    // default: score desc, then recency desc
    const sa = a.match ? a.match.score : 0;
    const sb = b.match ? b.match.score : 0;
    if (sb !== sa) return sb - sa;
    return new Date(b.posted_at) - new Date(a.posted_at);
  });
  return copy;
}

function heatClass(iso) {
  const mins = minutesSince(iso);
  if (mins <= 30) return "heat-red";
  if (mins <= 60) return "heat-orange";
  if (mins <= 180) return "heat-amber";
  return "heat-cyan";
}

function relativeTime(iso) {
  const mins = minutesSince(iso);
  if (!Number.isFinite(mins)) return "unknown";
  if (mins < 1) return "just now";
  if (mins < 60) return `${Math.round(mins)}m ago`;
  if (mins < 24 * 60) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / 1440)}d ago`;
}

// --- Rendering -----------------------------------------------------

function renderStatusLine() {
  const line = el("status-line");
  const liveCount = state.sources.filter((s) => s.ok).length;
  const scanTxt = state.lastScan ? new Date(state.lastScan).toLocaleString() : "never";
  const scanningTxt = state.scanning ? " — scan in progress…" : "";
  line.textContent = `Last scan: ${scanTxt} · ${liveCount}/${state.sources.length || 0} sources responded${scanningTxt}`;
}

function renderCvPanel() {
  const panel = el("cv-panel");
  if (!state.cvEvidenceCount) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const roleLabel = state.filterRole ? state.filterRole.replace(/_/g, " ") : "none detected";
  panel.textContent = "";
  const p1 = document.createElement("div");
  const strongEvidence = document.createElement("strong");
  strongEvidence.textContent = `${state.cvEvidenceCount} skill areas`;
  p1.appendChild(document.createTextNode("CV parsed: "));
  p1.appendChild(strongEvidence);
  p1.appendChild(document.createTextNode(` detected · auto-filtered role: ${roleLabel}`));
  panel.appendChild(p1);
}

function render() {
  const filtered = sortJobs(state.jobs.filter(jobMatchesFilters));
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  state.page = Math.min(state.page, totalPages);
  const start = (state.page - 1) * PAGE_SIZE;
  const pageItems = filtered.slice(start, start + PAGE_SIZE);

  el("result-count").textContent = `${filtered.length} job${filtered.length === 1 ? "" : "s"} match`;

  const grid = el("job-grid");
  grid.textContent = "";
  const emptyState = el("empty-state");
  emptyState.hidden = pageItems.length > 0;

  const tpl = el("job-card-template");
  for (const job of pageItems) {
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector(".job-card");
    card.classList.add(heatClass(job.posted_at));

    const link = node.querySelector(".job-title-link");
    link.textContent = job.title;
    link.href = job.url || "#";

    node.querySelector(".job-company-location").textContent = `${job.company} · ${job.location}`;
    node.querySelector(".job-source-posted").textContent = `${job.source} · ${relativeTime(job.posted_at)}`;

    const badge = node.querySelector(".score-badge");
    const match = job.match || { score: 0, band: "Weak", gaps: [], breakdown: {} };
    badge.textContent = `${match.score}% ${match.band}`;
    badge.classList.add(match.band);

    const gapList = node.querySelector(".gap-list");
    if (match.gaps && match.gaps.length) {
      const top2 = match.gaps.slice(0, 2).map((g) => g.label).join(", ");
      gapList.textContent = `Missing: ${top2}`;
    } else {
      gapList.textContent = state.cvEvidenceCount ? "No gaps detected" : "Upload a CV to see gap analysis";
    }

    const detailToggle = node.querySelector(".detail-toggle");
    const detail = node.querySelector(".job-detail");
    detailToggle.addEventListener("click", () => {
      const isHidden = detail.hidden;
      detail.hidden = !isHidden;
      detailToggle.setAttribute("aria-expanded", String(isHidden));
      if (isHidden) {
        detail.textContent = "";
        const rows = [
          ["Requirements", match.breakdown.requirements, 60],
          ["Title match", match.breakdown.title, 20],
          ["Seniority", match.breakdown.seniority, 10],
          ["Location", match.breakdown.location, 10],
        ];
        for (const [label, value, max] of rows) {
          const row = document.createElement("div");
          row.className = "breakdown-row";
          row.appendChild(document.createTextNode(label));
          const val = document.createElement("span");
          val.textContent = `${value ?? 0} / ${max}`;
          row.appendChild(val);
          detail.appendChild(row);
        }
        if (match.gaps && match.gaps.length > 2) {
          const more = document.createElement("div");
          more.textContent = `All gaps: ${match.gaps.map((g) => g.label).join(", ")}`;
          detail.appendChild(more);
        }
      }
    });

    const bookmarkBtn = node.querySelector(".bookmark-btn");
    bookmarkBtn.setAttribute("aria-pressed", String(!!job.bookmarked));
    bookmarkBtn.textContent = job.bookmarked ? "⭐" : "☆";
    bookmarkBtn.addEventListener("click", () => toggleBookmark(job.id, bookmarkBtn));

    grid.appendChild(node);
  }

  const pagination = el("pagination");
  pagination.hidden = filtered.length <= PAGE_SIZE;
  el("page-indicator").textContent = `Page ${state.page} of ${totalPages}`;
  el("prev-page").disabled = state.page <= 1;
  el("next-page").disabled = state.page >= totalPages;
}

function toggleBookmark(jobId, button) {
  fetchJson("/api/bookmark", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Requested-With": "Flux" },
    body: JSON.stringify({ job_id: jobId }),
  }).then((data) => {
    const job = state.jobs.find((j) => j.id === jobId);
    if (job) job.bookmarked = data.bookmarked;
    button.setAttribute("aria-pressed", String(data.bookmarked));
    button.textContent = data.bookmarked ? "⭐" : "☆";
    render();
  }).catch((err) => showToast(err.message));
}

// --- Actions -----------------------------------------------------

function triggerScan() {
  fetchJson("/api/scan", { method: "POST", headers: { "X-Requested-With": "Flux" } })
    .then(() => {
      showToast("Scan started…");
      state.scanning = true;
      renderStatusLine();
    })
    .catch((err) => showToast(err.message));
}

function uploadCv(file) {
  const formData = new FormData();
  formData.append("cv", file);
  fetchJson("/api/upload-cv", {
    method: "POST",
    headers: { "X-Requested-With": "Flux" },
    body: formData,
  }).then((data) => {
    showToast(data.message || "CV uploaded");
    for (const job of state.jobs) {
      if (data.job_scores && data.job_scores[job.id]) {
        job.match = data.job_scores[job.id];
      }
    }
    state.cvEvidenceCount = data.evidence_areas || 0;
    state.filterRole = data.filter_role;
    if (data.filter_role) {
      state.filters.role = data.filter_role;
      el("f-role").value = data.filter_role;
    }
    renderCvPanel();
    render();
  }).catch((err) => showToast(err.message));
}

function requestAlerts() {
  if (!("Notification" in window)) {
    showToast("Desktop notifications aren't supported in this browser");
    return;
  }
  Notification.requestPermission().then((perm) => {
    const enabled = perm === "granted";
    safeLocalSet(ALERTS_ENABLED_KEY, enabled);
    el("alerts-btn").setAttribute("aria-pressed", String(enabled));
    el("alerts-btn").textContent = enabled ? "🔔 Alerts on" : "🔕 Alerts off";
    showToast(enabled ? "Desktop alerts enabled for 65%+ matches" : "Notifications permission denied");
  });
}

// --- Wiring -----------------------------------------------------

function wireFilters() {
  const bindings = [
    ["f-role", "role"], ["f-band", "band"], ["f-location", "location"],
    ["f-posted", "posted"], ["f-type", "type"], ["f-bookmarks", "bookmarks"],
  ];
  for (const [id, key] of bindings) {
    el(id).addEventListener("change", (e) => {
      state.filters[key] = e.target.value;
      state.page = 1;
      render();
    });
  }
  el("f-sort").addEventListener("change", (e) => {
    state.sort = e.target.value;
    render();
  });
}

function wireActions() {
  el("scan-btn").addEventListener("click", triggerScan);
  el("upload-btn").addEventListener("click", () => el("cv-input").click());
  el("cv-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) uploadCv(file);
    e.target.value = "";
  });
  el("alerts-btn").addEventListener("click", requestAlerts);
  el("prev-page").addEventListener("click", () => { state.page -= 1; render(); });
  el("next-page").addEventListener("click", () => { state.page += 1; render(); });
}

function init() {
  wireFilters();
  wireActions();
  if (safeLocalGet(ALERTS_ENABLED_KEY, false) && "Notification" in window && Notification.permission === "granted") {
    el("alerts-btn").setAttribute("aria-pressed", "true");
    el("alerts-btn").textContent = "🔔 Alerts on";
  }
  loadJobs().catch((err) => showToast(err.message));
  window.setInterval(() => loadJobs().catch(() => {}), POLL_INTERVAL_MS);
}

document.addEventListener("DOMContentLoaded", init);
