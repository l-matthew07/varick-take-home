# Support Ticket System

## Setup

```bash
cp .env.example .env
docker compose up --build
```

The backend will wait for PostgreSQL, run the seed script, and start. The frontend will be available at http://localhost:3000.

**Default credentials:**
- Agent: agent@example.com / testpass123
- Team Lead: lead@example.com / testpass123

## Architecture

**Backend:** FastAPI + SQLAlchemy + PostgreSQL. Three layers: routers handle HTTP, services contain business logic (routing engine, SLA computation), models define the schema. No business logic in routers.

**Frontend:** Next.js 14 App Router + TypeScript. Auth state lives in a context provider, all API calls go through a single fetch wrapper that handles token attachment and 401 redirects.

**Routing engine:** Lives in `backend/app/services/routing.py`. Evaluates rules in `priority_order` ascending, first match wins. Supports `equals`, `contains`, and `in` operators, plus compound AND conditions via a JSON `conditions` array on each rule (e.g. rule #2 requires `category = billing AND priority in [P1, P2]` — a flat `condition_field/value` schema can't represent this, so `conditions` is a JSON array of `{field, operator, value}` objects). Rule #6 is the "Default Catch-All" seeded as a real DB row with empty conditions (which match vacuously via `all([]) == True`), routing to Account Management at P3. A hardcoded code-level fallback exists as a safety net if the DB row is ever deleted.

**SLA status** is computed at read time on every ticket response and is never stored. It's set to `on_track` if assigned, `breached` if past deadline and unassigned, `at_risk` if within 20% of the window.

**Status transitions** are enforced at the service layer via a transition map. Invalid transitions return 400 with the list of allowed next states.

## Tradeoffs

- JWT stored in localStorage (XSS-vulnerable vs HttpOnly cookies, acceptable for this scope)
- `NEXT_PUBLIC_API_URL` is baked into the frontend image at build time and changing it requires a frontend rebuild
- Next.js 14.2.0 has a known security advisory so I would upgrade in production
- Tests run against a real PostgreSQL container via `testcontainers`: one container is shared across the session, tables are truncated between tests

## Writeup

### How would you evolve this system from 500/day to 50,000/hour?

50,000/hour is ~14 tickets/second sustained, with spikes higher. The current design handles ticket creation synchronously — the routing engine runs inline on POST /tickets, which is fine at low volume but becomes a bottleneck under load.

The first change would be decoupling routing from the HTTP request. A message queue (SQS, Redis Streams) sits in front of the routing engine. The POST endpoint inserts the ticket and returns immediately with status `pending_routing`, a worker pool picks up the event and runs the engine asynchronously. This keeps p99 latency low for submitters even when routing is slow.

The database becomes the next bottleneck. Tickets are write-heavy on creation and read-heavy on the dashboard. Read replicas handle dashboard and list queries. The SLA breach query runs on a schedule (cron or a dedicated worker) rather than on every metrics request. The results would be cached in Redis with a short TTL.

At this scale the routing rules engine should be cached in memory on each worker and invalidated on rule changes, rather than querying the DB on every ticket. Rules change rarely but tickets arrive constantly.

For the frontend, the dashboard would move to cursor-based pagination and optimistic updates. SLA status would be pushed via WebSocket or SSE rather than computed on every poll.

### If the database went down for 30 seconds, what happens in your current design? What would you change?

In the current design, everything breaks. POST /tickets fails immediately, SQLAlchemy raises a connection error, and the ticket is lost. GET requests fail too. There's no buffering, no retry, no queue. The 30 seconds of downtime means 30 seconds of lost tickets with no recovery path.

The real fix is a write-ahead queue. Incoming tickets get written to a durable queue (Redis with AOF persistence, or SQS) before touching the database. The queue acts as a buffer, and during the outage, tickets accumulate. When the DB recovers, the worker drains the queue in order. Submitters get a 202 Accepted with a ticket ID immediately, and the ticket appears in the dashboard once processed.

For reads, a short Redis cache on list/detail endpoints means the dashboard stays partially functional during a DB outage — stale data is better than an error page for support agents mid-shift.

The harder problem is SLA deadlines. If a P1 ticket is queued for 30 seconds before being written, its `created_at` should reflect when it was submitted, not when it was persisted. The queue message needs to carry the original submission timestamp.