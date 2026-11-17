# SteadyDay narrated walkthrough — transcript

Actual browser captures with synthetic speech; no continuous screen capture.

## 1. Start where you are

SteadyDay helps men in Bangladesh track movement, sleep, and daily energy. It is designed for the moment a busy week interrupts a routine. The aim is to help people pick an achievable next step and see their own progress without a perfect streak. All the numbers in this walkthrough are fictional.

## 2. A check-in that saves

In the demo, choose a fictional profile and confirm that you will enter invented values only. Samir starts with a gap in his check-ins. SteadyDay suggests an easy return and preserves his earlier history. Here you can see a saved practice check-in on the dashboard. After changing movement to twenty five minutes and reloading, the same entry was returned from the database.

## 3. See the pattern

The dashboard shows the last fourteen days. Pick sleep, movement, or energy, and use the table to see the values behind the chart. Gaps stay visible, and are not counted as zero. The user decides how many days to aim for this week and can adjust the target as circumstances change. No goal is presented as a medical recommendation.

## 4. Show the safety boundary

Simple rules describe a logging gap or other context. A small local text retrieval component ranks fixed tips with sources and a reason. No external AI receives the entries. When very low energy is selected, the movement prompt is replaced by general support information. The demo does not diagnose a condition, predict risk, or determine urgency.

## 5. Keep control with the user

The optional reminder appears only inside the open dashboard. There is no email, text message, or push notification. The browser uses a private session with no account or email address. You can export the fictional history and delete the demo. The API tests verify session isolation, input validation, expiry, and removal of linked rows.

## 6. What we would test next

This walkthrough uses real browser captures from the tested local build. Before a real pilot, we would review the copy, accessibility, and health safeguards with qualified people. The first evaluation would measure whether participants understand prompts, return after a gap, and meet their own targets. No health outcomes have been measured. The release includes Docker Compose and local database settings. The container run still needs verification on a Docker enabled computer.
