import { words } from "./copy.js";
import { bangla, banglaCards, banglaReasons } from "./copy-bn.js";
import { initActivities } from "./activities.js";
import { notificationPermission, requestReminderPermission, showReminderNotification } from "./notifications.js";

const mount = document.getElementById("steadyday");
if (!mount) throw new Error("SteadyDay host is missing.");
const state = { screen: "", data: null, config: null, metric: "sleep", checkinDay: null, habitDay: null,
  notice: "", insightRange: "14", insights: null, dialog: null };
function storedPreference(key, choices, fallback) {
  try {
    const value = localStorage.getItem("steadyday." + key);
    if (choices.includes(value)) return value;
  } catch {}
  return fallback;
}
function savePreference(key, value) {
  try { localStorage.setItem("steadyday." + key, value); } catch {}
}
let language = storedPreference("language", ["en", "bn"], "en");
const themes = ["system", "light", "dark"];
let theme = storedPreference("theme", themes, "system");
const deviceTheme = matchMedia("(prefers-color-scheme: dark)");
function applyTheme() {
  document.documentElement.dataset.theme = theme === "system" ? (deviceTheme.matches ? "dark" : "light") : theme;
}
applyTheme();
deviceTheme.addEventListener("change", applyTheme);
const t = (key) => (language === "bn" ? bangla[key] : words[key]) ?? words[key] ?? key;
const locale = () => language === "bn" ? "bn-BD" : "en-GB";
const e = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const n = (value) => new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(value);
const dt = (day, opts = { weekday: "short", day: "numeric", month: "short" }) => new Intl.DateTimeFormat(locale(), { ...opts, timeZone: "UTC" }).format(new Date(String(day).slice(0, 10) + "T12:00:00Z"));
const tri = (value, limit) => Math.max(0, Math.min(100, Number(value) / limit * 100));
const motionText = (v) => n(v) + " " + t("minuteUnit");
const hoursText = (v) => n(v / 60) + " " + t("hourUnit");
const failKey = (x) => ({ VALIDATION_ERROR: "invalid", DEMO_CODE: "badCode", SESSION_REQUIRED: "missing", DEMO_CAPACITY: "capacity", CONSENT_REQUIRED: "consentRequired", ITEM_LIMIT: "limitReached" }[x] ?? "failed");
const name = "SteadyDay";
const glyph = {
  check: '<path d="m5 12 4 4 10-10"/>',
  wave: '<path d="M2 12h5l3-6 4 12 3-6h5"/>',
  moon: '<path d="M20 15.5A9 9 0 0 1 8.5 4 8.8 8.8 0 1 0 20 15.5Z"/>',
  spark: '<path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3Z"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  shield: '<path d="M12 22s7-3 7-10V5l-7-3-7 3v7c0 7 7 10 7 10Z"/><path d="m9 12 2 2 4-4"/>',
  bars: '<path d="M5 19V9m7 10V5m7 14v-7"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 8-3 9-3 9h18s-3-1-3-9m-8 12a2 2 0 0 0 4 0"/>',
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM9 21v-7h6v7"/>',
  clipboard: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 10h6m-6 5h6"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
  drop: '<path d="M12 3c2 3 6 7 6 11a6 6 0 0 1-12 0c0-4 4-8 6-11Z"/>',
  leaf: '<path d="M20 4C9 4 5 8 5 14a5 5 0 0 0 5 5c6 0 10-4 10-15ZM4 20 15 9"/>',
  play: '<path d="m8 4 12 8-12 8z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M4 20h4L20 8l-4-4L4 16zM13 7l4 4"/>',
  trash: '<path d="M3 6h18M6 6l1 15h10l1-15M9 6V3h6v3M10 10v7m4-7v7"/>',
};
const icon = (key, size = 20) => '<svg aria-hidden="true" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + glyph[key] + '</svg>';
const btn = (key, href, cls = "btn primary") => '<a class="' + cls + '" href="' + href + '" data-route>' + e(t(key)) + '</a>';
const literalLink = (source) => {
  if (source?.url === "/privacy#recommendations") return '<a href="/privacy#recommendations" data-route>' + e(t("designSource")) + '</a>';
  try {
    const url = new URL(source.url);
    if (url.protocol === "https:" && ["www.who.int","www.cdc.gov","www.nhs.uk"].includes(url.hostname)) {
      return '<a href="' + e(url.href) + '" target="_blank" rel="noopener noreferrer">' + e(source.label) + '</a>';
    }
  } catch {}
  return "";
};

async function api(resource, method = "GET", body) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 7000);
  try {
    const response = await fetch("/api/demo/" + resource, {
      method, credentials: "same-origin", cache: "no-store", signal: ctl.signal,
      ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || data === null) {
      const error = new Error("API request failed.");
      error.status = response.status;
      error.code = data?.error?.code ?? "BACKEND_UNAVAILABLE";
      throw error;
    }
    return data;
  } finally { clearTimeout(timer); }
}

function shell(body, mode) {
  document.documentElement.lang = language;
  document.title = name + " | " + t(mode === "privacy" ? "privacy" : mode === "dashboard" ? "dashboard" : "tag");
  const navLinks = mode === "dashboard" ? '<a class="top-link" href="#controls">' + e(t("navData")) + '</a>' : '<a class="top-link" href="/privacy" data-route>' + e(t("privacy")) + '</a>';
  mount.innerHTML = '<a class="skip" href="#main">' + e(t("skip")) + '</a>' +
    '<header class="mast"><div class="shell nav"><a class="brand" href="/" data-route aria-label="' + e(t("home") + " · " + name) + '"><img src="/steadyday/mark.svg" alt="" width="37" height="37"><span>' + name + '</span></a>' +
    '<div class="nav-end">' + navLinks + '<label class="language-control"><span class="sr">' + e(t("language")) + '</span>' + languageSelect(true) + '</label>' +
    (mode === "home" ? btn("demo", "/demo", "btn nav-cta") : '') + '</div></div></header>' +
    '<main id="main" tabindex="-1">' + body + '</main>' +
    '<footer class="foot"><div class="shell foot-inner"><span>' + e(t("footer")) + '</span><a href="/privacy" data-route>' + e(t("privacy")) + '</a></div></footer>';
}

const screens = {
  "/demo": ["dashboardNav", "home", null, "home"],
  "/check-in": ["dailyNav", "clipboard", "dailyDescription", "navCheckin"],
  "/insights": ["insightsNav", "bars", "insightsDescription", "insightsNav"],
  "/goals-habits": ["goalsHabitsNav", "target", "goalsHabitsDescription", "navGoals"],
  "/coach": ["coachNav", "spark", "coachDescription", "coachShort"],
  "/settings": ["profileNav", "person", "profileDescription", "settingsShort"],
};
const currentPath = () => location.pathname.replace(/\/$/, "") || "/";

function languageSelect(compact = false) {
  return '<select id="language" name="language"><option value="en" lang="en"' +
    (language === "en" ? " selected" : "") + '>' + (compact ? "EN" : "English") + '</option>' +
    '<option value="bn" lang="bn"' + (language === "bn" ? " selected" : "") + '>বাংলা</option></select>';
}

function personName(profile) {
  return profile.name && !["Arif", "Samir"].includes(profile.name) ? profile.name : t(profile.persona);
}

function appShell(body) {
  const data = state.data;
  const path = currentPath();
  const [title, symbol, description] = screens[path];
  const displayName = personName(data.profile);
  const navLinks = (compact = false) => Object.entries(screens).map(([href, [label, glyphName, , shortLabel]]) =>
    '<a class="app-nav-link" href="' + href + '" data-route aria-label="' + e(t(label)) + '"' +
    (href === path ? ' aria-current="page"' : "") + '>' + icon(glyphName, 20) + '<span>' + e(t(compact ? shortLabel : label)) + '</span></a>').join("");
  const avatar = '<span class="app-avatar" aria-hidden="true">' + e(Array.from(displayName)[0]) + '</span>';
  const brand = '<a class="brand app-brand" href="/demo" data-route aria-label="SteadyDay"><img src="/steadyday/mark.svg" alt="" width="38" height="38"><span>SteadyDay</span></a>';
  document.documentElement.lang = language;
  document.title = name + " | " + t(title);
  mount.innerHTML = '<a class="skip" href="#main">' + e(t("skip")) + '</a><div class="app-shell">' +
    '<aside class="app-sidebar">' + brand + '<nav class="app-nav" aria-label="' + e(t("mainNavigation")) + '">' + navLinks() +
    '</nav><div class="app-sidebar-footer"><a href="/privacy" data-route>' + icon("shield", 18) + e(t("privacy")) + '</a><span>' + e(t("fake")) + '</span></div></aside>' +
    '<main class="app-main" id="main" tabindex="-1"><header class="app-topbar">' +
    '<div class="app-top-title">' + icon(symbol, 18) + '<div><span>' + e(t(title)) + '</span><br><small>' + e(t("fake")) + '</small></div></div>' +
    '<div class="app-top-actions"><a class="app-header-icon" href="/settings#reminders" data-route aria-label="' + e(t("reminder")) + '">' + icon("bell", 20) + '</a>' +
    '<a class="app-header-icon" href="/settings" data-route aria-label="' + e(t("profileNav")) + '">' + avatar + '</a></div></header>' +
    '<div class="shell app-view">' + (description ? '<header class="app-page-head"><h1>' + e(t(title)) + '</h1><p>' + e(t(description)) + '</p></header>' : "") +
    '<div id="status" class="notice" role="status" tabindex="-1"' + (state.notice ? '' : ' hidden') + '>' + (state.notice ? e(t(state.notice)) : "") + '</div>' +
    '<aside id="reminder-due" class="notice due" role="status" hidden>' + icon("bell", 19) + e(t("reminderDue")) + '</aside>' +
    body + '</div></main><nav class="app-bottom-nav" aria-label="' + e(t("mainNavigation")) + '">' + navLinks(true) + '</nav></div>';
  refreshReminder();
}

function heroArt() {
  return '<div class="hero-art" aria-hidden="true"><div class="hero-note"><div class="hero-note-icon">' +
    icon("spark", 24) + '</div><div><strong>' + e(t("heroCard")) + '</strong><span>' + e(t("heroCardSub")) + '</span></div></div></div>';
}
function landing() {
  shell('<section class="shell hero"><div class="hero-copy"><p class="eyebrow"><span></span>' + e(t("tag")) + '</p><h1>' + e(t("heroA")) + '<br><em>' + e(t("heroB")) + '</em></h1><p class="lede">' + e(t("intro")) + '</p>' +
    '<div class="actions">' + btn("start","/demo") + '<a class="plain" href="#how">' + e(t("how")) + ' ' + icon("arrow",16) + '</a></div><p class="muted hero-privacy">' + icon("shield",17) + e(t("demoOnly")) + '</p></div>' + heroArt() + '</section>' +
    '<section id="how" class="how"><div class="shell"><h2>' + e(t("featureTitle")) + '</h2><div class="feature-grid">' +
    [["wave","f1","f1Body"],["bars","f2","f2Body"],["spark","f3","f3Body"]].map(([ic, title, text])=>'<article class="feature"><div class="mini-icon">' + icon(ic) + '</div><h3>' + e(t(title)) + '</h3><p>' + e(t(text)) + '</p></article>').join("") +
    '</div></div></section>', "home");
}
function privacyPage() {
  shell('<article class="shell prose"><p class="eyebrow"><span></span>' + e(t("tag")) + '</p><h1>' + e(t("privacyTitle")) + '</h1>' +
    [["data-use","p1","p1Body"],["recommendations","p2","p2Body"],["support","p3","p3Body"],["expiry","p4","p4Body"]].map(([id,h,p])=>'<section id="' + id + '"><h2>' + e(t(h)) + '</h2><p>' + e(t(p)) + '</p></section>').join("") +
    btn("demo","/demo") + '</article>', "privacy");
}
function messages(id) { return '<p id="' + id + '" class="form-msg" role="alert" tabindex="-1" hidden></p>'; }
function onboarding() {
  const needsCode = Boolean(state.config?.requires_access_code);
  shell('<section class="shell narrow"><p class="eyebrow"><span></span>' + e(t("adult")) + '</p><h1>' + e(t("choose")) + '</h1><p class="lede">' + e(t("onboardBody")) + '</p>' +
    (state.notice ? '<p class="notice" role="status">' + e(t(state.notice)) + '</p>' : '') +
    '<form id="onboard" class="panel start-panel"><fieldset><legend>' + e(t("profile")) + '</legend><div class="profiles">' +
    [["arif","arifStory","arifBody"],["samir","samirStory","samirBody"]].map(([id,h,b],i)=>'<label class="profile-choice"><input name="persona" type="radio" value="' + id + '"' + (i===0 ? " checked" : "") + ' required><span><strong>' + e(t(id)) + '</strong><span class="profile-title">' + e(t(h)) + '</span><small>' + e(t(b)) + '</small></span></label>').join("") +
    '</div></fieldset><label class="check-label"><input name="consent" type="checkbox" required><span>' + e(t("consent")) + '</span></label>' +
    (needsCode ? '<label class="field" for="access-code"><span>' + e(t("code")) + '</span><input id="access-code" name="access_code" type="password" required maxlength="128" autocomplete="off"></label>' : "") +
    messages("onboard-error") + '<div class="actions"><button class="btn primary" type="submit">' + e(t("begin")) + ' ' + icon("arrow",17) + '</button><a href="/privacy" data-route>' + e(t("privacy")) + '</a></div></form></section>', "onboard");
}
function offline() {
  shell('<section class="shell narrow"><div class="panel offline"><div class="mini-icon">' + icon("wave") + '</div><h1>' + e(t("unavailable")) + '</h1><p>' + e(t("unavailableBody")) + '</p><button type="button" class="btn primary" data-action="retry">' + e(t("retry")) + '</button></div></section>', "onboard");
}

function stats(data) {
  const latest = data.entries.at(-1);
  const goals = data.goals ?? [];
  const completed = goals.filter((goal) => goal.completed).length;
  const latestDate = latest ? dt(latest.day) : "—";
  return '<div class="stat-grid">' + [
    ["moon", "sleep", latest ? hoursText(latest.sleep_minutes) : "—", latestDate],
    ["sun", "mood", latest?.mood == null ? "—" : t("mood" + latest.mood), latestDate],
    ["wave", "energy", latest ? n(latest.energy) + " / " + n(5) : "—", latestDate],
    ["target", "weeklyProgress", goals.length ? n(completed) + " / " + n(goals.length) : "—", t(goals.length ? "thisWeek" : "noGoalProgress")],
  ].map(([i,k,v,cap])=>'<article class="stat"><div class="mini-icon">' + icon(i,19) + '</div><div><p>' + e(t(k)) + '</p><strong>' + e(v) + '</strong><small>' + e(cap) + '</small></div></article>').join("") + '</div>';
}
function checkinPanel(data) {
  const day = state.checkinDay ?? data.today;
  const entry = data.entries.find((row) => row.day === day);
  const input = (key, id, value, attrs) => '<label class="field" for="' + id + '"><span>' + e(t(key)) + '</span><input id="' + id + '" name="' + id + '" type="number" ' + attrs + ' value="' + e(value) + '"></label>';
  const scale = (key, labels, value, required) => '<fieldset class="energy"><legend>' + e(t(key)) + '</legend><div class="energy-grid">' +
    labels.map((label, index) => '<label class="energy-choice"><input type="radio" name="' + key + '" value="' + (index + 1) + '"' +
      (value === index + 1 ? " checked" : "") + (required ? " required" : "") + '><span><strong>' + e(n(index + 1)) +
      '</strong><small>' + e(t(label)) + '</small></span></label>').join("") + '</div></fieldset>';
  const extraOpen = currentPath() === "/check-in";
  return '<section id="checkin" class="panel"><div class="panel-top"><div><p class="eyebrow muted">' + e(dt(day)) + '</p><h2>' + e(t(day === data.today ? "checkin" : "pastCheckin")) + '</h2></div>' + (entry ? '<span class="tiny-pill">' + icon("check",14) + e(t("recorded")) + '</span>' : "") + '</div><p class="muted">' + e(t("checkinCopy")) + '</p>' +
    '<label class="field" for="checkin-day"><span>' + e(t("date")) + '</span><input id="checkin-day" type="date" min="' + e(data.trend_start) + '" max="' + e(data.today) + '" value="' + e(day) + '" required></label>' +
    '<form id="check-form">' + scale("mood", ["mood1", "mood2", "mood3", "mood4", "mood5"], entry?.mood, false) +
    '<div class="fields two">' +
    input("sleepHours","sleep-hours",entry ? String(Math.round(entry.sleep_minutes/60*100)/100) : "",'min="0" max="18" step="0.01" inputmode="decimal" required') +
    input("moveMinutes","movement",entry?.activity_minutes ?? "",'min="0" max="240" step="1" inputmode="numeric" required') +
    '</div>' + scale("energy", ["veryLow","low","steady","good","high"], entry?.energy, true) +
    '<details class="checkin-details"' + (extraOpen ? " open" : "") + '><summary>' + e(t("moreDetails")) + '</summary><div class="fields two">' +
    input("stress", "stress", entry?.stress ?? "", 'min="0" max="100" step="1" inputmode="numeric"') +
    input("hydration", "hydration", entry?.hydration ?? "", 'min="0" max="30" step="1" inputmode="numeric"') +
    '</div><label class="field" for="notes"><span>' + e(t("notes")) + '</span><textarea id="notes" name="notes" rows="2" maxlength="500" aria-describedby="notes-help">' +
    e(entry?.notes ?? "") + '</textarea></label><p id="notes-help" class="fine">' + e(t("fictionalText")) + '</p></details>' +
    messages("check-error") + '<div class="actions"><button type="submit" class="btn primary">' + e(t(entry ? "update" : "save")) + '</button><button class="btn ghost" type="button" data-action="sample">' + e(t("sample")) + '</button>' +
    (entry ? '<button class="btn danger" type="button" data-action="delete-checkin">' + e(t("deleteCheckin")) + '</button>' : "") + '</div></form>' +
    '<dialog id="delete-checkin-dialog" aria-labelledby="delete-checkin-title"><form id="delete-checkin-form"><h2 id="delete-checkin-title">' + e(t("deleteCheckinTitle")) + '</h2><p>' + e(dt(day)) + '</p>' + messages("delete-checkin-error") + '<div class="actions"><button type="button" class="btn ghost" data-action="cancel-delete-checkin" autofocus>' + e(t("cancel")) + '</button><button class="btn danger solid" type="submit">' + e(t("deleteNow")) + '</button></div></form></dialog></section>';
}
function suggestion(data) {
  const s = data.suggestion;
  const [title, body] = (language === "bn" ? banglaCards[s.id] : null) ?? [s.title, s.body];
  const reason = (language === "bn" ? banglaReasons[s.reason_key] : null) ?? s.reason;
  const kind = s.kind === "retrieval" ? "retrieved" : s.kind === "support" ? "support" : "fallback";
  return '<section class="panel next-card" data-suggestion="' + e(s.id) + '"><div class="mini-icon">' + icon("spark") + '</div><p class="eyebrow">' + e(t(kind)) + '</p><h2>' + e(title) + '</h2><p>' + e(body) + '</p>' +
    '<details><summary>' + e(t("why")) + '</summary><p>' + e(reason) + '</p></details><p class="source">' + e(t("source")) + ': ' + literalLink(s.source) + '</p>' +
    '<div class="actions">' + (s.kind === "support" ? "" : '<button class="btn primary" type="button" data-activity="breathing">' + icon("play", 16) + e(t("breathing")) + '</button>') +
    (currentPath() === "/coach" ? "" : btn("viewCoach", "/coach", "btn ghost")) + '</div>' +
    '<a class="support-link" href="/privacy#support" data-route>' + e(t("askHelp")) + ' ' + icon("arrow",15) + '</a></section>';
}
const metricInfo = {
  sleep: ["sleep","sleep_minutes",1080,hoursText],
  movement: ["activity","activity_minutes",240,motionText],
  mood: ["mood","mood",5,n],
  energy: ["energy","energy",5,n],
};
function dateFromOffset(start, i) { const day = new Date(start + "T12:00:00Z"); day.setUTCDate(day.getUTCDate()+i); return day.toISOString().slice(0,10); }
function textVars(key, values) {
  return t(key).replace(/\{(\w+)\}/g, (match, variable) => String(values[variable] ?? match));
}
function chart(data) {
  const chartData = currentPath() === "/insights" && state.insights
    ? state.insights : { start: data.trend_start, end: data.today, days: 14, entries: data.entries };
  const [, key, , display] = metricInfo[state.metric];
  const entries = new Map(chartData.entries.map((row) => [row.day, row]));
  const values = chartData.entries.flatMap((row) => row[key] == null ? [] : [Number(row[key])]);
  const max = state.metric === "sleep" ? Math.max(480, ...values) : state.metric === "movement" ? Math.max(30, ...values) : 5;
  const days = Array.from({ length: chartData.days }, (_, index) => dateFromOffset(chartData.start, index));
  const period = currentPath() === "/insights" ? textVars("chartPeriod", { start: dt(chartData.start), end: dt(chartData.end) }) : t("period");
  return '<section id="trends" class="panel"><div class="panel-top trend-top"><div><h2>' + e(t("pattern")) + '</h2><p class="muted">' + e(period) + '</p></div><div class="segmented" aria-label="' + e(t("pattern")) + '">' +
    Object.entries(metricInfo).map(([id,[label]])=>'<button type="button" data-metric="' + id + '" aria-pressed="' + (id === state.metric) + '">' + e(t(label)) + '</button>').join("") +
    '</div></div><div class="plot insight-plot" style="--plot-days:' + days.length + '" aria-hidden="true">' +
    days.map((day, i) => {
      const value = entries.get(day)?.[key];
      const showLabel = i % Math.ceil(days.length / 7) === 0 || i === days.length - 1;
      return '<div class="plot-col"><span class="bar' + (value == null ? " missing" : "") + '" style="--height:' +
        (value == null ? 0 : tri(value, max)) + '%" title="' + e(dt(day) + " · " + (value == null ? t("emptyValue") : display(value))) +
        '"></span><small>' + e(showLabel ? dt(day, { day: "numeric" }) : "\u00a0") + '</small></div>';
    }).join("") +
    '</div><details class="data-table"><summary>' + e(t("table")) + '</summary><div class="table-scroll" tabindex="0" role="region" aria-label="' + e(t("table")) + '"><table><caption class="sr">' + e(period) + '</caption><thead><tr>' +
    ["date","sleep","activity","energy","mood","type"].map(k=>'<th scope="col">' + e(t(k)) + '</th>').join("") +
    '</tr></thead><tbody>' + (chartData.entries.length ? [...chartData.entries].reverse().map(row=>'<tr><th scope="row">' + e(dt(row.day,{day:"numeric",month:"short"})) + '</th><td>' + e(hoursText(row.sleep_minutes)) + '</td><td>' + e(motionText(row.activity_minutes)) + '</td><td>' + e(n(row.energy)) + '</td><td>' + e(row.mood == null ? "—" : t("mood" + row.mood)) + '</td><td>' + e(t(row.is_sample ? "sampleRow" : "practiceRow")) + '</td></tr>').join("") : '<tr><td colspan="6">' + e(t("noData")) + '</td></tr>') +
    '</tbody></table></div></details></section>';
}
function insights(data) {
  const ranges = { week: "weeklyRange", 7: "days7", 14: "days14", 30: "days30" };
  const current = state.insights;
  const a = current?.averages;
  const h = current?.habits;
  return '<section class="panel insights-controls"><div class="segmented" role="group" aria-label="' + e(t("dateRange")) + '">' +
    ["week", "7", "14", "30"].map((value) => '<button type="button" data-range="' + value + '" aria-pressed="' +
      (state.insightRange === value) + '">' + e(t(ranges[value])) + '</button>').join("") + '</div>' +
    messages("insights-error") + '</section>' +
    (a && h ? '<section class="stat-grid insight-summary">' + [
      ["moon", "sleep", a.sleep_minutes == null ? "—" : hoursText(a.sleep_minutes), t("loggedAverage")],
      ["sun", "mood", a.mood == null ? "—" : n(a.mood) + " / " + n(5), t("loggedAverage")],
      ["wave", "energy", a.energy == null ? "—" : n(a.energy) + " / " + n(5), t("loggedAverage")],
      ["target", "habitConsistency", h.possible ? n(h.percent) + "%" : "—", textVars("habitSummary", { done: n(h.completed), total: n(h.possible) })],
    ].map(([symbol, key, value, caption]) => '<article class="stat"><div class="mini-icon">' + icon(symbol, 19) +
      '</div><div><p>' + e(t(key)) + '</p><strong>' + e(value) + '</strong><small>' + e(caption) + '</small></div></article>').join("") +
    '</section>' : "") + chart(data);
}

function goals(data, heading = "dailyTargets") {
  const w=data.week;
  const p=(key, done,target) => '<div class="progress-row"><label>' + e(t(key)) + '<strong>' + e(n(done)+" / "+n(target)) + '</strong></label><progress max="' + e(target) + '" value="' + e(Math.min(done,target)) + '" aria-label="' + e(t(key)) + '"></progress></div>';
  return '<section id="goals" class="panel"><p class="eyebrow muted">' + e(dt(w.start,{day:"numeric",month:"short"})+" – "+dt(w.end,{day:"numeric",month:"short"})) + '</p><h2>' + e(t(heading)) + '</h2><p class="muted">' + e(t("weekDesc")) + '</p>' +
    p("moved",w.activity_done,w.activity_target)+p("logged",w.checkin_done,w.checkin_target) + '<form id="goals-form"><div class="fields two">' +
    [["move-goal","movementTarget",w.activity_target],["check-goal","checkinTarget",w.checkin_target]].map(([id,k,v])=>'<label class="field" for="' + id + '"><span>' + e(t(k)) + '</span><input type="number" id="' + id + '" name="' + id + '" min="1" max="7" step="1" value="' + e(v) + '" required></label>').join("") +
    '</div><p class="fine">' + e(t("countNote")) + '</p>' + messages("goals-error") + '<button class="btn primary" type="submit">' + e(t("saveGoals")) + '</button></form></section>';
}
const habitNames = { screen_break: "screenBreak", wind_down: "windDown", reflect: "reflect" };
function habits(data) {
  const day = state.habitDay ?? data.today;
  const completions = data.habit_completions ?? [];
  const elapsedDays = Array.from({ length: 7 }, (_, i) => dateFromOffset(data.week.start, i))
    .filter((date) => date <= data.today);
  return '<section id="habits" class="panel habits"><h2>' + e(t("habits")) + '</h2><p class="muted">' + e(t("habitsNote")) + '</p>' +
    '<label class="field" for="habit-day"><span>' + e(t("date")) + '</span><select id="habit-day">' +
    elapsedDays.map((date) => '<option value="' + e(date) + '"' + (day === date ? ' selected' : '') + '>' + e(dt(date)) + '</option>').join("") + '</select></label>' +
    messages("habit-error") + '<h3>' + e(t("presetHabits")) + '</h3><div class="habit-list">' + Object.entries(habitNames).map(([habit, key]) => {
      const rows = completions.filter((row) => row.habit === habit);
      const completed = rows.some((row) => row.day === day);
      return '<div><button class="btn ghost" type="button" data-habit="' + habit + '" aria-pressed="' + completed + '">' +
        (completed ? icon("check", 15) : '') + e(t(key)) + '</button><small class="muted">' + e(textVars("daysDone", { n: n(rows.length) })) +
        '</small><small class="muted">' + e(textVars("streak", { n: n(data.habit_streaks?.[habit] ?? 0) })) + '</small></div>';
    }).join("") + '</div><h3 class="custom-habits-heading">' + e(t("customHabits")) + '</h3>' +
    (data.custom_habits?.length ? '<ul class="item-list">' + data.custom_habits.map((habit) =>
      itemRow(habit, "habit", habit.days.includes(day), textVars("streak", { n: n(habit.streak) }), true, day < habit.created_day)).join("") + '</ul>'
      : '<p class="muted">' + e(t("customHabitsEmpty")) + '</p>') + itemForm("habit") + '</section>';
}

function itemForm(kind) {
  const label = kind === "goal" ? "goalTitle" : "habitTitle";
  const action = kind === "goal" ? "addGoal" : "addHabit";
  return '<form id="custom-' + kind + '-form" class="app-form-actions"><label class="field"><span>' + e(t(label)) +
    '</span><input type="text" name="title" required maxlength="80"></label><button class="btn primary" type="submit">' +
    icon("plus", 16) + e(t(action)) + '</button></form>';
}

function itemRow(item, kind, completed, caption = "", editable = true, unavailable = false) {
  const key = kind === "goal" ? ["editGoal", "deleteGoal"] : ["editHabit", "deleteHabit"];
  const attrs = ' data-kind="' + kind + '" data-id="' + e(item.id) + '"';
  return '<li class="item-row"><div class="item-body"><button type="button" class="btn ghost item-toggle" data-action="toggle-item"' +
    attrs + ' aria-pressed="' + completed + '"' + (unavailable ? " disabled" : "") + '>' +
    (completed ? icon("check", 16) : '<span class="item-indicator" aria-hidden="true"></span>') +
    e(item.title) + '</button>' + (caption ? '<small class="muted">' + e(caption) + '</small>' : "") +
    (unavailable ? '<small class="muted">' + e(t("habitNotCreated")) + '</small>' : "") + '</div>' +
    (editable ? '<div class="item-actions"><button class="btn ghost" type="button" data-action="edit-item"' + attrs +
      ' aria-label="' + e(t(key[0]) + " · " + item.title) + '">' + icon("edit", 16) + '</button>' +
      '<button class="btn danger" type="button" data-action="delete-item"' + attrs + ' aria-label="' + e(t(key[1]) + " · " + item.title) +
      '">' + icon("trash", 16) + '</button></div>' : "") + '</li>';
}

function customGoals(data, preview = false) {
  const items = data.goals ?? [];
  const completed = items.filter((goal) => goal.completed).length;
  return '<section id="weekly-checklist" class="panel"><div class="panel-top"><h2>' + e(t("week")) + '</h2><span class="mini-icon">' +
    icon("target", 19) + '</span></div>' +
    (items.length ? '<div class="progress-row"><label for="weekly-checklist-progress">' + e(t("weeklyProgress")) +
      '<strong>' + e(n(completed) + " / " + n(items.length)) + '</strong></label><progress id="weekly-checklist-progress" max="' + items.length +
      '" value="' + completed + '"></progress></div><ul class="item-list">' +
      (preview ? items.slice(0, 4) : items).map((goal) => itemRow(goal, "goal", goal.completed, "", !preview)).join("") +
      '</ul>' : '<p class="muted">' + e(t("customGoalsEmpty")) + '</p>') +
    messages("goal-error") + (preview ? btn("viewGoals", "/goals-habits", "btn ghost") : itemForm("goal")) + '</section>';
}

function itemDialog() {
  return '<dialog id="item-dialog" aria-labelledby="item-dialog-title"><form id="item-form"><h2 id="item-dialog-title"></h2>' +
    '<p id="item-dialog-caption"></p><label id="item-dialog-field" class="field"><span></span><input name="title" type="text" maxlength="80"></label>' +
    messages("item-error") + '<div class="actions"><button class="btn ghost" type="button" data-action="close-item" autofocus>' + e(t("cancel")) +
    '</button><button id="item-dialog-submit" class="btn primary" type="submit"></button></div></form></dialog>';
}
function controls(data) {
  const profile = data.profile;
  return '<div class="settings-stack" id="controls"><section class="panel"><h2>' + e(t("profile")) + '</h2>' +
    '<form id="profile-form"><label class="field"><span>' + e(t("profileName")) + '</span><input name="name" maxlength="60" required value="' +
    e(profile.name) + '"></label><p class="fine">' + e(t("fictionalText")) + '</p>' + messages("profile-error") +
    '<button type="submit" class="btn primary">' + e(t("profileSave")) + '</button></form></section>' +
    '<section class="panel"><h2>' + e(t("appearance")) + '</h2><div class="fields two">' +
    '<label class="field" for="language"><span>' + e(t("language")) + '</span>' + languageSelect() + '</label>' +
    '<label class="field" for="theme"><span>' + e(t("theme")) + '</span><select id="theme">' +
    themes.map((value) => '<option value="' + value + '"' + (theme === value ? " selected" : "") + '>' + e(t(value)) + '</option>').join("") +
    '</select></label></div>' + messages("appearance-error") + '</section>' +
    '<section class="panel" id="reminders"><h2>' + e(t("reminder")) + '</h2><p class="muted">' + e(t("reminderNote")) + '</p>' +
    '<label class="check-label"><input id="reminder-enabled" type="checkbox"' + (profile.reminder_enabled === false ? "" : " checked") +
    '><span>' + e(t("reminderEnabled")) + '</span></label>' +
    '<form id="reminder-form"><label class="field" for="reminder-time"><span>' + e(profile.timezone) +
    '</span><input name="reminder-time" id="reminder-time" type="time" value="' + e(data.reminder.time ?? "") + '" required></label>' +
    messages("reminder-error") + '<div class="actions"><button type="submit" class="btn primary">' + e(t("saveReminder")) + '</button>' +
    (data.reminder.time ? '<button type="button" class="btn ghost" data-action="reminder-off">' + e(t("turnOff")) + '</button>' : "") +
    '</div></form></section><section class="panel"><h2>' + e(t("notificationSettings")) + '</h2><p class="muted">' + e(t("notificationNote")) + '</p>' +
    '<label class="check-label"><input id="notification-enabled" type="checkbox"' + (profile.notifications_enabled ? " checked" : "") +
    '><span>' + e(t("notificationEnabled")) + '</span></label>' +
    '<p class="fine" id="notification-permission" role="status">' + e(t(permissionCopy[notificationPermission()])) + '</p>' +
    messages("notification-error") + (notificationPermission() === "default" ?
      '<button type="button" class="btn ghost" data-action="notification-permission">' + e(t("notificationGrant")) + '</button>' : "") +
    '</section><section class="panel"><div class="panel-top"><h2>' + e(t("data")) + '</h2><div class="mini-icon">' + icon("shield") +
    '</div></div><p class="muted">' + e(t("dataNote")) + '</p><p class="fine">' + e(t("expires") + ": " +
    dt(profile.expires_at, { day: "numeric", month: "short", year: "numeric" })) + '</p>' + messages("data-error") +
    '<div class="actions"><button class="btn ghost" type="button" data-action="export">' + e(t("export")) +
    '</button><button class="btn danger" type="button" data-action="delete">' + e(t("delete")) +
    '</button><a class="btn ghost" href="/privacy" data-route>' + e(t("privacy")) + '</a></div></section>' +
    '<dialog id="delete-dialog" aria-labelledby="delete-title"><form id="delete-form"><h2 id="delete-title">' + e(t("deleteTitle")) +
    '</h2><p>' + e(t("deleteBody")) + '</p>' + messages("delete-error") +
    '<div class="actions"><button type="button" class="btn ghost" data-action="cancel-delete" autofocus>' + e(t("cancel")) +
    '</button><button class="btn danger solid" type="submit">' + e(t("deleteNow")) + '</button></div></form></dialog></div>';
}
const permissionCopy = {
  granted: "notificationGranted", default: "notificationDefault", denied: "notificationDenied", unsupported: "notificationUnsupported",
};

function quickActions(includeLogging = true) {
  const label = (glyphName, title, description) => '<span class="mini-icon">' + icon(glyphName, 19) + '</span><span><strong>' +
    e(t(title)) + '</strong>' + (description ? '<small>' + e(t(description)) + '</small>' : "") + '</span>';
  return '<section class="panel quick-actions"><h2>' + e(t("quickActions")) + '</h2><div class="quick-action-grid">' +
    '<button class="btn ghost quick-action" type="button" data-activity="breathing">' + label("play", "breathing", "breathingShort") + '</button>' +
    (includeLogging ? '<a class="btn ghost quick-action" href="/check-in#movement" data-route>' + label("wave", "logMovement") + '</a>' +
      '<a class="btn ghost quick-action" href="/check-in#hydration" data-route>' + label("drop", "logHydration") + '</a>' : "") +
    '<button class="btn ghost quick-action" type="button" data-activity="mindfulness">' + label("leaf", "mindfulness", "mindfulnessShort") +
    '</button></div></section>';
}

function dashboard(data) {
  return '<header class="dash-hero"><div class="app-greeting"><h1>' + e(t("dashboard")) + '</h1><p class="app-personal-greeting">' +
    e(textVars("todayGreeting", { name: personName(data.profile) })) + '</p><p>' + e(t("dashboardSubtitle")) + '</p></div></header>' +
    stats(data) + '<div class="dashboard-columns"><div class="dashboard-primary">' + checkinPanel(data) + chart(data) +
    '</div><div class="dashboard-secondary">' + suggestion(data) + customGoals(data, true) + '</div></div>' + quickActions();
}
function refreshReminder() {
  const alert = document.getElementById("reminder-due");
  const data = state.data;
  if (!alert || !data?.reminder.time || data.profile.reminder_enabled === false) {
    if (alert) alert.hidden = true;
    return;
  }
  const now = new Date();
  const timeZone = data.profile.timezone;
  const dateParts = new Intl.DateTimeFormat("en-GB", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(now);
  const part = (key) => dateParts.find((p) => p.type === key)?.value;
  const day = [part("year"), part("month"), part("day")].join("-");
  if (day !== data.today) { alert.hidden = true; return; }
  const time = new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(now);
  alert.hidden = Boolean(data.today_entry) || time < data.reminder.time;
  if (!alert.hidden && data.profile.notifications_enabled) {
    showReminderNotification(day, { title: "SteadyDay", body: t("reminderDue") });
  }
}
function render() {
  if (state.screen === "app") {
    const data = state.data;
    const views = {
      "/demo": () => dashboard(data),
      "/check-in": () => checkinPanel(data),
      "/insights": () => insights(data),
      "/goals-habits": () => '<div class="settings-stack">' + customGoals(data) + habits(data) + goals(data) + itemDialog() + '</div>',
      "/coach": () => '<div class="settings-stack">' + suggestion(data) + quickActions(false) + '</div>',
      "/settings": () => controls(data),
    };
    appShell(views[currentPath()]());
  }
  else if (state.screen==="onboard") onboarding();
  else if (state.screen==="loading") {
    mount.innerHTML = '<main id="main" class="shell narrow" aria-busy="true"><p class="boot" role="status">' + e(t("loading")) + '</p></main>';
  }
  else if (state.screen==="error") offline();
  else if (state.screen==="privacy") privacyPage();
  else landing();
}
let seq=0;
function applyProfile(profile) {
  if (["en", "bn"].includes(profile.language)) {
    language = profile.language;
    savePreference("language", language);
  }
  if (themes.includes(profile.theme)) {
    theme = profile.theme;
    savePreference("theme", theme);
    applyTheme();
  }
}

async function route({ focus = false, preserveNotice = false } = {}) {
  const mark = ++seq;
  if (!preserveNotice) state.notice = "";
  state.dialog = null;
  const pathname = currentPath();
  if (pathname === "/privacy") { state.screen = "privacy"; render(); }
  else if (Object.hasOwn(screens, pathname)) {
    state.screen = "loading";
    render();
    try {
      const data = await api("dashboard");
      if (mark !== seq) return;
      applyProfile(data.profile);
      state.data = data;
      if (state.checkinDay && (state.checkinDay < data.trend_start || state.checkinDay > data.today)) state.checkinDay = null;
      if (state.habitDay && (state.habitDay < data.week.start || state.habitDay > data.today)) state.habitDay = null;
      if (pathname === "/insights") {
        const current = await api("insights?days=" + state.insightRange);
        if (mark !== seq) return;
        state.insights = current;
      }
      state.screen = "app";
      render();
    } catch (err) {
      if (mark!==seq) return;
      if (err.status===401) {
        state.data = null;
        try {
          const config = await api("config");
          if (mark!==seq) return;
          state.config=config; state.screen="onboard"; render();
        } catch { if (mark===seq) {state.screen="error";render();} }
      } else { state.screen="error";render(); }
    }
  } else {state.screen="home";render();}
  if (mark===seq && location.hash) {
    try {
      const anchor = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      anchor?.scrollIntoView();
      if (focus && anchor?.matches("input, select, textarea, button")) anchor.focus({ preventScroll: true });
    } catch {}
  }
  else if (mark===seq && focus) { window.scrollTo(0,0);document.getElementById("main")?.focus(); }
}

function showError(id, error) {
  const box=document.getElementById(id);
  if (box) { box.textContent=t(failKey(error.code));box.hidden=false;box.focus(); }
}
function showStatus(key) {
  state.notice=key;
  const node=document.getElementById("status");
  if (node) { node.hidden=false;node.textContent=t(key); }
}
function renderResult(data, notice = "") {
  state.data = data;
  state.notice = notice;
  state.dialog = null;
  render();
  if (notice) document.getElementById("status")?.focus({ preventScroll: true });
}
let pending=false;
const preferenceFields = { "reminder-enabled": "reminder_enabled", "notification-enabled": "notifications_enabled" };
const preferenceControls = "#language, #theme, #reminder-enabled, #notification-enabled";
let preferenceWrite;
async function task(form, fn, errorId) {
  if (pending) return;
  pending=true;
  const button=form?.querySelector('button[type="submit"]');
  const enabledPreferences = [...mount.querySelectorAll(preferenceControls)].filter((field) => !field.disabled);
  enabledPreferences.forEach((field) => { field.disabled = true; });
  if (button) {button.disabled=true;form.setAttribute("aria-busy","true");}
  try { await fn(); }
  catch (error) {
    if (error?.status===401) { state.notice="missing";await route({preserveNotice:true,focus:true}); }
    else showError(errorId,error);
  }
  finally {
    pending=false;
    enabledPreferences.forEach((field) => { field.disabled = false; });
    if (button) {button.disabled=false;form.removeAttribute("aria-busy");}
  }
}

async function updatePreference(key, value, errorId) {
  const path = currentPath();
  const write = task(null, async () => {
    const data = await api("profile", "PUT", { [key]: value });
    applyProfile(data.profile);
    state.data = data;
    if (path !== currentPath()) return;
    if (key === "language") {
      renderResult(data, "profileSaved");
      document.getElementById("language")?.focus({ preventScroll: true });
    } else {
      refreshReminder();
      showStatus("profileSaved");
    }
  }, errorId);
  preferenceWrite = write;
  try { await write; }
  finally { if (preferenceWrite === write) preferenceWrite = null; }
}

function openItemDialog(action, kind, id) {
  const item = (kind === "goal" ? state.data.goals : state.data.custom_habits)?.find((row) => row.id === id);
  const dialog = document.getElementById("item-dialog");
  if (!item || !dialog || dialog.open) return;
  const editing = action === "edit-item";
  const goal = kind === "goal";
  state.dialog = { editing, kind, id };
  dialog.querySelector("#item-dialog-title").textContent = t(editing ? (goal ? "editGoal" : "editHabit") : (goal ? "deleteGoalTitle" : "deleteHabitTitle"));
  const caption = dialog.querySelector("#item-dialog-caption");
  caption.textContent = editing ? "" : item.title + (goal ? "" : " · " + t("deleteHabitBody"));
  caption.hidden = editing;
  const field = dialog.querySelector("#item-dialog-field");
  field.hidden = !editing;
  field.querySelector("span").textContent = t(goal ? "goalTitle" : "habitTitle");
  const input = field.querySelector("input");
  input.required = editing;
  input.value = editing ? item.title : "";
  const submit = dialog.querySelector("#item-dialog-submit");
  submit.textContent = t(editing ? "saveChanges" : "deleteNow");
  submit.className = editing ? "btn primary" : "btn danger solid";
  dialog.querySelector("#item-error").hidden = true;
  dialog.showModal();
  if (editing) { input.focus(); input.select(); }
}

function focusMatching(selector, key, value) {
  Array.from(mount.querySelectorAll(selector)).find((element) => element.dataset[key] === value)?.focus({ preventScroll: true });
}

mount.addEventListener("click",async (event)=>{
  const target=event.target.closest("[data-route], [data-action], [data-metric], [data-habit], [data-range]");
  if(!target) return;
  if(target.matches("[data-route]")){
    if(event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const u=new URL(target.href,location.href);
    if(u.origin!==location.origin) return;
    event.preventDefault();
    if (preferenceWrite) await preferenceWrite;
    history.pushState(null,"",u.pathname+u.hash); await route({focus:true});
    return;
  }
  if(target.dataset.metric){
    if(!Object.hasOwn(metricInfo,target.dataset.metric)||!state.data)return;
    state.metric=target.dataset.metric;
    document.getElementById("trends").outerHTML=chart(state.data);
    mount.querySelector('[data-metric="'+state.metric+'"]')?.focus({preventScroll:true});
    return;
  }
  if (target.dataset.range && currentPath() === "/insights") {
    const range = target.dataset.range;
    if (range === state.insightRange || !["week", "7", "14", "30"].includes(range) || pending) return;
    target.disabled = true;
    const mark = seq;
    await task(null, async () => {
      const result = await api("insights?days=" + range);
      if (mark !== seq) return;
      state.insightRange = range;
      state.insights = result;
      render();
      focusMatching("[data-range]", "range", range);
    }, "insights-error");
    target.disabled = false;
    return;
  }
  const habit = target.dataset.habit;
  if (habit && Object.hasOwn(habitNames, habit) && state.data && !pending) {
    target.disabled = true;
    await task(null, async () => {
      const data = await api("habits", "PUT", {
        habit, day: state.habitDay ?? state.data.today, completed: target.getAttribute("aria-pressed") !== "true",
      });
      state.data = data;
      const panel = document.getElementById("habits");
      if (!panel) return;
      panel.outerHTML = habits(data);
      focusMatching("[data-habit]", "habit", habit);
    }, "habit-error");
    target.disabled = false;
    return;
  }
  const action=target.dataset.action;
  if(action==="retry") await route();
  else if(action==="sample"){
    document.getElementById("sleep-hours").value="6.75";
    document.getElementById("movement").value="20";
    mount.querySelector('input[name="energy"][value="3"]').checked=true;
    mount.querySelector('input[name="mood"][value="4"]').checked=true;
    document.getElementById("stress").value="30";
    document.getElementById("hydration").value="6";
    document.getElementById("sleep-hours").focus();
  } else if (action === "toggle-item" && !pending) {
    const { kind, id } = target.dataset;
    const payload = { id, completed: target.getAttribute("aria-pressed") !== "true" };
    if (kind === "habit") payload.day = state.habitDay ?? state.data.today;
    target.disabled = true;
    await task(null, async () => {
      const data = await api(kind, "PUT", payload);
      state.data = data;
      render();
      focusMatching('[data-action="toggle-item"]', "id", id);
    }, kind + "-error");
    target.disabled = false;
  } else if (action === "edit-item" || action === "delete-item") {
    openItemDialog(action, target.dataset.kind, target.dataset.id);
  } else if (action === "close-item") {
    state.dialog = null;
    document.getElementById("item-dialog")?.close();
  } else if (action === "notification-permission") {
    const permission = await requestReminderPermission();
    const status = document.getElementById("notification-permission");
    if (status) status.textContent = t(permissionCopy[permission]);
    if (permission !== "default") target.hidden = true;
    refreshReminder();
  } else if(action==="reminder-off"){
    await task(null,async()=>renderResult(await api("reminder","PUT",{time:null}), "reminderSaved"), "reminder-error");
  } else if(action==="export"){
    await task(null,async()=>{
      const data=await api("export");
      if(data.synthetic_only!==true) throw new Error("Unexpected export.");
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));
      const link=document.createElement("a");link.href=url;link.download="steadyday-demo.json";
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),500);
      showStatus("exported");
    },"data-error");
  } else if(action==="delete-checkin") document.getElementById("delete-checkin-dialog")?.showModal();
  else if(action==="cancel-delete-checkin") document.getElementById("delete-checkin-dialog")?.close();
  else if(action==="delete") document.getElementById("delete-dialog")?.showModal();
  else if(action==="cancel-delete") document.getElementById("delete-dialog")?.close();
});
mount.addEventListener("change", async (event) => {
  const field = event.target;
  if (field.id === "language" && ["en", "bn"].includes(field.value)) {
    if (state.screen === "app") {
      if (!pending) await updatePreference("language", field.value, "appearance-error");
      if (field.isConnected) field.value = language;
    } else {
      language = field.value;
      savePreference("language", language);
      render();
      document.getElementById("language")?.focus({ preventScroll: true });
    }
    return;
  }
  if (field.id === "theme" && themes.includes(field.value)) {
    if (!pending) await updatePreference("theme", field.value, "appearance-error");
    if (field.isConnected) field.value = theme;
    return;
  }
  if (state.data && Object.hasOwn(preferenceFields, field.id)) {
    const key = preferenceFields[field.id];
    if (!pending) await updatePreference(key, field.checked, key === "reminder_enabled" ? "reminder-error" : "notification-error");
    if (field.isConnected) field.checked = Boolean(state.data?.profile[key]);
    return;
  }
  if (field.id === "habit-day" && state.data) {
    if (pending) { field.value = state.habitDay ?? state.data.today; return; }
    state.habitDay = field.value === state.data.today ? null : field.value;
    document.getElementById("habits").outerHTML = habits(state.data);
    document.getElementById("habit-day").focus({ preventScroll: true });
    return;
  }
  if (field.id !== "checkin-day" || !state.data) return;
  if (pending || !field.checkValidity()) {
    field.value = state.checkinDay ?? state.data.today;
    return;
  }
  state.checkinDay = field.value === state.data.today ? null : field.value;
  document.getElementById("checkin").outerHTML = checkinPanel(state.data);
  document.getElementById("checkin-day").focus({ preventScroll: true });
});
const formIds = new Set(["onboard", "check-form", "goals-form", "reminder-form", "delete-form", "delete-checkin-form",
  "custom-goal-form", "custom-habit-form", "item-form", "profile-form"]);
mount.addEventListener("submit",(event)=>{
  const form=event.target;
  if (!formIds.has(form.id)) return;
  event.preventDefault();
  const f=new FormData(form);
  if(form.id==="onboard"){
    void task(form,async()=>{
      try { await api("session","POST",{persona:f.get("persona"),consent:f.has("consent"),access_code:f.get("access_code")??""}); }
      catch(e){if(e.status!==409)throw e;}
      const data = await api("dashboard");
      if (data.profile.language !== language) await api("profile", "PUT", { language });
      await route({focus:true});
    },"onboard-error");
  } else if(form.id==="check-form"){
    void task(form,async()=>{
      const optional = (key) => f.get(key) === null || f.get(key) === "" ? null : Number(f.get(key));
      const data = await api("check-in", "PUT", {
        day: state.checkinDay ?? state.data.today,
        sleep_minutes: Math.round(Number(f.get("sleep-hours")) * 60),
        activity_minutes: Number(f.get("movement")),
        energy: Number(f.get("energy")),
        mood: optional("mood"), stress: optional("stress"), hydration: optional("hydration"), notes: f.get("notes").trim(),
      });
      renderResult(data, "saved");
    },"check-error");
  } else if(form.id==="delete-checkin-form"){
    void task(form,async()=>{
      const day = state.checkinDay ?? state.data.today;
      renderResult(await api("check-in?day=" + encodeURIComponent(day), "DELETE"), "checkinRemoved");
    },"delete-checkin-error");
  } else if(form.id==="goals-form"){
    void task(form,async()=>{
      renderResult(await api("goals", "PUT", { activity_days: Number(f.get("move-goal")), checkin_days: Number(f.get("check-goal")) }), "goalSaved");
    },"goals-error");
  } else if(form.id==="reminder-form"){
    void task(form,async()=>{
      renderResult(await api("reminder", "PUT", { time: f.get("reminder-time") }), "reminderSaved");
    },"reminder-error");
  } else if (form.id === "custom-goal-form" || form.id === "custom-habit-form") {
    const kind = form.id === "custom-goal-form" ? "goal" : "habit";
    void task(form, async () => {
      renderResult(await api(kind, "POST", { title: f.get("title").trim() }), kind + "Changed");
    }, kind + "-error");
  } else if (form.id === "item-form" && state.dialog) {
    const { editing, id, kind } = state.dialog;
    void task(form, async () => {
      const data = editing ? await api(kind, "PUT", { id, title: f.get("title").trim() })
        : await api(kind + "?id=" + encodeURIComponent(id), "DELETE");
      renderResult(data, kind + (editing ? "Changed" : "Removed"));
    }, "item-error");
  } else if (form.id === "profile-form") {
    void task(form, async () => {
      renderResult(await api("profile", "PUT", { name: f.get("name").trim() }), "profileSaved");
    }, "profile-error");
  } else if (form.id === "delete-form") {
    void task(form,async()=>{
      await api("session","DELETE");state.data=null;state.checkinDay=null;state.habitDay=null;state.notice="removed";
      state.insights = null;
      if (currentPath() !== "/demo") history.replaceState(null, "", "/demo");
      await route({preserveNotice:true,focus:true});
    },"delete-error");
  }
});
window.addEventListener("popstate", async () => {
  if (preferenceWrite) await preferenceWrite;
  await route();
});
initActivities(mount, { t, language: () => language });
setInterval(refreshReminder, 15000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshReminder(); });
void route();
