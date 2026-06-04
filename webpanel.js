const $ = (id) => document.getElementById(id);

const state = {
  diskUsageChart: null,
  movesChart: null,
  config: null,
  lastStatsOk: false,
};

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  const value = Number(bytes);
  if (!Number.isFinite(value)) return "—";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let v = Math.max(0, value);
  let u = 0;
  while (v >= 1024 && u < units.length - 1) {
    v /= 1024;
    u += 1;
  }
  const decimals = u === 0 ? 0 : u <= 2 ? 1 : 2;
  return `${v.toFixed(decimals)} ${units[u]}`;
}

function formatUptime(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.max(0, Math.floor(Number(seconds)));
  if (!Number.isFinite(s)) return "—";
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const parts = [];
  if (days) parts.push(`${days}d`);
  if (days || hours) parts.push(`${hours}u`);
  parts.push(`${mins}m`);
  return parts.join(" ");
}

function formatDate(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function formatShortTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString();
}

function updateBackupStrategyHelp(strategy) {
  const el = document.getElementById("backupStrategyHelp");
  if (!el) return;
  const v = String(strategy || "").toLowerCase();
  if (v === "most_free_space") {
    el.textContent =
      "Always picks the disk with the most free space. Useful to keep usage balanced.";
    return;
  }
  if (v === "least_used_pct") {
    el.textContent =
      "Always picks the disk with the lowest percent used. Useful when disks have different sizes.";
    return;
  }
  if (v === "path_hash") {
    el.textContent =
      "Keeps the same path/file mostly on the same disk (hash-based). Useful for predictability; if space is low it will try other disks.";
    return;
  }
  el.textContent =
    "Distributes files round-robin across disks. Simple and a good default.";
}

function updateRaidSimulationHelp(value) {
  const el = document.getElementById("raidSimulationHelp");
  if (!el) return;
  const v = String(value || "").toLowerCase();
  if (v === "raid1") {
    el.textContent =
      "Virtual RAID 1: the file is stored on 2 different disks (2 copies).";
    return;
  }
  if (v === "raid5") {
    el.textContent =
      "Virtual RAID 5: the file is stored on 2 disks (2 copies). This is software-based and does not use classic parity limits.";
    return;
  }
  if (v === "raid6") {
    el.textContent =
      "Virtual RAID 6: the file is stored on 3 disks (3 copies). This is software-based and works with disks of different sizes.";
    return;
  }
  if (v === "raid10") {
    el.textContent =
      "Virtual RAID 10: the file is stored on 2 disks (2 copies), selected as a 'pair' for extra distribution.";
    return;
  }
  el.textContent =
    "Virtual RAID 0: the file is stored only once (no redundancy), distributed according to the selected backup strategy.";
}

function normalizeRaidSimulation(value) {
  const v = String(value || "").trim().toLowerCase();
  const alias = {
    none: "raid0",
    raid0: "raid0",
    raid_0: "raid0",
    mirror_2: "raid1",
    raid1: "raid1",
    raid_1: "raid1",
    raid5: "raid5",
    raid_5: "raid5",
    raid6: "raid6",
    raid_6: "raid6",
    raid10: "raid10",
    raid_10: "raid10",
  };
  return alias[v] || "raid0";
}

function setStatus(ok, text) {
  const badge = $("statusBadge");
  badge.textContent = text;
  badge.style.background = ok ? "rgba(85, 216, 140, 0.14)" : "rgba(255, 112, 112, 0.14)";
  badge.style.border = ok ? "1px solid rgba(85, 216, 140, 0.35)" : "1px solid rgba(255, 112, 112, 0.35)";
}

function setSaveStatus(text, ok) {
  const el = $("saveStatus");
  el.textContent = text;
  el.style.color = ok ? "rgba(85, 216, 140, 0.85)" : "rgba(255, 112, 112, 0.85)";
}

function navInit() {
  const buttons = Array.from(document.querySelectorAll(".nav-item"));
  const views = {
    dashboard: $("view-dashboard"),
    config: $("view-config"),
  };
  const setView = (name) => {
    for (const b of buttons) b.classList.toggle("active", b.dataset.view === name);
    for (const key of Object.keys(views)) views[key].classList.toggle("active", key === name);
  };
  for (const b of buttons) {
    b.addEventListener("click", () => setView(b.dataset.view));
  }
}

function ensureDiskUsageChart() {
  const canvas = $("diskUsageChart");
  if (!window.Chart) {
    $("diskUsageHint").textContent = "Chart library not loaded. Check internet access or CDN blocking.";
    return null;
  }
  if (state.diskUsageChart) return state.diskUsageChart;
  state.diskUsageChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Used (%)",
          data: [],
          backgroundColor: "rgba(90, 125, 255, 0.35)",
          borderColor: "rgba(90, 125, 255, 0.7)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100 },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.y.toFixed(1)}% used`,
          },
        },
      },
    },
  });
  return state.diskUsageChart;
}

function ensureMovesChart() {
  const canvas = $("movesChart");
  if (!window.Chart) {
    $("movesHint").textContent = "Chart library not loaded. Check internet access or CDN blocking.";
    return null;
  }
  if (state.movesChart) return state.movesChart;
  state.movesChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Files moved",
          data: [],
          fill: false,
          borderColor: "rgba(85, 216, 140, 0.8)",
          backgroundColor: "rgba(85, 216, 140, 0.2)",
          tension: 0.25,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
  return state.movesChart;
}

function renderInsights(insights) {
  const root = $("insights");
  root.innerHTML = "";
  if (!Array.isArray(insights) || insights.length === 0) {
    const div = document.createElement("div");
    div.className = "insight";
    div.innerHTML = `<div class="insight-title">No insights</div><div class="insight-body">No data available yet.</div>`;
    root.appendChild(div);
    return;
  }
  for (const item of insights) {
    const div = document.createElement("div");
    div.className = "insight";
    const title = (item && item.title) || "Insight";
    const body = (item && item.body) || "";
    div.innerHTML = `<div class="insight-title"></div><div class="insight-body"></div>`;
    div.querySelector(".insight-title").textContent = title;
    div.querySelector(".insight-body").textContent = body;
    root.appendChild(div);
  }
}

function pillForUsedPct(pct) {
  const p = Number(pct);
  if (!Number.isFinite(p)) return "pill";
  if (p >= 90) return "pill bad";
  if (p >= 75) return "pill warn";
  return "pill good";
}

function renderDisksOverview(disks) {
  const root = $("disksOverview");
  const hint = $("disksOverviewHint");
  root.innerHTML = "";
  hint.textContent = "";

  const list = Array.isArray(disks) ? disks : [];
  if (!list.length) {
    hint.textContent = "No disks in config.yml or no data yet.";
    return;
  }

  const head = document.createElement("div");
  head.className = "t-head";
  head.innerHTML = "<div>Naam</div><div>Pad</div><div>Used</div><div>Free</div>";
  root.appendChild(head);

  let errCount = 0;
  for (const d of list) {
    const row = document.createElement("div");
    row.className = "t-row";

    const name = document.createElement("div");
    name.textContent = d.name || "disk";

    const path = document.createElement("div");
    path.className = "muted";
    path.textContent = d.path || "—";

    const used = document.createElement("div");
    const free = document.createElement("div");

    if (d.error) {
      errCount += 1;
      used.innerHTML = `<span class="pill bad">ERROR</span>`;
      free.textContent = "—";
    } else {
      const pct = Number(d.used_pct ?? 0);
      used.innerHTML = `<span class="${pillForUsedPct(pct)}">${pct.toFixed(1)}%</span>`;
      free.textContent = formatBytes(d.free_bytes);
    }

    row.appendChild(name);
    row.appendChild(path);
    row.appendChild(used);
    row.appendChild(free);
    root.appendChild(row);
  }

  if (errCount) hint.textContent = `${errCount} disk(s) have an error (path not reachable or no permission).`;
}

function describeEvent(e) {
  const type = e?.type || "";
  if (type === "move") {
    const disk = e.disk ? `Disk: ${e.disk}` : "Disk: —";
    const mode = e.mode ? `Mode: ${e.mode}` : "Mode: —";
    const bytes = formatBytes(e.bytes);
    const src = e.src || "—";
    const dst = e.dst || "—";
    return `${disk} • ${mode} • ${bytes}\n${src} → ${dst}`;
  }
  if (type === "cleanup") {
    const action = e.action ? `Action: ${e.action}` : "Action: —";
    const bytes = formatBytes(e.bytes);
    return `${action} • ${bytes}`;
  }
  if (type === "error") {
    return String(e.message || "Unknown error");
  }
  return JSON.stringify(e || {});
}

function titleForEvent(e) {
  const type = e?.type || "";
  if (type === "move") return "Move";
  if (type === "cleanup") return "Cleanup";
  if (type === "error") return "Error";
  return "Event";
}

function renderRecentEvents(events) {
  const root = $("recentEvents");
  const hint = $("recentEventsHint");
  root.innerHTML = "";
  hint.textContent = "";

  const list = Array.isArray(events) ? events : [];
  if (!list.length) {
    hint.textContent = "No events yet (or no data yet).";
    return;
  }

  const maxItems = 12;
  const items = list.slice(-maxItems).reverse();
  for (const e of items) {
    const card = document.createElement("div");
    card.className = "event";

    const top = document.createElement("div");
    top.className = "event-top";

    const title = document.createElement("div");
    title.className = "event-title";
    title.textContent = titleForEvent(e);

    const time = document.createElement("div");
    time.className = "event-time";
    time.textContent = formatShortTime(e.ts);

    top.appendChild(title);
    top.appendChild(time);

    const body = document.createElement("div");
    body.className = "event-body";
    body.textContent = describeEvent(e);

    card.appendChild(top);
    card.appendChild(body);
    root.appendChild(card);
  }

  if (list.length > maxItems) hint.textContent = `Toon laatste ${maxItems} van ${list.length}.`;
}

function kvRow(key, value) {
  const row = document.createElement("div");
  row.className = "kv-row";
  const k = document.createElement("div");
  k.className = "kv-key";
  k.textContent = key;
  const v = document.createElement("div");
  v.className = "kv-val";
  v.textContent = value;
  row.appendChild(k);
  row.appendChild(v);
  return row;
}

function renderServices(services, configSummary) {
  const root = $("servicesList");
  const hint = $("servicesHint");
  root.innerHTML = "";
  hint.textContent = "";

  if (configSummary) {
    root.appendChild(kvRow("Input folders", String(configSummary.src_folders_count ?? "—")));
    root.appendChild(kvRow("Disks", String(configSummary.disks_count ?? "—")));
    root.appendChild(kvRow("Space Hunter disks", String(configSummary.space_hunter_disks_count ?? "—")));
  }

  const s = services && typeof services === "object" ? services : null;
  if (!s) {
    hint.textContent = "No service info available.";
    return;
  }

  const wp = s.webpanel || {};
  const wpValue = wp.enabled ? `on (${wp.host || "—"}:${wp.port || "—"})` : "off";
  root.appendChild(kvRow("Webpanel", wpValue));

  const fb = s.filebrowser || {};
  const fbValue = fb.enabled ? `on (port ${fb.port || "—"}, user ${fb.username || "—"})` : "off";
  root.appendChild(kvRow("Filebrowser", fbValue));

  const wd = s.webdav || {};
  const wdValue = wd.enabled ? `on (port ${wd.port || "—"})` : "off";
  root.appendChild(kvRow("WebDAV", wdValue));

  const sftp = s.sftp || {};
  const sftpValue = sftp.enabled ? `on (port ${sftp.port || "—"})` : "off";
  root.appendChild(kvRow("SFTP", sftpValue));

  const nfs = s.nfs || {};
  root.appendChild(kvRow("NFS", nfs.enabled ? "on" : "off"));

  const fuse = s.fuse || {};
  const fuseValue = fuse.enabled ? `on (${fuse.mount_point || "mount"})` : "off";
  root.appendChild(kvRow("FUSE", fuseValue));

  const rr = s.reverse_raid || {};
  const rrValue = rr.enabled ? `on (every ${rr.run_interval_minutes || "—"} min)` : "off";
  root.appendChild(kvRow("Reverse RAID", rrValue));
}

function updateDashboard(stats) {
  $("movedFilesTotal").textContent = stats.totals?.files_moved_total ?? "—";
  $("movedBytesTotal").textContent = formatBytes(stats.totals?.bytes_moved_total);
  $("errorsTotal").textContent = stats.totals?.errors_total ?? "—";
  $("cleanupTotal").textContent = `Cleanup actions: ${stats.totals?.cleanup_actions_total ?? "—"}`;

  if (stats.last_action?.type) {
    $("lastAction").textContent = stats.last_action.type;
    $("lastActionAt").textContent = formatDate(stats.last_action.ts);
  } else {
    $("lastAction").textContent = "—";
    $("lastActionAt").textContent = "—";
  }

  $("uptimeText").textContent = `Uptime: ${formatUptime(stats.uptime_seconds)}`;
  $("configPathText").textContent = `Config: ${stats.meta?.config_path ?? "—"}`;
  $("lastUpdatedText").textContent = `Last updated: ${new Date().toLocaleString()}`;

  const cycle = stats.cycle || {};
  const cycleMoved = Number(cycle.last_moved_files ?? 0);
  const cycleCleanup = Number(cycle.last_cleanup_actions ?? 0);
  const cycleErrors = Number(cycle.last_errors ?? 0);
  const cycleBytes = formatBytes(cycle.last_moved_bytes ?? 0);
  const cycleDur = formatUptime(cycle.last_duration_seconds ?? 0);
  $("cycleSummary").textContent = `${cycleMoved} moved`;
  $("cycleNextRun").textContent = `Next run: ${formatDate(cycle.next_run_ts)} • Duration: ${cycleDur} • Cleanup: ${cycleCleanup} • Errors: ${cycleErrors} • Bytes: ${cycleBytes}`;

  const diskChart = ensureDiskUsageChart();
  if (diskChart && Array.isArray(stats.disks_usage)) {
    diskChart.data.labels = stats.disks_usage.map((d) => d.name || d.path || "disk");
    diskChart.data.datasets[0].data = stats.disks_usage.map((d) => Number(d.used_pct ?? 0));
    diskChart.update();
    const worst = stats.disks_usage
      .slice()
      .sort((a, b) => (b.used_pct ?? 0) - (a.used_pct ?? 0))[0];
    if (worst) {
      $("diskUsageHint").textContent = `Highest usage: ${(worst.used_pct ?? 0).toFixed(1)}% (${worst.name || worst.path || "disk"})`;
    }
  }

  const movesChart = ensureMovesChart();
  const points = stats.timeseries?.moves ?? [];
  if (movesChart && Array.isArray(points)) {
    const labels = points.map((p) => {
      const d = new Date((p.ts || 0) * 1000);
      return Number.isNaN(d.getTime()) ? "—" : d.toLocaleTimeString();
    });
    movesChart.data.labels = labels;
    movesChart.data.datasets[0].data = points.map((p) => Number(p.files ?? 0));
    movesChart.update();
    $("movesHint").textContent = `Points: ${points.length}, total files: ${points.reduce((a, p) => a + Number(p.files ?? 0), 0)}`;
  }

  renderDisksOverview(stats.disks_usage);
  renderRecentEvents(stats.recent_actions);
  renderServices(stats.services, stats.config_summary);
  renderInsights(stats.insights);
}

async function fetchJson(url, opts) {
  const res = await fetch(url, opts);
  const ct = res.headers.get("content-type") || "";
  if (!res.ok) {
    let detail = "";
    if (ct.includes("application/json")) {
      const j = await res.json().catch(() => null);
      detail = j && j.error ? j.error : JSON.stringify(j);
    } else {
      detail = await res.text().catch(() => "");
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

async function loadStatsOnce() {
  try {
    const stats = await fetchJson("/api/stats");
    updateDashboard(stats);
    state.lastStatsOk = true;
    setStatus(true, "Status: online");
  } catch (e) {
    state.lastStatsOk = false;
    setStatus(false, `Status: fout (${String(e.message || e)})`);
  }
}

function rowInput(value, placeholder) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = value || "";
  if (placeholder) input.placeholder = placeholder;
  return input;
}

function rowNumber(value, min = 0, step = 1) {
  const input = document.createElement("input");
  input.type = "number";
  input.min = String(min);
  input.step = String(step);
  input.value = value === null || value === undefined ? "" : String(value);
  return input;
}

function removeButton() {
  const b = document.createElement("button");
  b.className = "btn secondary";
  b.type = "button";
  b.textContent = "Verwijderen";
  return b;
}

function splitLines(text) {
  const raw = text === null || text === undefined ? "" : String(text);
  return raw
    .split(/\r?\n/g)
    .map((s) => s.trim())
    .filter((s) => s);
}

function joinLines(list) {
  const arr = Array.isArray(list) ? list : [];
  return arr.map((s) => String(s || "").trim()).filter((s) => s).join("\n");
}

function actionSelect(value) {
  const sel = document.createElement("select");
  const options = [
    { value: "delete", label: "delete" },
    { value: "move", label: "move" },
  ];
  for (const o of options) {
    const opt = document.createElement("option");
    opt.value = o.value;
    opt.textContent = o.label;
    sel.appendChild(opt);
  }
  sel.value = value ? String(value) : "delete";
  return sel;
}

function renderSrcFolders(srcFolders) {
  const root = $("srcFoldersList");
  root.innerHTML = "";
  const list = Array.isArray(srcFolders) ? srcFolders : [];
  const ensureAtLeastOne = list.length ? list : [""];
  for (const value of ensureAtLeastOne) {
    const row = document.createElement("div");
    row.className = "row";
    const input = rowInput(value, "/path/to/input");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(input);
    row.appendChild(del);
    root.appendChild(row);
  }
}

function readSrcFolders() {
  const rows = Array.from($("srcFoldersList").querySelectorAll(".row"));
  const values = rows
    .map((r) => r.querySelector("input")?.value?.trim())
    .filter((v) => v);
  return values;
}

function renderReverseRaidSources(paths) {
  const root = $("reverseRaidSourcesList");
  root.innerHTML = "";
  const list = Array.isArray(paths) ? paths : [];
  const ensureAtLeastOne = list.length ? list : [""];
  for (const value of ensureAtLeastOne) {
    const row = document.createElement("div");
    row.className = "row";
    const input = rowInput(value, "/path/to/source");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(input);
    row.appendChild(del);
    root.appendChild(row);
  }
}

function readReverseRaidSources() {
  const root = $("reverseRaidSourcesList");
  const rows = Array.from(root.querySelectorAll(".row"));
  return rows
    .map((r) => r.querySelector("input")?.value?.trim())
    .filter((v) => v);
}

function renderDisks(disks) {
  const root = $("disksTable");
  root.innerHTML = "";
  const list = Array.isArray(disks) ? disks : [];
  const ensureAtLeastOne = list.length ? list : [{ name: "disk1", path: "" }];

  for (const disk of ensureAtLeastOne) {
    const row = document.createElement("div");
    row.className = "row";
    const name = rowInput(disk?.name || "", "disk1");
    const path = rowInput(disk?.path || "", "/path/to/output");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(name);
    row.appendChild(path);
    row.appendChild(del);
    root.appendChild(row);
  }
}

function readDisks() {
  const rows = Array.from($("disksTable").querySelectorAll(".row"));
  const disks = [];
  for (const r of rows) {
    const inputs = r.querySelectorAll("input");
    const name = inputs[0]?.value?.trim();
    const path = inputs[1]?.value?.trim();
    if (!name && !path) continue;
    disks.push({ name: name || "", path: path || "" });
  }
  return disks;
}

function renderSpaceHunter(spaceHunterDisks) {
  const root = $("spaceHunterTable");
  root.innerHTML = "";
  const list = Array.isArray(spaceHunterDisks) ? spaceHunterDisks : [];
  for (const disk of list) {
    const row = document.createElement("div");
    row.className = "row sh-row";
    const path = rowInput(disk?.path || "", "/path/to/disk");
    const minFree = rowNumber(disk?.min_free_gb ?? "", 0, 1);
    const action = actionSelect(disk?.action || "delete");
    const moveDest = rowInput(disk?.move_destination || "", "/path/to/destination (move only)");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(path);
    row.appendChild(minFree);
    row.appendChild(action);
    row.appendChild(moveDest);
    row.appendChild(del);
    root.appendChild(row);
  }
  if (!list.length) {
    const row = document.createElement("div");
    row.className = "hint";
    row.textContent = "No space_hunter_disks configured.";
    root.appendChild(row);
  }
}

function readSpaceHunter() {
  const rows = Array.from($("spaceHunterTable").querySelectorAll(".row"));
  const disks = [];
  for (const r of rows) {
    const inputs = r.querySelectorAll("input");
    const selects = r.querySelectorAll("select");
    const path = inputs[0]?.value?.trim();
    const minFreeRaw = inputs[1]?.value;
    const action = selects[0]?.value?.trim() || "delete";
    const moveDestinationRaw = inputs[2]?.value?.trim();
    if (!path) continue;
    const min_free_gb = minFreeRaw === "" ? undefined : Number(minFreeRaw);
    const move_destination = moveDestinationRaw ? moveDestinationRaw : null;
    disks.push({ path, min_free_gb, action, move_destination });
  }
  return disks;
}

function setIfPresent(id, value) {
  const el = $(id);
  if (!el) return;
  if (el.tagName === "SELECT") {
    if (typeof value === "boolean") {
      el.value = value ? "true" : "false";
    } else if (value === null || value === undefined) {
      el.value = "";
    } else {
      el.value = String(value);
    }
  } else {
    el.value = value === null || value === undefined ? "" : String(value);
  }
}

function readNumber(id, fallback) {
  const el = $(id);
  const raw = el?.value;
  if (raw === "" || raw === null || raw === undefined) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function readText(id, fallback) {
  const el = $(id);
  const raw = el?.value;
  const v = raw === null || raw === undefined ? "" : String(raw).trim();
  return v !== "" ? v : fallback;
}

function readBoolSelect(id, fallback) {
  const el = $(id);
  if (!el) return fallback;
  const v = String(el.value).toLowerCase();
  if (v === "true") return true;
  if (v === "false") return false;
  return fallback;
}

function fillConfigForm(cfg, meta) {
  state.config = cfg;
  setIfPresent("cfg-webhook_url", cfg.webhook_url || "");
  setIfPresent("cfg-settings-backup_strategy", cfg.settings?.backup_strategy ?? "round_robin");
  updateBackupStrategyHelp($("cfg-settings-backup_strategy")?.value);
  setIfPresent("cfg-settings-raid_simulation", normalizeRaidSimulation(cfg.settings?.raid_simulation ?? "raid0"));
  updateRaidSimulationHelp($("cfg-settings-raid_simulation")?.value);
  setIfPresent("cfg-settings-scan_interval_seconds", cfg.settings?.scan_interval_seconds ?? 120);
  setIfPresent("cfg-settings-min_file_age_hours", cfg.settings?.min_file_age_hours ?? 1);
  setIfPresent("cfg-settings-extra_safety_space_gb", cfg.settings?.extra_safety_space_gb ?? 0);
  setIfPresent("cfg-settings-console_clear_interval_hours", cfg.settings?.console_clear_interval_hours ?? 6);
  setIfPresent("cfg-settings-space_check_default_min_free_gb", cfg.settings?.space_check_default_min_free_gb ?? 3);
  setIfPresent("cfg-settings-space_hunter_min_file_age_hours", cfg.settings?.space_hunter_min_file_age_hours ?? (cfg.settings?.min_file_age_hours ?? 1));
  setIfPresent("cfg-settings-space_hunter_dry_run", cfg.settings?.space_hunter_dry_run ?? false);
  setIfPresent("cfg-settings-space_hunter_max_actions_per_cycle", cfg.settings?.space_hunter_max_actions_per_cycle ?? 0);
  setIfPresent("cfg-settings-space_hunter_global_fallback", cfg.settings?.space_hunter_global_fallback ?? false);
  setIfPresent("cfg-settings-space_hunter_exclude_folders", joinLines(cfg.settings?.space_hunter_exclude_folders || []));

  const srcFolders = cfg.src_folders || (cfg.src ? [cfg.src] : []);
  renderSrcFolders(srcFolders);
  renderDisks(cfg.disks || []);
  renderSpaceHunter(cfg.space_hunter_disks || []);

  const rr = cfg.reverse_raid && typeof cfg.reverse_raid === "object" ? cfg.reverse_raid : {};
  setIfPresent("cfg-reverse_raid-enabled", Boolean(rr.enabled ?? false));
  setIfPresent("cfg-reverse_raid-destination_path", rr.destination_path ?? (cfg.src || ""));
  setIfPresent("cfg-reverse_raid-min_file_age_hours", rr.min_file_age_hours ?? 12);
  setIfPresent("cfg-reverse_raid-run_interval_minutes", rr.run_interval_minutes ?? 10);
  renderReverseRaidSources(rr.source_paths || []);

  const webdav = cfg.webdav_server && typeof cfg.webdav_server === "object" ? cfg.webdav_server : {};
  setIfPresent("cfg-webdav_server-enabled", Boolean(webdav.enabled ?? false));
  setIfPresent("cfg-webdav_server-port", webdav.port ?? 8080);
  setIfPresent("cfg-webdav_server-username", webdav.username ?? "admin");
  setIfPresent("cfg-webdav_server-password", webdav.password ?? "admin");

  const sftp = cfg.sftp_server && typeof cfg.sftp_server === "object" ? cfg.sftp_server : {};
  setIfPresent("cfg-sftp_server-enabled", Boolean(sftp.enabled ?? false));
  setIfPresent("cfg-sftp_server-port", sftp.port ?? 8081);
  setIfPresent("cfg-sftp_server-username", sftp.username ?? "admin");
  setIfPresent("cfg-sftp_server-password", sftp.password ?? "admin");

  const nfs = cfg.nfs_server && typeof cfg.nfs_server === "object" ? cfg.nfs_server : {};
  setIfPresent("cfg-nfs_server-enabled", Boolean(nfs.enabled ?? false));
  setIfPresent("cfg-nfs_server-permitted", nfs.permitted ?? "*");

  const fuse = cfg.fuse_server && typeof cfg.fuse_server === "object" ? cfg.fuse_server : {};
  setIfPresent("cfg-fuse_server-enabled", Boolean(fuse.enabled ?? false));
  setIfPresent("cfg-fuse_server-mount_point", fuse.mount_point ?? "");

  const fb = cfg.filebrowser && typeof cfg.filebrowser === "object" ? cfg.filebrowser : {};
  setIfPresent("cfg-filebrowser-enabled", Boolean(fb.enabled ?? true));
  setIfPresent("cfg-filebrowser-port", fb.port ?? 8082);
  setIfPresent("cfg-filebrowser-state_dir", fb.state_dir ?? "");
  setIfPresent("cfg-filebrowser-username", fb.username ?? "admin");
  setIfPresent("cfg-filebrowser-password", fb.password ?? "");
  setIfPresent("cfg-filebrowser-image", fb.image ?? "filebrowser/filebrowser");

  const webpanel = cfg.webpanel || {};
  setIfPresent("cfg-webpanel-enabled", Boolean(webpanel.enabled ?? true));
  setIfPresent("cfg-webpanel-host", webpanel.host ?? "127.0.0.1");
  setIfPresent("cfg-webpanel-port", webpanel.port ?? 5000);

  if (meta?.config_path) $("configPathText").textContent = `Config: ${meta.config_path}`;
}

function collectConfigFromForm() {
  const base = state.config && typeof state.config === "object" ? structuredClone(state.config) : {};

  base.webhook_url = readText("cfg-webhook_url", "");
  base.src_folders = readSrcFolders();
  if (base.src_folders && base.src_folders.length) base.src = base.src_folders[0];

  base.disks = readDisks();

  base.settings = base.settings && typeof base.settings === "object" ? base.settings : {};
  base.settings.backup_strategy = readText("cfg-settings-backup_strategy", base.settings.backup_strategy || "round_robin");
  base.settings.raid_simulation = normalizeRaidSimulation(
    readText("cfg-settings-raid_simulation", base.settings.raid_simulation || "raid0"),
  );
  base.settings.scan_interval_seconds = readNumber("cfg-settings-scan_interval_seconds", 120);
  base.settings.min_file_age_hours = readNumber("cfg-settings-min_file_age_hours", 1);
  base.settings.extra_safety_space_gb = readNumber("cfg-settings-extra_safety_space_gb", 0);
  base.settings.console_clear_interval_hours = readNumber("cfg-settings-console_clear_interval_hours", 6);
  base.settings.space_check_default_min_free_gb = readNumber("cfg-settings-space_check_default_min_free_gb", 3);
  base.settings.space_hunter_min_file_age_hours = readNumber(
    "cfg-settings-space_hunter_min_file_age_hours",
    base.settings.min_file_age_hours
  );
  base.settings.space_hunter_dry_run = readBoolSelect("cfg-settings-space_hunter_dry_run", false);
  base.settings.space_hunter_max_actions_per_cycle = readNumber("cfg-settings-space_hunter_max_actions_per_cycle", 0);
  base.settings.space_hunter_global_fallback = readBoolSelect("cfg-settings-space_hunter_global_fallback", false);
  base.settings.space_hunter_exclude_folders = splitLines(readText("cfg-settings-space_hunter_exclude_folders", ""));

  base.space_hunter_disks = readSpaceHunter();

  base.reverse_raid = base.reverse_raid && typeof base.reverse_raid === "object" ? base.reverse_raid : {};
  base.reverse_raid.enabled = readBoolSelect("cfg-reverse_raid-enabled", false);
  base.reverse_raid.destination_path = readText(
    "cfg-reverse_raid-destination_path",
    base.reverse_raid.destination_path || base.src || ""
  );
  base.reverse_raid.min_file_age_hours = readNumber("cfg-reverse_raid-min_file_age_hours", 12);
  base.reverse_raid.run_interval_minutes = readNumber("cfg-reverse_raid-run_interval_minutes", 10);
  base.reverse_raid.source_paths = readReverseRaidSources();

  base.webdav_server = base.webdav_server && typeof base.webdav_server === "object" ? base.webdav_server : {};
  base.webdav_server.enabled = readBoolSelect("cfg-webdav_server-enabled", false);
  base.webdav_server.port = readNumber("cfg-webdav_server-port", 8080);
  base.webdav_server.username = readText("cfg-webdav_server-username", base.webdav_server.username || "admin");
  base.webdav_server.password = readText("cfg-webdav_server-password", base.webdav_server.password || "admin");

  base.sftp_server = base.sftp_server && typeof base.sftp_server === "object" ? base.sftp_server : {};
  base.sftp_server.enabled = readBoolSelect("cfg-sftp_server-enabled", false);
  base.sftp_server.port = readNumber("cfg-sftp_server-port", 8081);
  base.sftp_server.username = readText("cfg-sftp_server-username", base.sftp_server.username || "admin");
  base.sftp_server.password = readText("cfg-sftp_server-password", base.sftp_server.password || "admin");

  base.nfs_server = base.nfs_server && typeof base.nfs_server === "object" ? base.nfs_server : {};
  base.nfs_server.enabled = readBoolSelect("cfg-nfs_server-enabled", false);
  base.nfs_server.permitted = readText("cfg-nfs_server-permitted", base.nfs_server.permitted || "*");

  base.fuse_server = base.fuse_server && typeof base.fuse_server === "object" ? base.fuse_server : {};
  base.fuse_server.enabled = readBoolSelect("cfg-fuse_server-enabled", false);
  base.fuse_server.mount_point = readText("cfg-fuse_server-mount_point", base.fuse_server.mount_point || "");

  base.filebrowser = base.filebrowser && typeof base.filebrowser === "object" ? base.filebrowser : {};
  base.filebrowser.enabled = readBoolSelect("cfg-filebrowser-enabled", true);
  base.filebrowser.port = readNumber("cfg-filebrowser-port", 8082);
  base.filebrowser.state_dir = readText("cfg-filebrowser-state_dir", base.filebrowser.state_dir || "");
  base.filebrowser.username = readText("cfg-filebrowser-username", base.filebrowser.username || "admin");
  base.filebrowser.password = readText("cfg-filebrowser-password", base.filebrowser.password || "");
  base.filebrowser.image = readText("cfg-filebrowser-image", base.filebrowser.image || "filebrowser/filebrowser");

  base.webpanel = base.webpanel && typeof base.webpanel === "object" ? base.webpanel : {};
  base.webpanel.enabled = readBoolSelect("cfg-webpanel-enabled", true);
  base.webpanel.host = readText("cfg-webpanel-host", "127.0.0.1");
  base.webpanel.port = readNumber("cfg-webpanel-port", 5000);

  return base;
}

async function loadConfig() {
  try {
    const data = await fetchJson("/api/config");
    fillConfigForm(data.config, data.meta);
    setSaveStatus("Config loaded.", true);
  } catch (e) {
    setSaveStatus(`Failed to load config: ${String(e.message || e)}`, false);
  }
}

async function saveConfig() {
  try {
    const cfg = collectConfigFromForm();
    const data = await fetchJson("/api/config", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ config: cfg }),
    });
    fillConfigForm(data.config, data.meta);
    const note = data.meta?.note ? ` ${data.meta.note}` : "";
    setSaveStatus(`Saved.${note}`, true);
  } catch (e) {
    setSaveStatus(`Failed to save: ${String(e.message || e)}`, false);
  }
}

function configInit() {
  const backupSel = $("cfg-settings-backup_strategy");
  if (backupSel) {
    backupSel.addEventListener("change", () => updateBackupStrategyHelp(backupSel.value));
    updateBackupStrategyHelp(backupSel.value);
  }
  const raidSel = $("cfg-settings-raid_simulation");
  if (raidSel) {
    raidSel.addEventListener("change", () => updateRaidSimulationHelp(raidSel.value));
    updateRaidSimulationHelp(raidSel.value);
  }

  $("addSrcFolder").addEventListener("click", () => {
    const root = $("srcFoldersList");
    const row = document.createElement("div");
    row.className = "row";
    const input = rowInput("", "/path/to/input");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(input);
    row.appendChild(del);
    root.appendChild(row);
  });

  $("addDisk").addEventListener("click", () => {
    const root = $("disksTable");
    const row = document.createElement("div");
    row.className = "row";
    row.appendChild(rowInput("", "diskX"));
    row.appendChild(rowInput("", "/path/to/output"));
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(del);
    root.appendChild(row);
  });

  $("addSpaceHunter").addEventListener("click", () => {
    const root = $("spaceHunterTable");
    const row = document.createElement("div");
    row.className = "row sh-row";
    row.appendChild(rowInput("", "/path/to/disk"));
    row.appendChild(rowNumber("", 0, 1));
    row.appendChild(actionSelect("delete"));
    row.appendChild(rowInput("", "/path/to/destination (move only)"));
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(del);
    root.appendChild(row);
  });

  $("addReverseRaidSource").addEventListener("click", () => {
    const root = $("reverseRaidSourcesList");
    const row = document.createElement("div");
    row.className = "row";
    const input = rowInput("", "/path/to/source");
    const del = removeButton();
    del.addEventListener("click", () => row.remove());
    row.appendChild(input);
    row.appendChild(del);
    root.appendChild(row);
  });

  $("reloadConfig").addEventListener("click", loadConfig);
  $("saveConfig").addEventListener("click", saveConfig);
}

async function boot() {
  navInit();
  configInit();
  $("refreshNow").addEventListener("click", loadStatsOnce);
  await loadConfig();
  await loadStatsOnce();
  setInterval(loadStatsOnce, 5000);
}

window.addEventListener("DOMContentLoaded", boot);
