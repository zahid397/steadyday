"""Bounded, local information retrieval. The rules select context, not diagnoses."""
from collections import Counter
from datetime import date
from math import log, sqrt
import re
from typing import Any

CDC = {"label": "CDC · Sleep habits", "url": "https://www.cdc.gov/sleep/about/index.html"}
WHO = {"label": "WHO · Physical activity", "url": "https://www.who.int/initiatives/behealthy/physical-activity/"}
NHS = {"label": "NHS · Tiredness and fatigue", "url": "https://www.nhs.uk/symptoms/tiredness-and-fatigue/"}
DESIGN = {"label": "SteadyDay · Demo design", "url": "/privacy#recommendations"}



CARDS = {
    "restart": {
        "tags": "restart restart gap missed return setback resume checkin routine",
        "title": "Make the next check-in easy",
        "body": "Pick a time that suits you for one simple check-in. Your previous entries and weekly targets are still here.",
        "source": DESIGN,
    },
    "wind_down": {
        "tags": "sleep sleep irregular variation wind down bedtime routine rest schedule",
        "title": "Choose a regular wind-down cue",
        "body": "If it fits your schedule, choose one cue to start winding down, such as putting the phone aside around the same time.",
        "source": CDC,
    },
    "movement": {
        "tags": "movement movement activity active consistency goal walking comfortable",
        "title": "Choose movement that fits your day",
        "body": "If movement feels appropriate for you, choose something comfortable that fits your day, such as a short walk or wheeling. You can skip it or adjust your goal.",
        "source": WHO,
    },
    "adjust": {
        "tags": "goals review adjust achieved achievable plan choose consistency",
        "title": "Review what felt manageable",
        "body": "Keep a goal that fits your week. You can keep the same target, lower it, or leave it for another day.",
        "source": DESIGN,
    },
    "pause": {
        "tags": "stress high pause breathing rest quiet break settle",
        "title": "Take a quiet moment",
        "body": "If it feels comfortable, pause somewhere quiet and let your breath settle naturally. You can also take a short screen break or simply rest.",
        "source": DESIGN,
    },
    "build_on": {
        "tags": "energy improving continue repeat manageable build consistency",
        "title": "Build on what felt manageable",
        "body": "Think of one routine that felt manageable recently. If it still fits your day, try it again at the same pace.",
        "source": DESIGN,
    },
    "starter": {
        "tags": "",
        "title": "Start with one practice entry",
        "body": "Log a fictional check-in, or review your weekly targets. There is no score to reach.",
        "source": DESIGN,
    },
    "support": {
        "tags": "",
        "title": "Make space for qualified support",
        "body": "If low energy persists or affects daily life, consider speaking with a qualified healthcare professional. For urgent help, use local emergency services. This demo cannot assess causes or urgency.",
        "source": NHS,
    },
}

REASONS = {
    "gap": "There is a gap in your recent practice entries. The suggestion helps you resume without resetting progress.",
    "sleep": "Your recent practice sleep entries vary. This is a routine prompt, not a judgement about sleep quality.",
    "short_sleep": "Your latest practice entry records less sleep than the other recent days you logged.",
    "stress": "You selected a higher stress level in a recent practice entry.",
    "energy_up": "Your latest practice energy rating is higher than the previous one.",
    "movement": "Your chosen movement-day target is still open this week.",
    "review": "Your recent activity matches the current target; you can decide what to keep or change.",
    "starter": "There is too little history for retrieval, or retrieval is unavailable. This is the standard fallback.",
    "energy": "The latest practice entry marks energy as very low. The demo shows support information and withholds movement suggestions.",
}
TERMS = {
    "gap": "restart restart gap missed resume return setback checkin",
    "sleep": "sleep sleep irregular variation bedtime wind rest schedule",
    "short_sleep": "sleep sleep bedtime wind routine schedule",
    "stress": "stress stress high pause breathing rest quiet",
    "energy_up": "energy energy improving continue repeat manageable build",
    "movement": "movement movement activity active goal comfortable consistency",
    "review": "goals review adjust achieved achievable plan choose",
}
CANDIDATES = tuple(k for k, v in CARDS.items() if v["tags"])


def tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z]+", text.lower()))


def rank(query: str) -> tuple[str, float]:
    docs = {k: tokens(CARDS[k]["tags"]) for k in CANDIDATES}
    term_counts = Counter(t for v in docs.values() for t in v)
    idf = {t: log((1 + len(docs)) / (1 + f)) + 1 for t, f in term_counts.items()}

    def vector(counts: Counter[str]) -> dict[str, float]:
        return {t: (1 + log(n)) * idf[t] for t, n in counts.items() if t in idf}

    q = vector(tokens(query))
    qnorm = sqrt(sum(x * x for x in q.values()))
    if not qnorm:
        return "starter", 0.0
    scores = []
    for key, counts in docs.items():
        v = vector(counts)
        vn = sqrt(sum(x * x for x in v.values()))
        scores.append((sum(w * v.get(t, 0.0) for t, w in q.items()) / (qnorm * vn), key))
    value, key = sorted(scores, key=lambda s: (-s[0], s[1]))[0]
    return key, value


def result(key: str, kind: str, why: str) -> dict[str, Any]:
    card = {k: v for k, v in CARDS[key].items() if k != "tags"}
    return {"id": key, "kind": kind, "reason": REASONS[why], "reason_key": why, **card}


def suggest(entries: list[dict[str, Any]], today: date, active: int, goal: int, enabled: bool) -> dict[str, Any]:
    recent = [r for r in entries if 0 <= (today - date.fromisoformat(r["day"])).days <= 7]
    latest = recent[-1] if recent else None
    # This is a product safeguard for explicitly selected very-low energy. It
    # never assigns a condition, risk score, cause, or emergency classification.
    if latest and latest["energy"] == 1 and (today - date.fromisoformat(latest["day"])).days <= 2:
        return result("support", "support", "energy")
    if not enabled or not entries:
        return result("starter", "fallback", "starter")
    last = date.fromisoformat(entries[-1]["day"])
    sleep = [r["sleep_minutes"] for r in recent]
    if latest and (today - last).days <= 2 and (latest.get("stress") or 0) >= 75:
        reason = "stress"
    elif (today - last).days >= 3:
        reason = "gap"
    elif latest and len(sleep) >= 3 and latest["sleep_minutes"] + 60 <= sum(sleep[:-1]) / (len(sleep) - 1):
        reason = "short_sleep"
    elif len(sleep) >= 3 and max(sleep) - min(sleep) >= 75:
        reason = "sleep"
    elif len(recent) >= 2 and recent[-1]["energy"] > recent[-2]["energy"]:
        reason = "energy_up"
    elif active < goal:
        reason = "movement"
    else:
        reason = "review"
    try:
        key, score = rank(TERMS[reason])
        if score < 0.18 or key not in CANDIDATES:
            return result("starter", "fallback", "starter")
        return result(key, "retrieval", reason)
    except Exception:
        # The fallback itself is static and does not depend on the ranker.
        return result("starter", "fallback", "starter")
