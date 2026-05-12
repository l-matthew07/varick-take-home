# Support Ticket System — Plan

## Stack

- **Backend:** FastAPI + Python
- **Frontend:** Next.js 14 App Router + TypeScript + Tailwind
- **Database:** PostgreSQL via SQLAlchemy ORM
- **Auth:** JWT (role claim: `agent` | `lead`), bcrypt via passlib
- **Infra:** docker-compose, three services (db, backend, frontend)

## Data Model

Just copy from spec. One deliberate deviation: `RoutingRule` gets three optional extra columns: `secondary_condition_field`, `secondary_condition_operator`, `secondary_condition_value` to handle compound rules like "category = billing AND priority in [P1, P2]" without a separate conditions table or a DSL. Keeps everything flat and queryable.

## Environment Variables

`.env.example`:

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme
POSTGRES_DB=tickets
DATABASE_URL=postgresql://postgres:changeme@db:5432/tickets
SECRET_KEY=changeme
ALGORITHM=HS256
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Routing Engine

`services/routing.py`
**Logic:**
1. Load all `RoutingRule` rows ordered by `priority_order ASC`
2. For each rule, pull the ticket's value for `condition_field`
3. Evaluate operator: `equals` = exact match, `contains` = substring, `in` = JSON array membership
4. If a secondary condition exists, both must pass
5. First full match wins → return `(target_team, auto_priority, rule_name)`
6. No match → return the catch-all rule (seeded as `priority_order = 6`, not hardcoded)

**On ticket creation:**
1. Insert ticket (`status = open`)
2. Log `created` → TicketHistory
3. Run routing engine
4. Set `assigned_team`; log `classified` and `assigned`
5. If `auto_priority` differs from submitted priority, override and log it
6. `sla_deadline = created_at + SLA_WINDOWS[final_priority]`
7. Commit, return routing result to caller

The catch-all is a real seeded row, not an implicit fallback in code — so it shows up if someone queries the RoutingRule table.

## SLA

Computed at read time, never stored as a column.

```
assigned_agent is not null  → on_track (already assigned, SLA met)
now > sla_deadline          → breached
remaining / total <= 0.20   → at_risk
else                        → on_track
```

SLA windows: P1 = 5min, P2 = 1hr, P3 = 24hr, P4 = 48hr.

Breach query: `sla_deadline < now AND assigned_agent IS NULL AND status NOT IN ('resolved', 'closed')`.

## Status Transitions

Enforced at the service layer via a transition map — not just the UI:

```
open        → [in_progress]
in_progress → [resolved]
resolved    → [closed, in_progress]   # reopen path
closed      → []                      # terminal
```

Invalid transition returns 400 with the list of allowed next states. Every transition logs to TicketHistory.

## Auth

- `POST /api/auth/login` → JWT with `sub=email`, `role` in payload
- `get_current_user` dependency decodes token and returns user on every protected route
- `require_role("lead")` dependency on `/api/metrics` — agents get 403 at the API level, not just a frontend redirect
- Token stored in localStorage on the frontend, attached as Bearer header, redirect to /login on 401

Note: localStorage is XSS-vulnerable vs HttpOnly cookies. Acceptable tradeoff for this scope — would switch to cookies in production.

## Frontend Pages

**Login** email/password, store JWT, redirect to /dashboard.

**Dashboard** table: Title, Priority (badge), Category, Team, Status, Created, SLA Status (dot). Filters: status, priority, team. Click row → detail.

**Ticket Detail** info + action buttons by status:
- Open: "Start Working", "Assign to Me"
- In Progress: "Resolve"
- Resolved: "Close", "Reopen"
- Closed: nothing

History timeline below, chronological.

**Submit** title, description, channel, category, priority. After submit, show routing result: team, final priority, SLA deadline, rule that matched.

**Metrics** (lead only — redirect agents) — summary cards (open, in-progress, SLA breaches, avg resolution time), tickets-by-team as a table, SLA breach list with elapsed time.

## Containerization

```yaml
services:
  db:        # postgres:16-alpine, pg_isready healthcheck
  backend:   # python:3.12-slim, depends_on db (service_healthy), runs start.sh
  frontend:  # node:20-alpine, multi-stage build, depends_on backend
```

`start.sh` polls until postgres accepts connections, runs `seed.py`, starts uvicorn.

Seed is idempotent per-table (not just `Team.count() > 0`), wrapped in a transaction so a mid-seed crash doesn't leave partial state.

## Seed Data

- 4 teams
- 2 users (agent + lead, bcrypt passwords)
- 6 routing rules including the catch-all as an actual row
- 12 sample tickets — run through the real routing engine so assigned_team, priority overrides, SLA deadlines, and history all reflect actual behavior

## Tests

Focus on `services/routing.py`:
- `evaluate_condition` — equals/contains/in, match and no-match
- `route_ticket` — priority ordering, first-match-wins, compound condition, catch-all
- `compute_sla_status` — on_track, at_risk (within 20%), breached, assigned overrides breach

## Build Order

1. Models + DB setup
2. Seed script — verify data before touching the API
3. Routing engine — write and test standalone
4. Auth
5. API routes
6. Frontend
7. Docker + cold start verification
8. README + writeup