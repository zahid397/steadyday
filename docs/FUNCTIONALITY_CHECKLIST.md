# UI interaction checklist

The FastAPI and Next.js entry points share the browser implementation in `web/public/steadyday/app.js`. Browser results refer to the automated Chromium suite. Controls marked NOT TESTED were inspected in source and have no dedicated browser assertion.

| Control | Handler and expected result | Browser status |
| --- | --- | --- |
| Brand, footer privacy, header demo and privacy links | `data-route` calls `route()` and renders `/`, `/demo` or `/privacy`. | NOT TESTED individually |
| Try the fictional demo | `data-route` opens `/demo` and checks whether a session exists. | PASS |
| How it works, dashboard section shortcuts | Native anchors scroll to the corresponding section. | NOT TESTED individually |
| Skip to content | Native anchor targets `#main`. The link is the first Tab stop. | PASS for keyboard focus |
| Profile choices, consent and Start demo | `onboard` submits a session. The dashboard loads the selected profile and its fictional data. | PASS |
| Hosted review-code field | `onboard` submits the code when configuration requests it. | NOT TESTED in browser. API rejection and acceptance covered. |
| Sidebar and mobile navigation | All six app sections navigate to a dedicated URL and support direct reload. | PASS |
| Language and Appearance | `change` saves the session preference and updates the UI. | PASS for English/Bangla and light/dark. Device changes were inspected. |
| Check-in date | `change` shows an existing entry or a blank form for the selected date. | PASS |
| Check-in fields, sample values and Save/Update | The sample action fills the form. `check-form` validates and writes the chosen date. | PASS |
| Delete check-in, Cancel and Delete permanently | Native dialog confirms the day. `delete-checkin-form` deletes the record and reloads the dashboard data. | PASS for confirm. Cancel inspected. |
| Trend metric buttons and data table | Metric handler re-renders the chart. Native disclosure exposes the stored rows. | PASS for Movement and data table. Other metrics use the same handler. |
| Insights range | Sends a range query and displays saved activity and check-in measurements. | PASS for 30 days in Chromium. Other ranges covered by API tests. |
| Recommendation explanation and support link | Native disclosure opens the reason. `data-route` opens the support section of `/privacy`. | PASS |
| Recommendation source link | Internal source navigates to privacy details. External sources use standard HTTPS links. | NOT TESTED individually |
| Weekly target fields and Save goals | `goals-form` saves targets. Progress is recalculated from the check-ins. | PASS |
| Custom goals and habits | Add, edit, mark, unmark and delete named records. | PASS |
| Habit date and completion toggles | Date selector loads that day. `data-habit` writes completion and refreshes the count. | PASS for marking and reload. Day switch inspected and undo covered by API test. |
| Reminder time, Save reminder and Turn off | `reminder-form` and `reminder-off` update or clear the saved time. | PASS for saving and disabling |
| Profile name and notification preferences | Update the session profile. | PASS for saved values and reload. OS notification delivery NOT TESTED. |
| Breathing and mindfulness | Open the timer, choose duration, start, pause, resume, finish, reset and close. | PASS |
| Export demo JSON | `export` downloads the session’s fictional JSON. | PASS |
| Delete demo, Cancel/Escape and Delete permanently | Native dialog confirms deletion. `delete-form` deletes the session and returns to onboarding. | PASS for confirm and Escape. Cancel inspected. |
| Try again | `retry` reruns the route and fetches data again. | PASS |

The dashboard combines check-ins, the 14-day history and insights, weekly targets, habits and guidance. Current scope and release checks are in the [test report](TEST_REPORT.md).
