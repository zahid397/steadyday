# Copy-ready draft for portal fields

Use this text after you confirm the registered statement and required fields. Add verified links only.

**Product:** SteadyDay — a wellbeing prototype.

**Problem and approach:** When a week gets busy, a routine can be hard to resume. SteadyDay helps men in Bangladesh use a short sleep, movement and energy check-in, see recent patterns and select a weekly target. After a gap it offers a manageable next step and explains why, while preserving history.

**Provisional Wellbeing alignment:** Challenge 09, Sustaining Healthy Behaviors. The prototype supports goal adjustment, recovery after gaps, understandable guidance and the freedom to ignore a suggestion. A sustained benefit is a pilot hypothesis, not a result.

**Technology:** A FastAPI/Pydantic service stores isolated demo sessions in a local SQLite file. The Docker setup uses PostgreSQL. The optional hosted profile includes a Next.js same-origin proxy. Local rules extract routine context; TF–IDF text retrieval ranks a small card library. A static fallback covers unavailable retrieval.

**Safety and evidence:** Two hand-authored fictional profiles, no contact details and no external AI requests. The app does not diagnose, treat or assess urgency. A fixed support path withholds activity suggestions when fictional energy is very low. Eighteen API, safety and configuration tests and three proxy tests passed; manual Chromium checks verified the main journey. Container startup, hosted integration and real-world validation are pending.

**Pilot and scale:** First verify hosted reliability, accessibility and safety. Then seek an opt-in community or workplace pilot to assess comprehension, return after gaps and chosen-goal completion. A possible organizational buyer and support costs remain hypotheses. Android, wearables and clinical data are deferred.
