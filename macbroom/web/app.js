"use strict";

const state = {
  categories: [],
  data: {},          // key -> {items, total_size, count, scanned}
  itemsById: {},     // id -> item
  selected: new Set(),
  activeTab: null,
  lang: detectLanguage(),
  hasScanned: false,
  showRisky: false,  // 是否展示高风险项
  enabled: new Set(),// 启用的扫描类别 key，关闭的类别不参与扫描
  excluded: { paths: new Set(), ids: new Set() }, // 排除清单：命中的项不扫描/不删除
  scanning: false,   // 是否正在扫描（用于取消）
  abort: null,       // 当前扫描的 AbortController
  sortBy: "size",    // 结果排序：size | name
};

const CSRF_TOKEN = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
const LARGE_WARN_BYTES = 10 * 1024 * 1024 * 1024;  // 单次清理超过 10GB 额外警告
// 默认关闭较慢的两类（遍历整盘 / 全库哈希），用户需要时在设置里开启。
const DEFAULT_DISABLED = ["large_files", "duplicates"];

const I18N = {
  zh: {
    brandTagline: "安全、可视化的 macOS 清理工具",
    summaryLabel: "检测到可清理",
    languageLabel: "语言",
    showRisky: "显示高风险项",
    settingsTitle: "扫描类别",
    settingsHint: "选择要扫描的类别，关闭的类别不会被扫描。较慢的「大文件」「重复文件」默认关闭。",
    rescanCategory: "重扫此类",
    scanStart: "开始扫描",
    scanning: "扫描中…",
    cancelScan: "取消扫描",
    scanCancelled: "已取消扫描",
    rescan: "重新扫描",
    noEnabled: "所有类别都已关闭，点击右上角 ⚙ 开启至少一个类别。",
    exclude: "排除",
    excludeTitle: "永久排除此项，不再扫描",
    excludedTitle: "排除清单",
    excludedHint: "被排除的项不会被扫描或删除。常用于排除误判项。",
    excludedEmpty: "暂无排除项。在扫描结果里点某项的「排除」即可加入。",
    removeExclude: "移除",
    excludedToast: "已加入排除清单（重扫不再出现）",
    unexcludedToast: "已移出排除清单（下次扫描会重新出现）",
    emptyTitle: "点击「开始扫描」",
    emptyBody: "MacBroom 会在本机检测可释放的空间，全部操作仅在本地完成，默认移入废纸篓可还原。",
    selectedPrefix: "已选",
    selectedUnit: "项",
    deleteHint: "删除将移入废纸篓（命令类项会直接执行）",
    deleteSelected: "清理选中项",
    deleting: "清理中…",
    done: "完成",
    loadingCategory: "正在扫描 {title}…",
    itemCount: "{count} 项",
    itemAndSize: "{count} 项 · {size}",
    noItems: "🎉 没有检测到可清理项",
    scanFail: "扫描失败：{err}",
    deleteFail: "清理失败：{err}",
    tagRun: "命令",
    tagManual: "手动",
    tagSudo: "需 sudo",
    tagKeep: "保留",
    riskSafe: "安全",
    riskModerate: "中等",
    riskRisky: "高风险",
    confirmTitle: "确认清理",
    confirmBody: "即将清理 <strong>{count}</strong> 项，预计释放 <strong>{size}</strong>。<br>文件将移入废纸篓（命令项会直接执行），可在废纸篓还原。",
    confirmLargeWarn: "⚠️ 本次清理体积较大（超过 10 GB），请再次确认所选项目无误。",
    confirmRiskyWarn: "⚠️ 所选包含 <strong>{count}</strong> 个高风险项（个人数据 / 不可逆），请谨慎确认。",
    confirmOk: "确认清理",
    confirmCancel: "取消",
    riskyHiddenHint: "{count} 个高风险项已隐藏，勾选右上角「显示高风险项」查看",
    modalTitle: "清理完成 · 成功 {ok} · 待处理 {fail}",
    successBody: "成功清理 <strong>{count}</strong> 项（文件已移入废纸篓，可在废纸篓还原）",
    failIntro: "以下项需要你手动处理（多为权限不足）：",
    copy: "复制",
    copied: "已复制命令，去终端粘贴执行",
    noResults: "没有可处理的项",
    failed: "失败",
    sortBySize: "按大小",
    sortByName: "按名称",
    expandRow: "展开明细",
    collapseRow: "收起明细",
    rowReason: "判定",
  },
  en: {
    brandTagline: "Safe, visual macOS cleanup tool",
    summaryLabel: "Detected Cleanable",
    languageLabel: "Language",
    showRisky: "Show risky items",
    settingsTitle: "Scan Categories",
    settingsHint: "Choose which categories to scan. Disabled ones are skipped. The slower “Large Files” and “Duplicates” are off by default.",
    rescanCategory: "Rescan",
    scanStart: "Start Scan",
    scanning: "Scanning…",
    cancelScan: "Cancel Scan",
    scanCancelled: "Scan cancelled",
    rescan: "Scan Again",
    noEnabled: "All categories are off. Click ⚙ at the top right to enable at least one.",
    exclude: "Exclude",
    excludeTitle: "Permanently exclude this item from scans",
    excludedTitle: "Exclusion List",
    excludedHint: "Excluded items are never scanned or deleted. Useful for false positives.",
    excludedEmpty: "No exclusions yet. Click “Exclude” on any scanned item to add it.",
    removeExclude: "Remove",
    excludedToast: "Added to exclusion list (won't appear on rescan)",
    unexcludedToast: "Removed from exclusion list (will reappear on next scan)",
    emptyTitle: "Click “Start Scan”",
    emptyBody: "MacBroom checks reclaimable space locally. Everything stays on this Mac; file deletions go to Trash by default.",
    selectedPrefix: "Selected",
    selectedUnit: "items",
    deleteHint: "Files move to Trash; command items run directly",
    deleteSelected: "Clean Selected",
    deleting: "Cleaning…",
    done: "Done",
    loadingCategory: "Scanning {title}…",
    itemCount: "{count} items",
    itemAndSize: "{count} items · {size}",
    noItems: "🎉 Nothing cleanable found",
    scanFail: "Scan failed: {err}",
    deleteFail: "Cleanup failed: {err}",
    tagRun: "Command",
    tagManual: "Manual",
    tagSudo: "sudo",
    tagKeep: "Keep",
    riskSafe: "Safe",
    riskModerate: "Moderate",
    riskRisky: "Risky",
    confirmTitle: "Confirm Cleanup",
    confirmBody: "About to clean <strong>{count}</strong> items, freeing roughly <strong>{size}</strong>.<br>Files move to Trash (command items run directly) and can be restored from Trash.",
    confirmLargeWarn: "⚠️ This cleanup is large (over 10 GB). Please double-check your selection.",
    confirmRiskyWarn: "⚠️ Your selection includes <strong>{count}</strong> risky item(s) (personal data / irreversible). Please review carefully.",
    confirmOk: "Confirm Cleanup",
    confirmCancel: "Cancel",
    riskyHiddenHint: "{count} risky item(s) hidden. Tick “Show risky items” at the top right to view.",
    modalTitle: "Cleanup Finished · Success {ok} · Needs Action {fail}",
    successBody: "Cleaned <strong>{count}</strong> items (files were moved to Trash and can be restored)",
    failIntro: "These items need manual handling, usually because of permissions:",
    copy: "Copy",
    copied: "Command copied. Paste it in Terminal when ready.",
    noResults: "No items to process",
    failed: "failed",
    sortBySize: "By size",
    sortByName: "By name",
    expandRow: "Expand details",
    collapseRow: "Collapse details",
    rowReason: "Reason",
  },
};

const $ = (s) => document.querySelector(s);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

function normalizeLang(value) {
  const lang = String(value || "").toLowerCase();
  return lang.startsWith("zh") ? "zh" : "en";
}

function detectLanguage() {
  const saved = localStorage.getItem("macbroom.lang");
  return saved ? normalizeLang(saved) : normalizeLang(navigator.language || "en");
}

function t(key, vars = {}) {
  const dict = I18N[state.lang] || I18N.en;
  return String(dict[key] || I18N.en[key] || key).replace(/\{(\w+)\}/g, (_, k) =>
    vars[k] == null ? "" : String(vars[k]));
}

function langQuery() {
  return "lang=" + encodeURIComponent(state.lang);
}

function humanSize(n) {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (Math.abs(n) >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return (i === 0 ? n : n.toFixed(1)) + " " + u[i];
}

async function init() {
  loadExcluded();
  applyLanguage();
  await loadCategories();
  const selector = $("#language-select");
  selector.value = state.lang;
  selector.addEventListener("change", async () => {
    const wasScanned = state.hasScanned;
    state.lang = normalizeLang(selector.value);
    localStorage.setItem("macbroom.lang", state.lang);
    applyLanguage();
    resetScanState();
    await loadCategories();
    if (wasScanned) await scanAll();
  });
  const riskyToggle = $("#show-risky");
  if (riskyToggle) {
    riskyToggle.checked = state.showRisky;
    riskyToggle.addEventListener("change", () => {
      state.showRisky = riskyToggle.checked;
      // 隐藏高风险项时，顺带取消其已勾选状态，避免误删看不见的项
      if (!state.showRisky) {
        [...state.selected].forEach((id) => {
          const it = state.itemsById[id];
          if (it && it.risk === "risky") state.selected.delete(id);
        });
      }
      state.categories.forEach((c) => { if (state.data[c.key]) renderPanel(c.key); });
      updateActionbar();
    });
  }
  $("#scan-all").addEventListener("click", onScanButton);
  $("#delete-btn").addEventListener("click", deleteSelected);
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal-ok").addEventListener("click", closeModal);
  $("#settings-btn").addEventListener("click", openSettings);
  $("#settings-close").addEventListener("click", closeSettings);
  $("#settings-done").addEventListener("click", closeSettings);
}

function loadEnabledRaw() {
  try {
    const v = localStorage.getItem("macbroom.enabled");
    return v ? JSON.parse(v) : null;
  } catch (e) { return null; }
}

function saveEnabled() {
  localStorage.setItem("macbroom.enabled", JSON.stringify([...state.enabled]));
}

function resolveEnabled() {
  const allKeys = state.categories.map((c) => c.key);
  const raw = loadEnabledRaw();
  if (Array.isArray(raw)) {
    state.enabled = new Set(raw.filter((k) => allKeys.includes(k)));
  } else {
    state.enabled = new Set(allKeys.filter((k) => !DEFAULT_DISABLED.includes(k)));
  }
}

function enabledCategories() {
  return state.categories.filter((c) => state.enabled.has(c.key));
}

function loadExcluded() {
  try {
    const v = JSON.parse(localStorage.getItem("macbroom.excluded") || "{}");
    state.excluded = {
      paths: new Set(Array.isArray(v.paths) ? v.paths : []),
      ids: new Set(Array.isArray(v.ids) ? v.ids : []),
    };
  } catch (e) {
    state.excluded = { paths: new Set(), ids: new Set() };
  }
}

function saveExcluded() {
  localStorage.setItem("macbroom.excluded", JSON.stringify({
    paths: [...state.excluded.paths],
    ids: [...state.excluded.ids],
  }));
}

// 命中规则：路径精确匹配，或是某个被排除目录的子路径；命令类项按 id 匹配。
function isExcluded(it) {
  if (it.path) {
    if (state.excluded.paths.has(it.path)) return true;
    for (const ex of state.excluded.paths) {
      if (it.path === ex || it.path.startsWith(ex + "/")) return true;
    }
    return false;
  }
  return state.excluded.ids.has(it.id);
}

function excludeItem(it) {
  if (it.path) state.excluded.paths.add(it.path);
  else state.excluded.ids.add(it.id);
  saveExcluded();
  // 即时从当前结果中移除，避免还能被勾选删除。
  state.selected.delete(it.id);
  delete state.itemsById[it.id];
  const d = state.data[it.category];
  if (d) {
    d.items = d.items.filter((x) => x.id !== it.id);
    d.total_size = sumSize(d.items);
    d.count = d.items.length;
    renderPanel(it.category);
    const b = $("#badge-" + it.category);
    if (b) b.textContent = d.total_size ? humanSize(d.total_size) : d.count;
  }
  updateActionbar();
  updateGrandTotal();
  toast(t("excludedToast"));
}

function removeExclusion(kind, value) {
  if (kind === "path") state.excluded.paths.delete(value);
  else state.excluded.ids.delete(value);
  saveExcluded();
  renderExcludedList();
  toast(t("unexcludedToast"));
}

function isVisible(it) {
  return state.showRisky || it.risk !== "risky";
}

// 是否允许勾选删除（如重复组的「保留项」服务端标 deletable=false）。
function isDeletable(it) {
  return it.deletable !== false;
}

function visibleItems(list) {
  return list.filter(isVisible);
}

function applyLanguage() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  $("#scan-all").innerHTML = `<span class="dot"></span> ${state.hasScanned ? t("rescan") : t("scanStart")}`;
  $("#delete-btn").textContent = t("deleteSelected");
}

async function loadCategories() {
  const res = await fetch("/api/categories?" + langQuery());
  if (!res.ok) {
    toast(t("scanFail", { err: "HTTP " + res.status }));
    return;
  }
  state.categories = await res.json();
  resolveEnabled();
  renderTabs();
}

function resetScanState() {
  state.data = {};
  state.itemsById = {};
  state.selected = new Set();
  state.activeTab = null;
  state.hasScanned = false;
  $("#panels").innerHTML = "";
  $("#empty-state").style.display = "";
  $("#grand-total").textContent = "—";
  updateActionbar();
}

function renderTabs() {
  const tabs = $("#tabs");
  tabs.innerHTML = "";
  const cats = enabledCategories();
  cats.forEach((c) => {
    const t = el("div", "tab" + (c.danger ? " danger" : ""));
    t.dataset.key = c.key;
    t.innerHTML = `<span>${c.icon}</span><span>${c.title}</span><span class="badge" id="badge-${c.key}">—</span>`;
    t.addEventListener("click", () => activateTab(c.key));
    tabs.appendChild(t);
  });
  // 同步徽标（重渲染后丢失），并保证有一个激活的 Tab。
  cats.forEach((c) => {
    const d = state.data[c.key];
    const badge = $("#badge-" + c.key);
    if (badge && d) badge.textContent = d.total_size ? humanSize(d.total_size) : d.count;
  });
  if (state.activeTab && state.enabled.has(state.activeTab)) activateTab(state.activeTab);
  else if (cats.length) activateTab(cats[0].key);
}

function activateTab(key) {
  state.activeTab = key;
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.key === key));
  document.querySelectorAll(".panel").forEach((p) =>
    p.classList.toggle("active", p.dataset.key === key));
}

function onScanButton() {
  if (state.scanning) cancelScan();
  else scanAll();
}

function cancelScan() {
  state.scanning = false;
  if (state.abort) { try { state.abort.abort(); } catch (e) { /* noop */ } }
  toast(t("scanCancelled"));
}

function setScanBtnScanning() {
  const btn = $("#scan-all");
  btn.disabled = false;
  btn.classList.add("cancel");
  btn.innerHTML = `<span class="dot"></span> ${t("cancelScan")}`;
}

function setScanBtnIdle() {
  const btn = $("#scan-all");
  btn.disabled = false;
  btn.classList.remove("cancel");
  btn.innerHTML = `<span class="dot"></span> ${state.hasScanned ? t("rescan") : t("scanStart")}`;
}

function finishScan() {
  state.scanning = false;
  state.abort = null;
  setScanBtnIdle();
  updateGrandTotal();
}

async function scanAll() {
  const cats = enabledCategories();
  $("#empty-state").style.display = "none";
  // 记住上一轮用户手动勾选的项，重扫后若仍存在则保留（ID 按路径稳定）。
  const prevSelected = new Set(state.selected);
  state.data = {};
  state.itemsById = {};
  state.selected = new Set();
  state._prevSelected = prevSelected;
  state.hasScanned = true;
  state.scanning = true;
  state.abort = new AbortController();
  setScanBtnScanning();

  // 为每个启用的分类建立面板占位
  const panels = $("#panels");
  panels.innerHTML = "";
  if (!cats.length) {
    panels.innerHTML = `<div class="panel active"><div class="panel-empty">${t("noEnabled")}</div></div>`;
    finishScan();
    return;
  }
  cats.forEach((c) => {
    const p = el("div", "panel");
    p.dataset.key = c.key;
    p.innerHTML = `<div class="loading"><div class="spinner"></div>${t("loadingCategory", {title: c.title})}</div>`;
    panels.appendChild(p);
  });
  if (!state.activeTab || !state.enabled.has(state.activeTab)) activateTab(cats[0].key);

  for (const c of cats) {
    if (!state.scanning) break;  // 用户中途取消
    await scanCategory(c.key);
  }
  finishScan();
}

async function scanCategory(key) {
  try {
    const opts = state.abort ? { signal: state.abort.signal } : {};
    const res = await fetch("/api/scan?key=" + encodeURIComponent(key) + "&" + langQuery(), opts);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    // 过滤用户排除清单中的项：不计入结果、不可被勾选删除。
    if (Array.isArray(data.items)) {
      data.items = data.items.filter((it) => !isExcluded(it));
      data.total_size = sumSize(data.items);
      data.count = data.items.length;
    }
    state.data[key] = data;
    const prev = state._prevSelected;
    data.items.forEach((it) => {
      state.itemsById[it.id] = it;
      // 默认勾选推荐的安全项；或保留用户上一轮已勾选且仍可见的项。
      if (it.recommend || (prev && prev.has(it.id) && isVisible(it))) {
        state.selected.add(it.id);
      }
    });
    renderPanel(key);
    const badge = $("#badge-" + key);
    if (badge) badge.textContent = data.total_size ? humanSize(data.total_size) : data.count;
  } catch (e) {
    if (e && e.name === "AbortError") return;  // 用户主动取消，不算失败
    const p = document.querySelector(`.panel[data-key="${key}"]`);
    if (p) p.innerHTML = `<div class="panel-empty">${esc(t("scanFail", {err: String(e)}))}</div>`;
  }
  updateActionbar();
}

function renderPanel(key) {
  const cat = state.categories.find((c) => c.key === key);
  const data = state.data[key];
  const p = document.querySelector(`.panel[data-key="${key}"]`);
  if (!p) return;
  p.innerHTML = "";

  const shown = visibleItems(data.items);
  const hiddenCount = data.items.length - shown.length;
  const shownSize = sumSize(shown);

  const head = el("div", "panel-head");
  head.innerHTML = `<h2>${cat.icon} ${cat.title}</h2>
    <span class="desc">${cat.description}</span>
    <span class="pill">${t("itemAndSize", {count: shown.length, size: humanSize(shownSize)})}</span>
    <span class="sort-bar">
      <button type="button" class="sort-btn ${state.sortBy === "size" ? "active" : ""}" data-sort="size">${esc(t("sortBySize"))}</button>
      <button type="button" class="sort-btn ${state.sortBy === "name" ? "active" : ""}" data-sort="name">${esc(t("sortByName"))}</button>
    </span>
    <button class="panel-rescan" title="${esc(t("rescanCategory"))}">↻ ${esc(t("rescanCategory"))}</button>`;
  head.querySelector(".panel-rescan").addEventListener("click", () => rescanCategory(key));
  head.querySelectorAll(".sort-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.sortBy = btn.dataset.sort;
      renderPanel(key);
    });
  });
  p.appendChild(head);

  if (hiddenCount > 0) {
    p.appendChild(el("div", "risky-hint", t("riskyHiddenHint", {count: hiddenCount})));
  }

  if (!shown.length) {
    p.appendChild(el("div", "panel-empty", t("noItems")));
    return;
  }

  // 分组
  const groups = {};
  shown.forEach((it) => {
    (groups[it.group] = groups[it.group] || []).push(it);
  });
  const groupNames = Object.keys(groups).sort(
    (a, b) => sumSize(groups[b]) - sumSize(groups[a]));

  groupNames.forEach((gname) => {
    const list = sortItems(groups[gname]);
    const g = el("div", "group");
    const gsize = sumSize(list);
    const ghead = el("div", "group-head");
    ghead.innerHTML = `<div class="cb" data-group="${esc(gname)}"></div>
      <span class="gname">${esc(gname)}</span>
      <span class="gsize">${t("itemAndSize", {count: list.length, size: humanSize(gsize)})}</span>
      <span class="chev">▾</span>`;
    g.appendChild(ghead);

    const rows = el("div", "rows");
    list.forEach((it) => rows.appendChild(renderRow(it)));
    g.appendChild(rows);

    // 折叠
    ghead.addEventListener("click", (e) => {
      if (e.target.classList.contains("cb")) return;
      g.classList.toggle("collapsed");
    });
    // 组全选
    ghead.querySelector(".cb").addEventListener("click", (e) => {
      e.stopPropagation();
      const sel = list.filter(isDeletable);
      const allSel = sel.length && sel.every((it) => state.selected.has(it.id));
      sel.forEach((it) => allSel ? state.selected.delete(it.id) : state.selected.add(it.id));
      renderPanel(key);
      updateActionbar();
    });

    p.appendChild(g);
    refreshGroupCb(ghead, list);
  });
}

function sortItems(list) {
  const copy = [...list];
  if (state.sortBy === "name") {
    copy.sort((a, b) => String(a.name).localeCompare(String(b.name)));
  } else {
    copy.sort((a, b) => (b.size || 0) - (a.size || 0));
  }
  return copy;
}

function renderRow(it) {
  const row = el("div", "row");
  const tag = it.action === "run" ? `<span class="tag run">${t("tagRun")}</span>`
    : it.action === "manual" ? `<span class="tag manual">${t("tagManual")}</span>` : "";
  const sudo = it.needs_sudo ? `<span class="tag sudo">${t("tagSudo")}</span>` : "";
  const riskKey = it.risk === "safe" ? "riskSafe" : it.risk === "risky" ? "riskRisky" : "riskModerate";
  const risk = `<span class="tag risk-${it.risk || "moderate"}">${t(riskKey)}</span>`;
  const reasonLine = it.reason
    ? `<div class="rreason"><span class="rlabel">${esc(t("rowReason"))}:</span> ${esc(it.reason)}</div>` : "";
  const pathLine = it.path ? `<div class="rpath">${esc(it.path.replace(/^.*\/Users\/[^/]+/, "~"))}</div>` : "";
  const hasChildren = Array.isArray(it.children) && it.children.length > 0;
  const expandBtn = hasChildren
    ? `<button type="button" class="row-expand" title="${esc(t("expandRow"))}">▾</button>` : "";
  const locked = !isDeletable(it);
  const keepTag = locked ? `<span class="tag keep">${t("tagKeep")}</span>` : "";
  const cbClass = locked ? "cb disabled" : `cb ${state.selected.has(it.id) ? "checked" : ""}`;
  row.innerHTML = `<div class="${cbClass}"></div>
    <div class="meta">
      <div class="rname">${esc(it.name)}${risk}${keepTag}${tag}${sudo}</div>
      ${reasonLine}
      <div class="rnote">${esc(it.note || "")}</div>
      ${pathLine}
    </div>
    <div class="rsize">${it.size ? humanSize(it.size) : "—"}</div>
    ${expandBtn}
    <button class="row-exclude" title="${esc(t("excludeTitle"))}">${esc(t("exclude"))}</button>`;
  if (hasChildren) {
    const sub = el("div", "row-children hidden");
    it.children.forEach((ch) => {
      const cr = el("div", "row-child");
      cr.innerHTML = `<span class="cname">${esc(ch.name)}</span>
        <span class="cpath">${esc(ch.path || "")}</span>
        <span class="csize">${ch.size ? humanSize(ch.size) : "—"}</span>`;
      sub.appendChild(cr);
    });
    row.appendChild(sub);
    const exp = row.querySelector(".row-expand");
    exp.addEventListener("click", (e) => {
      e.stopPropagation();
      const hidden = sub.classList.toggle("hidden");
      exp.textContent = hidden ? "▾" : "▴";
      exp.title = hidden ? t("expandRow") : t("collapseRow");
    });
  }
  if (!locked) {
    row.querySelector(".cb").addEventListener("click", () => {
      if (state.selected.has(it.id)) state.selected.delete(it.id);
      else state.selected.add(it.id);
      renderPanel(state.activeTab);
      updateActionbar();
    });
  }
  row.querySelector(".row-exclude").addEventListener("click", (e) => {
    e.stopPropagation();
    excludeItem(it);
  });
  return row;
}

function refreshGroupCb(ghead, list) {
  const cb = ghead.querySelector(".cb");
  const sel = list.filter(isDeletable);
  const allSel = sel.length && sel.every((it) => state.selected.has(it.id));
  cb.classList.toggle("checked", allSel);
}

function sumSize(list) { return list.reduce((s, it) => s + (it.size || 0), 0); }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function updateActionbar() {
  const bar = $("#actionbar");
  let size = 0;
  state.selected.forEach((id) => { const it = state.itemsById[id]; if (it) size += it.size || 0; });
  $("#sel-count").textContent = state.selected.size;
  $("#sel-size").textContent = humanSize(size);
  $("#delete-btn").disabled = state.selected.size === 0;
  bar.classList.toggle("show", state.selected.size > 0);
}

function updateGrandTotal() {
  let total = 0;
  Object.values(state.data).forEach((d) => total += d.total_size || 0);
  $("#grand-total").textContent = humanSize(total);
}

async function deleteSelected() {
  const ids = [...state.selected];
  if (!ids.length) return;

  // 先走 dry-run 式确认：列出总数 / 总体积 / 高风险与大体积警告。
  let totalSize = 0, riskyCount = 0;
  ids.forEach((id) => {
    const it = state.itemsById[id];
    if (!it) return;
    totalSize += it.size || 0;
    if (it.risk === "risky") riskyCount++;
  });
  const ok = await showConfirm({ count: ids.length, size: totalSize, risky: riskyCount, ids });
  if (!ok) return;

  const btn = $("#delete-btn");
  btn.disabled = true; btn.textContent = t("deleting");

  let out = null;
  try {
    const res = await fetch("/api/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-MacBroom-Token": CSRF_TOKEN },
      body: JSON.stringify({ ids }),
    });
    out = await res.json().catch(() => null);
    if (!res.ok || !out || !Array.isArray(out.results)) {
      const err = (out && out.error) || ("HTTP " + res.status);
      throw new Error(err);
    }
  } catch (e) {
    btn.textContent = t("deleteSelected");
    btn.disabled = state.selected.size === 0;
    toast(t("deleteFail", {err: String((e && e.message) || e)}));
    return;
  }
  btn.textContent = t("deleteSelected");

  // 处理结果：成功项移除
  out.results.forEach((r) => {
    if (r.ok) {
      state.selected.delete(r.id);
      const it = state.itemsById[r.id];
      if (it) {
        const d = state.data[it.category];
        if (d) { d.items = d.items.filter((x) => x.id !== r.id); d.total_size -= it.size || 0; d.count = d.items.length; }
        delete state.itemsById[r.id];
      }
    }
  });
  state.categories.forEach((c) => { if (state.data[c.key]) renderPanel(c.key); const b = $("#badge-" + c.key); if (b && state.data[c.key]) b.textContent = state.data[c.key].total_size ? humanSize(state.data[c.key].total_size) : state.data[c.key].count; });
  updateActionbar();
  updateGrandTotal();
  showResults(out.results);
}

function showResults(results) {
  const ok = results.filter((r) => r.ok);
  const fail = results.filter((r) => !r.ok);
  const body = $("#modal-body");
  body.innerHTML = "";

  $("#modal-title").textContent = t("modalTitle", {ok: ok.length, fail: fail.length});

  if (ok.length) {
    body.appendChild(el("div", "", `<div class="res-row"><span class="ic ok">✓</span><div class="body">${t("successBody", {count: ok.length})}</div></div>`));
  }
  if (fail.length) {
    body.appendChild(el("div", "", `<p style="margin:14px 0 8px;color:var(--text-dim);font-size:13px;">${t("failIntro")}</p>`));
    fail.forEach((r) => {
      const cmd = r.command
        ? `<div class="cmd"><code>${esc(r.command)}</code><button class="copy-btn" data-cmd="${esc(r.command)}">${t("copy")}</button></div>`
        : "";
      const hint = r.hint
        ? `<div class="rnote" style="margin-top:4px;">${esc(r.hint)}</div>` : "";
      const node = el("div", "res-row");
      node.innerHTML = `<span class="ic fail">!</span><div class="body">
        <div>${esc(r.name || r.id)} <span style="color:var(--text-faint)">— ${esc(r.error || t("failed"))}</span></div>
        ${cmd}${hint}</div>`;
      body.appendChild(node);
    });
    body.querySelectorAll(".copy-btn").forEach((b) =>
      b.addEventListener("click", () => {
        navigator.clipboard.writeText(b.dataset.cmd);
        toast(t("copied"));
      }));
  }
  if (!results.length) body.innerHTML = `<p>${t("noResults")}</p>`;
  $("#modal-mask").classList.add("show");
}

function closeModal() { $("#modal-mask").classList.remove("show"); }

function openSettings() {
  const list = $("#settings-list");
  list.innerHTML = "";
  state.categories.forEach((c) => {
    const row = el("div", "set-row");
    row.innerHTML = `<span class="set-name">${c.icon} ${esc(c.title)}</span>
      <label class="switch"><input type="checkbox" ${state.enabled.has(c.key) ? "checked" : ""}><span class="slider"></span></label>`;
    row.querySelector("input").addEventListener("change", (e) => toggleCategory(c.key, e.target.checked));
    list.appendChild(row);
  });
  renderExcludedList();
  $("#settings-mask").classList.add("show");
}

function renderExcludedList() {
  const box = $("#excluded-list");
  box.innerHTML = "";
  const entries = [
    ...[...state.excluded.paths].map((v) => ({ kind: "path", value: v, label: v.replace(/^.*\/Users\/[^/]+/, "~") })),
    ...[...state.excluded.ids].map((v) => ({ kind: "id", value: v, label: v })),
  ];
  if (!entries.length) {
    box.appendChild(el("div", "excluded-empty", t("excludedEmpty")));
    return;
  }
  entries.forEach((en) => {
    const row = el("div", "excluded-row");
    row.innerHTML = `<span class="excluded-path" title="${esc(en.value)}">${esc(en.label)}</span>
      <button class="excluded-remove">${esc(t("removeExclude"))}</button>`;
    row.querySelector(".excluded-remove").addEventListener("click", () => removeExclusion(en.kind, en.value));
    box.appendChild(row);
  });
}

function closeSettings() { $("#settings-mask").classList.remove("show"); }

function ensurePanel(key) {
  let p = document.querySelector(`.panel[data-key="${key}"]`);
  if (!p) {
    p = el("div", "panel");
    p.dataset.key = key;
    $("#panels").appendChild(p);
  }
  return p;
}

function toggleCategory(key, on) {
  if (on) state.enabled.add(key);
  else state.enabled.delete(key);
  saveEnabled();

  if (on) {
    renderTabs();
    if (state.hasScanned) {
      ensurePanel(key);
      rescanCategory(key);
    }
  } else {
    // 关闭：清掉该类的数据、勾选与面板，避免计入总量与误删。
    const d = state.data[key];
    if (d) d.items.forEach((it) => { state.selected.delete(it.id); delete state.itemsById[it.id]; });
    delete state.data[key];
    const p = document.querySelector(`.panel[data-key="${key}"]`);
    if (p) p.remove();
    renderTabs();
    updateActionbar();
    updateGrandTotal();
  }
}

async function rescanCategory(key) {
  const p = ensurePanel(key);
  const cat = state.categories.find((c) => c.key === key);
  p.innerHTML = `<div class="loading"><div class="spinner"></div>${t("loadingCategory", {title: cat ? cat.title : key})}</div>`;
  // 保留用户上一轮在该类的勾选（仍存在的项会被重新勾上）。
  state._prevSelected = new Set(state.selected);
  const old = state.data[key];
  if (old) old.items.forEach((it) => { state.selected.delete(it.id); delete state.itemsById[it.id]; });
  state.scanning = true;
  state.abort = new AbortController();
  setScanBtnScanning();
  await scanCategory(key);
  finishScan();
}

function showConfirm({ count, size, risky, ids = [] }) {
  return new Promise((resolve) => {
    $("#modal-title").textContent = t("confirmTitle");
    const body = $("#modal-body");
    body.innerHTML = "";
    body.appendChild(el("div", "confirm-body", t("confirmBody", {count, size: humanSize(size)})));
    if (risky > 0) {
      body.appendChild(el("div", "confirm-warn", t("confirmRiskyWarn", {count: risky})));
    }
    if (size >= LARGE_WARN_BYTES) {
      body.appendChild(el("div", "confirm-warn", t("confirmLargeWarn")));
    }
    if (ids.length) {
      const list = el("div", "confirm-list");
      ids.forEach((id) => {
        const it = state.itemsById[id];
        if (!it) return;
        const line = el("div", "confirm-item");
        const path = it.path ? it.path.replace(/^.*\/Users\/[^/]+/, "~") : "";
        line.innerHTML = `<strong>${esc(it.name)}</strong> · ${it.size ? humanSize(it.size) : "—"}
          ${it.reason ? `<div class="ci-reason">${esc(it.reason)}</div>` : ""}
          ${path ? `<div class="ci-path">${esc(path)}</div>` : ""}`;
        list.appendChild(line);
      });
      body.appendChild(list);
    }

    const foot = $("#modal-foot");
    foot.innerHTML = "";
    const cancel = el("button", "btn", t("confirmCancel"));
    const okBtn = el("button", "btn btn-danger", t("confirmOk"));
    foot.appendChild(cancel);
    foot.appendChild(okBtn);

    const closeBtn = $("#modal-close");
    const onClose = () => cleanup(false);
    const cleanup = (val) => {
      $("#modal-mask").classList.remove("show");
      closeBtn.removeEventListener("click", onClose);
      // 还原默认底栏（结果弹窗只有一个「完成」按钮）
      foot.innerHTML = `<button class="btn" id="modal-ok">${t("done")}</button>`;
      $("#modal-ok").addEventListener("click", closeModal);
      resolve(val);
    };
    cancel.addEventListener("click", () => cleanup(false));
    okBtn.addEventListener("click", () => cleanup(true));
    // 点右上角 ✕ 关闭确认弹窗，视为「取消」，避免 promise 挂起。
    closeBtn.addEventListener("click", onClose);
    $("#modal-mask").classList.add("show");
  });
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

init();
