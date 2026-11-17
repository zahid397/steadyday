# SteadyDay — MVP specification

**Problem.** A disrupted routine can make general fitness advice feel impractical. Men who want to track movement, sleep and daily energy need a simple way to choose achievable actions, see what they logged and restart after a gap without losing their history. The initial demo is in English.

**Provisional alignment.** Hack2skill publicly lists Wellbeing Challenge 09, “Sustaining Healthy Behaviors.” Its scope includes adaptive actions, support after lapses, understandable evidence, user autonomy and sustained outcomes. This is the closest public fit. Account-specific statement and team name are still unverified. SteadyDay does not address the separate fertility statement.

**Demo scope.** A visitor chooses one of two fictional adult personas and agrees to use only simulated data. The dashboard shows recent sleep, movement and self-rated energy. A check-in saves to the API for the current Dhaka date. The user can change their weekly movement/check-in targets, see progress, set an in-app reminder, export the demo and delete it. The movement-day definition is a demo counting convention, not a health target.

**Personalisation.** A transparent rules layer maps recent practice entries and chosen goals to nonclinical context tokens. TF-IDF retrieval ranks a small catalogue of source-linked tips. A deterministic fallback handles cold start or disabled retrieval. Low self-rated energy takes a fixed general-support path that suppresses activity prompts. A gap in logging suggests a gentle restart without resetting history. No model predicts health outcomes, and no data are sent to an AI service.

**Architecture.** Browser → same-origin demo API → FastAPI/Pydantic → scoped session and data service → SQL database. The Docker setup uses FastAPI with PostgreSQL and serves the UI from the app container. The verified Python fallback uses SQLite. An optional hosted profile adds a Next.js server and proxy. These paths share the same business logic and UI. See [Architecture](ARCHITECTURE.md).

**Pilot hypothesis.** People can understand why a routine prompt appears and resume after missed days. A future opt-in pilot would first review translations and safeguards, then measure return after a gap, repeated check-ins and self-selected goal completion over several weeks. No efficacy, partnership, patient data or clinical validation is claimed.
