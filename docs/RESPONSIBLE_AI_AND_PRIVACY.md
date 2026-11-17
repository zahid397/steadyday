# Responsible AI, safety and privacy

**Purpose.** SteadyDay supports general routines for a fictional demo. It makes no diagnosis, risk prediction, treatment recommendation or claim of medical approval. The user can skip suggestions, alter goals, or leave the demo. No appearance rating, body-weight target, competition, streak reset or exercise-intensity prescription is used.

| Layer | Actual behavior |
| --- | --- |
| Ordinary rules | Validate fields and summarize recent fictional entries and chosen targets. Logging gaps, relatively short sleep, changes in sleep or energy, higher reported stress, and goal progress can influence the suggestion. |
| Retrieval personalization | Use TF–IDF and cosine similarity to match context to a prewritten card. Display the reason and source. The score measures text relevance. |
| Safety and fallback | A recent fictional selection of very low energy shows fixed general support information and withholds movement prompts. Missing history, disabled or failed retrieval, or a low match returns a fixed starter card. The safeguard applies even if retrieval is disabled. There is no LLM, model training or external AI request. |

## Evidence and content provenance

The profile seeds were hand-authored for demonstration in `server/steadyday/service.py`. They are neither real patient records nor statistically representative. The code labels example rows and user-entered **practice** rows separately. The following sources inform the general-language cards; they do not validate the prototype or its counting rules:

- [CDC: About Sleep](https://www.cdc.gov/sleep/about/index.html) — regular sleep routines and sleep habits.
- [WHO: Physical activity](https://www.who.int/initiatives/behealthy/physical-activity/) — examples of movement, including walking and wheeling.
- [NHS: Tiredness and fatigue](https://www.nhs.uk/symptoms/tiredness-and-fatigue/) — general guidance on discussing persistent or disruptive tiredness with a health professional. It is used as background guidance, not a Bangladesh referral pathway. The interface does not assess urgency.

The gap rule, sleep variation trigger, 10-minute activity count and score cutoff are demo design choices. They are not health thresholds. The interface wording and prompts should be reviewed for accessibility and suitability by an appropriate health-domain reviewer before use beyond the demo.

## Data handling

- Opt-in asks users to confirm they are adults and will enter only fictional values. A fictional display name, goal and habit labels, and optional check-in notes can be stored. The app has no email, phone, address, precise location or diagnosis fields. Enter fictional text and values in the demo.
- Habit completions store the habit identifier and date. Language, appearance and reminder settings are saved to the fictional session. The browser also remembers the selected language and appearance before onboarding.
- The browser stores an opaque HttpOnly session cookie. The database stores a token hash, not the token. The hosted origin uses a Secure cookie and server-only upstream credentials. The prototype has no tracking tags; hosting providers may still keep operational request logs.
- In the split hosted setup, the Next.js server calls FastAPI with a shared credential. API writes from the browser must match the configured origin. Reads and writes are scoped to the session, API responses disable caching, and validation errors omit submitted values.
- Default access expires after seven days. Expired records are purged on later onboarding or by an operator running the cleanup command. If there is no cleanup or new onboarding, rows can remain in storage after access has expired. Export omits credentials; confirmed deletion removes session-linked rows from the live demo store. Hosting backups or retained local exports are separate and are not erased by the demo.
- Reminders display while the app is open. The optional browser notification uses the browser's permission and may be unavailable on some devices. There is no background delivery, email, SMS or external AI service.
- Demo data is stored as ordinary database records and can be read by operators with database access. Cloud backups and log retention depend on the hosting configuration. The app requests fictional values and cannot verify that the text entered is fictional.

## Failure cases and future validation

A few logged entries may be misleading; the chart distinguishes missing days from zero, and suggestions never override the user's judgment. A slow or unreachable API shows a retry/error state; it does not silently queue or fake a save. The demo does not detect crises, account for medical conditions or verify that a visitor entered fictional values. Before a real pilot, confirm rights and governance, review the interface copy and accessibility, define referral boundaries with qualified local expertise, and decide on consent, oversight and retention. Evaluate comprehension and opt-out, return after a gap, check-in persistence and chosen-goal completion; report only observed results.
