const activityCopy = {
  en: {
    breathing: ["Guided breathing", "Sit comfortably and let your breath move at a pace that feels easy."],
    mindfulness: ["Mindful pause", "Let your attention rest on something you can see, hear, or feel."],
    minutes: "Duration (minutes)", ready: "Ready when you are", start: "Start", pause: "Pause",
    resume: "Resume", reset: "Reset", close: "Close", paused: "Paused", done: "Practice complete",
    inhale: "Breathe in gently", exhale: "Breathe out slowly", notice: "Notice what is here",
    return: "Gently bring your attention back",
  },
  bn: {
    breathing: ["শ্বাসের অনুশীলন", "আরাম করে বসুন। যে ছন্দে স্বস্তি লাগে, সেভাবে শ্বাস নিন।"],
    mindfulness: ["মনোযোগের বিরতি", "আপনি যা দেখতে, শুনতে বা অনুভব করতে পাচ্ছেন, তার একটিতে মন দিন।"],
    minutes: "সময় (মিনিট)", ready: "প্রস্তুত হলে শুরু করুন", start: "শুরু", pause: "বিরতি",
    resume: "আবার শুরু", reset: "নতুন করে শুরু", close: "বন্ধ করুন", paused: "বিরতি চলছে", done: "অনুশীলন শেষ",
    inhale: "আস্তে শ্বাস নিন", exhale: "ধীরে শ্বাস ছাড়ুন", notice: "এই মুহূর্তে যা আছে খেয়াল করুন",
    return: "আলতো করে মনোযোগ ফিরিয়ে আনুন",
  },
};

const durations = [1, 2, 5];
const phases = {
  breathing: { interval: 4, labels: ["inhale", "exhale"] },
  mindfulness: { interval: 15, labels: ["notice", "return"] },
};

export function initActivities(mount, { language }) {
  const dialog = document.createElement("dialog");
  dialog.className = "activity-dialog";
  dialog.setAttribute("aria-labelledby", "activity-title");
  dialog.innerHTML = `
    <h2 id="activity-title"></h2>
    <p class="activity-intro"></p>
    <label class="field" for="activity-duration"><span></span><select id="activity-duration" autofocus></select></label>
    <div class="activity-display">
      <p class="activity-time" role="timer"></p>
      <p class="activity-phase" role="status"></p>
      <progress class="activity-progress" value="0"></progress>
    </div>
    <div class="activity-actions actions">
      <button type="button" class="btn primary" data-timer="toggle"></button>
      <button type="button" class="btn ghost" data-timer="reset"></button>
      <button type="button" class="btn ghost" data-timer="close"></button>
    </div>`;
  document.body.append(dialog);

  const durationSelect = dialog.querySelector("select");
  const time = dialog.querySelector(".activity-time");
  const phase = dialog.querySelector(".activity-phase");
  const progress = dialog.querySelector("progress");
  const toggle = dialog.querySelector('[data-timer="toggle"]');
  const reset = dialog.querySelector('[data-timer="reset"]');
  const close = dialog.querySelector('[data-timer="close"]');
  let activity;
  let locale;
  let copy;
  let duration;
  let elapsed;
  let started;
  let ticker;
  let trigger;

  function clearTicker() {
    clearInterval(ticker);
    ticker = undefined;
  }

  function paint() {
    let elapsedNow = elapsed + (started === null ? 0 : Date.now() - started);
    if (elapsedNow >= duration) {
      elapsedNow = elapsed = duration;
      started = null;
      clearTicker();
    }

    const remaining = Math.ceil((duration - elapsedNow) / 1000);
    const digits = new Intl.NumberFormat(locale, { minimumIntegerDigits: 2, useGrouping: false });
    time.textContent = digits.format(Math.floor(remaining / 60)) + ":" + digits.format(remaining % 60);
    progress.max = duration;
    progress.value = elapsedNow;
    const definition = phases[activity];
    const currentPhase = definition.labels[Math.floor(elapsedNow / (definition.interval * 1000)) % definition.labels.length];
    const label = elapsedNow === duration ? "done" : started !== null ? currentPhase : elapsed > 0 ? "paused" : "ready";
    if (phase.textContent !== copy[label]) phase.textContent = copy[label];
    toggle.textContent = copy[started !== null ? "pause" : elapsed > 0 && elapsed < duration ? "resume" : "start"];
    durationSelect.disabled = started !== null || (elapsed > 0 && elapsed < duration);
  }

  function setDuration(minutes) {
    clearTicker();
    duration = minutes * 60000;
    elapsed = 0;
    started = null;
    durationSelect.value = String(minutes);
    paint();
  }

  mount.addEventListener("click", (event) => {
    const button = event.target.closest("[data-activity]");
    if (!button || !Object.hasOwn(phases, button.dataset.activity) || dialog.open) return;
    event.preventDefault();
    activity = button.dataset.activity;
    trigger = button;
    const lang = language();
    locale = lang === "bn" ? "bn-BD" : "en-GB";
    copy = activityCopy[lang] ?? activityCopy.en;
    const [title, intro] = copy[activity];
    dialog.querySelector("h2").textContent = title;
    dialog.querySelector(".activity-intro").textContent = intro;
    dialog.querySelector("label span").textContent = copy.minutes;
    durationSelect.replaceChildren(...durations.map((value) => new Option(value.toLocaleString(locale), String(value))));
    progress.setAttribute("aria-label", title);
    reset.textContent = copy.reset;
    close.textContent = copy.close;
    setDuration(5);
    dialog.showModal();
  });

  durationSelect.addEventListener("change", () => setDuration(Number(durationSelect.value)));
  toggle.addEventListener("click", () => {
    if (started !== null) {
      elapsed += Date.now() - started;
      started = null;
      clearTicker();
    } else {
      if (elapsed >= duration) elapsed = 0;
      started = Date.now();
      ticker = setInterval(paint, 250);
    }
    paint();
  });
  reset.addEventListener("click", () => setDuration(Number(durationSelect.value)));
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    clearTicker();
    trigger?.focus();
    trigger = undefined;
  });
  window.addEventListener("popstate", () => { if (dialog.open) dialog.close(); });
}
