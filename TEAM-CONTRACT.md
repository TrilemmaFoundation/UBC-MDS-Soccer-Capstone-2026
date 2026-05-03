# Teamwork Contract: DSCI 591 Capstone

**Project:** Delivering Elite European Football (Soccer) Analytics  
**Date:** April 26, 2026  
**Signed by:** Li Pu, Ngoc Minh Quan Hoang, Rabindranath Duran Pons, Teem Kwong

---

> This is a living document and may be revised throughout the capstone as the team re-evaluates its effectiveness.

## 1. Time Expectations
* Each team member is expected to contribute a maximum of 40 hours per week to the capstone project unless all members agree to extend this limit.
* If a member anticipates they cannot complete their assigned work within this timeframe, they must notify the team on Slack at least 24 hours before the Friday group seminar (2:00 PM) so the team can discuss redistributing work or adjusting expectations.
* All submissions must meet milestone criteria, including working scripts, tested functions, and proper grammar in written deliverables.

## 2. Meetings
* Meeting times were established during the initial team meeting on April 26, 2026. 
* Meetings will be held on campus unless otherwise specified 24 hours in advance, in which case they will be held on Zoom.
* Meetings will recur weekly until the last day of class (June 24, 2026).

| Day | Time | Purpose |
| :--- | :--- | :--- |
| Monday | 2:00 PM - 3:00 PM | Team meeting (planning, standup) |
| Friday | 12:30 PM - 1:30 PM | Team meeting (review, retro) |
| Friday | 1:30 PM - 2:00 PM| Mentor and partner meeting |

* All members are expected to attend every meeting. 
* If a member cannot attend, they must notify the team via Slack at least 24 hours before the meeting to discuss alternatives.

## 3. Communication
The team will use three communication channels, each with a distinct purpose:
* **Slack (students-only channel):** Primary tool for informal communication, quick questions, scheduling, and day-to-day coordination. Messages should be responded to within 24 hours.
* **GitHub Issues:** Primary tool for task tracking, ideas, suggestions, submitting work, and reviewing work. Issues should be self-contained and reference-worthy for future use.
* **In-person / Zoom meetings:** For synchronous discussion, design decisions, and sprint planning as outlined in the meeting schedule above.

## 4. Task Management
* The team will use GitHub Projects (Kanban board) linked to the main project repository.
* All tasks will be tracked as GitHub Issues with the following columns:
    * **Backlog:** Tasks identified but not yet scheduled
    * **To Do:** Tasks assigned for the current sprint/week
    * **In Progress:** Tasks actively being worked on
    * **In Review:** Tasks with open pull requests awaiting review
    * **Done:** Tasks completed and merged

## 5. Roles and Responsibilities
Each team member has a primary workstream. In addition, rotating weekly roles ensure shared ownership of project health.

### 5.1 Primary Workstreams
| Member | Role | Key Deliverables |
| :--- | :--- | :--- |
| **Quan** | DE + Pipeline Lead: ingestion, GCS, BigQuery, Dagster assets, dbt staging + seeds + tests, Databricks support | Pipeline infra, Dagster orchestration, staging layer, data quality, model artifact pipeline |
| **Teem** | Infra + dbt Lead: Docker Compose, CI/CD, dbt intermediate + marts + docs, Django app + API | DevOps, GCP VM, transformation logic, mart tables, dbt docs, Django app + Looker embed |
| **Rabin** | ML Lead + Documentation: match prediction, feature engineering, model evaluation, optional pressing/home advantage analysis, final report | Databricks env, XGBoost predictor, calibration, optional RQ analysis, README, report, demo video |
| **Li** | Dashboard + ML + Chatbot: Looker Studio, player clustering (Databricks), chatbot backend (Groq tool calling, guardrails) | 3 Looker Studio pages, cluster assignments, chatbot backend (tool calling, live BigQuery queries) |

### 5.2 Rotating Weekly Roles
The following roles rotate weekly among all four members:
* **Project Manager:** Runs meetings, tracks overall progress, escalates blockers.
* **Infrastructure Manager:** Ensures Docker, GCP, Dagster, and CI/CD are running smoothly.
* **Documentation Manager:** Ensures README, dbt docs, and code comments are up to date.
* **Test Manager:** Ensures dbt tests, unit tests, and integration tests pass before merges.

## 6. Code Reviews and Pull Requests
* All work must be submitted via pull request on the project GitHub repository.
* All teammates must be added as reviewers on every pull request.
* At least one approval is required before merging.
* Pull requests should be reviewed within 24 hours of creation.
* PRs should be small and focused. Avoid large monolithic PRs.
* All CI checks (dbt test, linting) must pass before merging.

## 7. Deadlines
* All individual tasks should be completed by 11:59 PM on Thursday to allow for team review and proofreading on Friday before submission.
* If a member anticipates missing a Thursday deadline, they must notify the team on Slack by Wednesday evening.

## 8. Contributions and Accountability
All members are expected to contribute meaningfully and consistently. If a team member cannot complete an assigned task:
* Notify the team on Slack as soon as possible (at least 24 hours before the Thursday deadline).
* Propose a plan: request help, suggest scope reduction, or offer to take on a different task.
* The team will discuss redistribution during the next meeting or asynchronously on Slack.

## 9. Breach of Contract
Failure to follow this contract will result in a three-step process:
1. **Step 1 (Written notice):** A Slack message outlining the specific violation and a reminder of the contract conditions.
2. **Step 2 (Meeting):** A team meeting to discuss the behavior. A written agreement to follow the contract is required from the member.
3. **Step 3 (Escalation):** The team will reach out to the mentor to address the issue.