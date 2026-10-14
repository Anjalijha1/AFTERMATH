# AFTERMATH backend (Member 1)

FastAPI + SQLite service for the AFTERMATH / OpsDesk synthetic demo.
Backend only. Existing `../agent/` teammate files are unchanged.

## What is ready

- `POST /runs` starts asynchronous execution and returns HTTP 202 with a run ID.
- `GET /runs/{run_id}` returns queued/running/completed/failed status, result,
  timestamps, structured evidence and a safe error when execution fails.
- Runs and evidence survive restarts in SQLite. A run interrupted by a restart
  is marked failed instead of silently stuck or repeating a mutation.
- Strict bounded inputs, API errors, optional API-key gate, restricted CORS,
  idempotency keys, bounded active-run queue and concurrent isolated demos.
- Deterministic mock scenarios show allowed and blocked actions. A blocked
  run records a regression fixture; replay independently checks the expected
  blocked decision and unchanged state. A changed outcome reports a failed
  regression, separate from execution failure.

**This is NOT a real ArmorIQ integration, MCP server or LLM agent.** There are
no external refunds or account changes. Mock evidence is labeled in API
responses. This alone does not satisfy the hackathon's real integration proof.

## Run locally

Python 3.10 or newer. From this repository:

```sh
cd backend
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation,
`/openapi.json` for the API schema, `/health` for health status.

The DB is automatically initialized at `backend/data/aftermath.db` when run
from `backend/`. Data and secrets are gitignored inside this folder. Do not
commit real credentials or customer data. The default is a local synthetic
sandbox, not a public production service.

### Configuration

Environment variables are read from the process. `.env.example` is a reference;
files named `.env` are **not loaded automatically** (especially the team root
`.env`). Set variables in your shell or hosting environment before startup:

| Variable | Default | Meaning |
| --- | --- | --- |
| `AFTERMATH_DB_PATH` | `./data/aftermath.db` | File-backed SQLite DB, writable directory |
| `AFTERMATH_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated exact frontend origins |
| `AFTERMATH_API_KEY` | empty | If nonempty, require `X-API-Key` except for health and CORS preflight |

For example on macOS/Linux:

```sh
export AFTERMATH_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Only one API process / uvicorn worker may use this DB. Startup recovery assumes
it owns the active-run lifecycle. Do not run multi-worker/multi-instance until
ownership leases and a durable worker queue are implemented. Use persistent
disk if deploying; no deployment is included here. Back up the DB when needed.
Keep local-only unless access control is set. An API key in a browser bundle
is not per-user authentication: public multi-user deployment needs real auth,
authorization, rate limits and tenant isolation before it is safe.

## Frontend API contract

All money uses integer **INR minor units (paise)**: `50000` means INR 500,
`100000` means INR 1000. Never send `500` expecting INR 500.

### Start a run

```sh
curl -s -X POST http://127.0.0.1:8000/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-refund-001' \
  -d '{"scenario_id":"allowed_refund"}'
```

Response shape (ID is an example):

```json
{
  "run_id": "b2ba9b62-e4c1-4d2e-9507-a52b3dcde840",
  "status": "queued",
  "status_url": "/runs/b2ba9b62-e4c1-4d2e-9507-a52b3dcde840",
  "execution_mode": "mock"
}
```

The initial status can already be running or completed if execution is fast.
Poll the returned relative `status_url` against your backend URL until status
is `completed` or `failed` (e.g. every 0.5-1 seconds during an active demo).

Allowed request properties:

| Property | Requirement |
| --- | --- |
| `scenario_id` | Required, one of the four IDs below |
| `amount_minor` | Optional integer 0-10000000, or null for scenario default |
| `ticket` | Optional string 1-4000 characters, or null for scenario default |

Unknown properties are rejected. Amount strings, booleans, negatives and
fractions are rejected. Zero is a valid test input but the mock policy blocks
it. Ticket text is captured as synthetic evidence only; it does not select
amounts/actions or invoke an LLM. Do not enter real personal data or secrets.

`Idempotency-Key` is optional, 1-128 characters `[A-Za-z0-9._:-]`. The same
key with the same parsed inputs returns the existing run, including after
restart. A different input/replay using that key returns 409. Reuse cannot
restart a failed run: submit a new key for a new attempt. Keys have no expiry
in this prototype, so clients should generate a unique key per intended run.

### Run detail

`GET /runs/{run_id}` returns:

- `run_id`, `status`, `execution_mode`, original `input`.
- UTC ISO timestamps: `created_at`, `started_at`, `finished_at` (null until reached).
- `result` null until completion; otherwise `action`, `decision`, `reason`,
  `amount_minor`, `currency`, `state_before`, `state_after`, `state_mutated`.
- `regression_id` on a new blocked run; `replay_of` and `regression_passed`
  on a replay. These result fields are null when not applicable.
- `error` null except on failed execution: `{code, message}`. Stack traces
  and secrets are not exposed to the API. Server logs use run IDs for diagnosis.
- `evidence[]`: ordered `{sequence, timestamp, kind, message, data}` events.

The result decision is independent of run lifecycle status. `completed` can
mean the action was blocked correctly. It can also mean a regression replay
completed but its security expectation failed (`regression_passed: false`).

```js
const backend = 'http://127.0.0.1:8000';
const res = await fetch(`${backend}/runs`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID()},
  body: JSON.stringify({scenario_id: 'injection_refund'})
});
const accepted = await res.json();
if (!res.ok) throw new Error(accepted.error?.message ?? 'Could not start run');
const detail = await fetch(`${backend}${accepted.status_url}`).then(r => r.json());
// Poll until terminal, then render detail.result and detail.evidence.
// Add X-API-Key to every request only if your backend is configured to require it.
```

### Other endpoints

| Endpoint | Result |
| --- | --- |
| `GET /health` | Status, mock mode, `real_armoriq: false` |
| `GET /scenarios` | Scenario picker data |
| `GET /runs?limit=20&offset=0` | Paginated summaries and total |
| `GET /runs/{run_id}/evidence` | Same evidence as run detail, for timeline |
| `GET /regressions?limit=20&offset=0` | Persisted blocked-run fixtures and total |
| `GET /regressions/{regression_id}` | Fixture, source run, input and expectations |
| `POST /regressions/{regression_id}/replay` | HTTP 202, new run from stored inputs; supports idempotency header |

Limits are 1-100, offsets 0-100000, ordered newest first. Offset pagination is
suitable for this small demo, not a stable cursor under concurrent inserts.

### Scenarios

| ID | Default action | Default mock outcome |
| --- | --- | --- |
| `allowed_refund` | Refund INR 500 | allowed |
| `excessive_refund` | Refund INR 5000 | blocked |
| `injection_refund` | Propose hidden injected INR 50000 refund | blocked |
| `account_email_change` | Propose unauthorized account change | blocked |

The first two IDs match `../agent/scenerios.py` as currently committed. The
injection scenario deliberately proposes the bad amount so the mock gate is
exercised. This is not evidence of real prompt-injection resistance.
Each run starts with a fresh isolated customer sandbox. Allowed refunds
change only that run's returned state. Blocked actions never mutate that
state, and the backend independently rejects a runner that claims blocked
but changes before/after state. There is no shared business customer ledger.

### Errors

HTTP 422 validation, 404 missing run/fixture, 409 conflicting idempotency key,
401 missing/wrong API key when enabled, 413 body over 64 KiB, 429 over 100
active runs, 503 worker unavailable. Errors use `{ "error": { "code": "...",
"message": "..." } }`, with safe field details for validation errors. Worker
failures use run status `failed` and safe `RUN_FAILED` errors in GET results.
Unknown routes use FastAPI's standard 404 shape. Infrastructure/storage
errors are not disguised as successful runs.

## Teammate integration seam

`app/runner.py` defines `Runner.execute(run_id, inputs, emit) -> RunResult`.
`create_app(..., runner=your_runner)` injects an adapter for integration tests.
The service owns scheduling, persistence, status and regression evaluation;
the adapter owns interpretation, policy-gated tools and external execution.
Do not invoke a teammate file blindly: the current agent is a scaffold,
`ProposedAction.amount` is a float in rupees, and `deny_request` is a proposal,
not an ArmorIQ blocked decision. Add explicit validated unit conversion and
map the agent result to a real policy/MCP execution flow when it is ready.

Before replacing the mock for a real demo:

1. Member 3 supplies the real LLM structured proposal. Never treat its claims
   as authorization or allow it to determine security test pass/fail.
2. Member 4 supplies real ArmorIQ policy checks and an onboarded real MCP
   server. Authorize immediately before every mutation. Capture actual
   provider decisions/trace IDs and verified before/after tool state.
3. Keep business sandbox state under the tool owner's transaction. The
   backend's snapshot invariant is an extra check, not a rollback mechanism
   for an external mutation. Never send production money/customer records.
4. Replace hardcoded `execution_mode: mock`/`real_armoriq: false` only after
   integration is implemented and proven. Real result/provider types must
   be added to the response models; injecting a runner alone is not enough.
5. Add end-to-end integration tests proving a real allowed call succeeds,
   a real denied call is not executed, denied state is unchanged, and replay
   remains verifiable. Store no raw credentials in evidence.

## Tests

```sh
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover endpoint acceptance, lifecycle, evidence order, policy boundaries,
invalid inputs, error hygiene, isolated concurrent runs, concurrent
idempotency, persistence, restart recovery, regression creation/replay,
changed behavior, blocked-state invariants, API-key/CORS and capacity limits.

## Limits / remaining team work

- No real ArmorIQ onboarding/keys/integration, MCP network server or LLM calls.
- No frontend work, deployment, video or submission assets.
- Single process, two worker threads, no distributed durable queue/cancellation.
- No user auth/roles/tenant model; API-key option is for controlled demos.
- Mock regression fixtures are useful backend plumbing, not hackathon proof.
- Python dependencies are pinned for this prototype; review/update before production.
