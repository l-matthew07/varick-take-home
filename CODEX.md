concise in speech, comprehensive in analysis.

## Project Context

Support Ticket System — a full-stack web app (backend API + frontend + PostgreSQL) where support agents submit tickets, the system auto-classifies and routes them via a rules engine, and team leads track SLA compliance. Containerized with `docker-compose`.

**Stack:** Backend (FastAPI/Express/Django), Frontend (React or equivalent), PostgreSQL, Docker.

**Core domain objects:** Ticket, Team, Routing Rule, Ticket History.

---

## 1. Read Before Writing

- NEVER implement a solution without first reading all relevant existing code
- When building a new flow, find the existing flow that does something similar and follow its patterns exactly
- Don't reinvent the wheel — search for how the codebase already solves similar problems
- When you see an error or problem, read the related code thoroughly before proposing fixes

## 2. No Hacks in Production Code

- Never use type casts like `as unknown as X` to bypass type errors — they indicate you don't understand the data model
- Never create migrations or schema changes as a first resort — understand why the schema is designed that way
- If you're fighting the type system, you're probably doing something wrong
- Think through deployment order and race conditions before writing code
- Status transitions are `open → in_progress → resolved → closed` — enforce them at the model/service layer, not just the UI

## 3. Keep UI Simple

- No emojis unless explicitly requested
- No flashy colors (especially green "success" colors) unless explicitly requested
- Exception: priority badges (P1 red, P2 orange, P3 yellow, P4 gray) and SLA indicators (green/yellow/red) are spec requirements — use them
- When in doubt, keep it simple — inline text over fancy badges, plain styles over decorated ones
- Don't over-design. If the user asks for X, give them X, not X with extra flourishes

## 4. Think Before Coding

- When asked to implement something significant, pause and plan first
- Ask yourself: "Is this production-ready? What could go wrong?"
- Consider: deployment order, race conditions, data integrity, existing patterns
- Don't be eager to write code — understanding the problem fully comes first

## 5. Treat Code Seriously

- This is production code that real users depend on
- Every change should be thoughtful, not reactive
- When you make a mistake, don't patch it with another hack — step back and do it right

## 6. Code Quality Standards

- Clear separation of concerns — routes, services, models, and utils in distinct layers
- Consistent style and naming across the entire codebase
- Proper error handling — never swallow errors silently, return meaningful HTTP status codes and messages
- No security anti-patterns: no SQL injection (use parameterized queries/ORM), no plaintext passwords (hash with bcrypt or equivalent), no missing auth on protected routes

## 7. Domain Rules (Do Not Violate)

- **Routing engine:** Evaluate rules in `priority_order` (ascending). First match wins. If no match, apply default catch-all (→ Account Management, P3).
- **Auto-priority override:** If a routing rule specifies `auto_priority`, it replaces the ticket's submitted priority.
- **SLA deadlines:** Calculated from `created_at` using the *final* (possibly overridden) priority: P1 = 5min, P2 = 1hr, P3 = 24hr, P4 = 48hr.
- **SLA status:** `on_track` (> 20% time remaining), `at_risk` (≤ 20% remaining), `breached` (past deadline and still unassigned).
- **Ticket history:** Append-only. Every state change (`created`, `classified`, `assigned`, `status_changed`, `escalated`, `resolved`) must be logged with `old_value`, `new_value`, `changed_by`, and `timestamp`.
- **Auth:** JWT-based, two roles — `agent` and `team_lead`. Metrics dashboard is team-lead-only.

## 8. API Surface (Reference)

| Method | Endpoint | Notes |
|--------|-------------------------------|-------|
| POST   | `/api/auth/login`             | Returns JWT |
| GET    | `/api/auth/me`                | Current user info |
| POST   | `/api/tickets`                | Create + auto-route + SLA + history |
| GET    | `/api/tickets`                | List with filters (`status`, `priority`, `category`, `assigned_team`) + pagination |
| GET    | `/api/tickets/{id}`           | Detail with full history |
| PUT    | `/api/tickets/{id}`           | Update status/agent/team — enforce transitions |
| GET    | `/api/tickets/sla-breaches`   | Unassigned tickets past deadline |
| GET    | `/api/metrics`                | Counts by status/priority/team, breach count, avg resolution time |
| GET    | `/api/health`                 | `{"status": "healthy", "db": "connected", "timestamp": "..."}` |

## 9. Commands & Workflow

- `docker-compose up --build` must work on a fresh machine with zero manual steps
- Seed script auto-populates teams, users, routing rules, and 10+ sample tickets on first run
- Health check: `GET /api/health` → `{"status": "healthy", "db": "connected", "timestamp": "..."}`
- No hardcoded secrets — use environment variables
- Include Dockerfiles for backend and frontend separately
- PostgreSQL container must run the seed script automatically on first boot

## 10. Seed Data Checklist

- 4 teams: Engineering, Billing, Account Management, Security
- 2 users: `agent@example.com` (agent), `lead@example.com` (team_lead) — password `testpass123`
- 6 routing rules (see spec for exact conditions and priority_order)
- 10+ sample tickets covering: 2× P1 (one assigned, one SLA-breaching), 3+ different statuses, 2+ different teams, 1× catch-all default