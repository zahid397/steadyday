# Early review and final submission checklist

**Project:** SteadyDay · **Focus:** Wellbeing · **Working team name:** Team Antibiotics (not verified against the account).

## Organizer evidence

- [Hack2skill challenge page](https://hack2skill.com/event/futurehealthchallenge/) — public Wellbeing focus includes Challenge 09, **Sustaining Healthy Behaviors**: “How might we help people start, maintain and recover healthier behaviors through support that adapts to their goals, circumstances, motivation and setbacks over time?” The MVP addresses feasible actions, recovery without a reset, explanations and user control. Sustained benefit has not been tested.
- The organizer's registration confirmation establishes registration, not eligibility or the selected challenge. Organizer emails identify **15 November 2026** for early review and **20 November 2026** for final submission; early review is optional feedback and not final scoring. The applicable cutoff hours/timezone, portal edit/replace behavior and Wellbeing AMA time have not been verified. The app calendar uses Dhaka time; it says nothing about the portal cutoff.
- The public event page permits international participation, teams of one to five, and requires leads and award recipients to be at least 18 by the submission deadline. Confirm each applicable eligibility and conflict condition, team role, and submission rights in the [official terms](https://hack2skill.com/event/futurehealthchallenge/tnc) and dashboard. No exception is assumed. Confirm the exact registered Wellbeing statement before treating alignment as final; this project is not for the separate fertility statement.
- The organizer requests a working prototype and technical notes covering assumptions, dependencies and limitations. The public FAQ says the organizer does not supply datasets. Our sample values are generated locally; disclose them and ask whether synthetic demonstration is accepted. Do not submit any real participant data.

## Deliverables

| Item | Current state |
| --- | --- |
| Working source | Complete local source and instructions in this archive. No remote GitHub repository/push verified. |
| Local frontend and API | Demonstrated. Open `http://127.0.0.1:8000/` after starting the README commands. Local URL is not a shareable hosted link. |
| Docker Compose | Built and ran on Windows with PostgreSQL. See [verification](VERIFICATION.md) for the base-image mirror and test results. |
| Hosted Next.js, Render API and PostgreSQL | The Next.js production build was exercised locally. Connect the repository, provision PostgreSQL, add server settings and run the public HTTPS checks in [deployment](DEPLOYMENT.md). Public URLs are pending. |
| Requirements and architecture | [Concept](CONCEPT.md), [architecture/API](ARCHITECTURE.md), [deployment](DEPLOYMENT.md), [responsible AI](RESPONSIBLE_AI.md). |
| Demo and pitch | [Walkthrough script](DEMO_SCRIPT.md), [pitch](PITCH.md), and actual Chromium captures in `evidence/`. Companion presentation and narrated browser-capture walkthrough provided with the release. |
| QA | [Verification](VERIFICATION.md) and sanitized logs/captures. Retest the deployed stack if using a hosted link. |
| AMA | [Five unanswered questions](AMA.md) ready to paste in the [official advance form](https://forms.gle/bxx4oaXgs2Mit3LR7). Not sent. |
| Portal | No early-review or final submission made. |

## Before 15 November early review

1. Check the dashboard team name, lead role, team size, challenge statement, exact time/timezone and early-review fields. Confirm eligibility and organizer terms directly.
2. Open the source archive from a clean folder. Run it, rehearse Samir, and check the assets. If the form needs a shareable URL, deploy first or confirm that a reproducible local demo/video is accepted.
3. Enter accurate facts and synthetic-data disclosure. If the owner decides to submit early, record the organizer's confirmation without exposing account details.

## Before 20 November final

1. Apply only verified reviewer/AMA feedback. Confirm whether replacing the earlier upload is allowed; use the portal's actual deadline timezone.
2. Verify links from a clean browser and test the same released commit, APIs, database and reviewer access. Never put the demo code or service secrets in public files.
3. Submit through the organizer's workflow, then retain the receipt and final artifact version. No health impact, pilot, partner or deployment should be reported without evidence.
