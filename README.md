# AFTERMATH + OpsDesk (Team Cosmic, Flow State 2026)

Back-office support agent whose every sensitive action is governed by **ArmorIQ**;
blocked actions become reusable regression tests that replay on every change.


## Live deployment

- Dashboard: https://aftermath-dashboard-cosmic.onrender.com
- API: https://aftermath-api-cosmic.onrender.com
- MCP server: https://aftermath-mcp-cosmic.onrender.com/mcp

- **Agent** (`agent/`): interprets a support ticket into a structured proposal
  (Gemini structured output when `GEMINI_API_KEY` is set; clearly labeled
  deterministic fallback otherwise). The agent never authorizes or executes.
- **Governance** (`backend/app/armoriq.py`): real ArmorIQ check via the official
  `armoriq-sdk` (capture plan -> intent token -> `invoke_with_policy`). A
  `PolicyBlockedException` is a genuine, verified denial with an evidence id.
- **Backend** (`backend/`): FastAPI + SQLite. Runs, evidence timeline,
  deterministic PASS/FAIL verdicts, regression capture + replay. Mock runner by
  default; `AFTERMATH_RUNNER=live` switches to the agent + ArmorIQ path.
- **MCP sandbox** (`app/`): synthetic support tools (`read_ticket`,
  `lookup_customer`, `issue_refund`) exposed as an MCP server; mutations require
  a verified ArmorIQ authorization record.
- **Frontend** (`aftermath-frontend/`): React + Vite dashboard. Demo data by
  default; set `VITE_DEMO_MODE=false` to read from the live backend.

## Quick start

```sh
cp .env.example .env    # fill ARMORIQ_API_KEY / GEMINI_API_KEY locally; .env is gitignored

# Backend (mock mode, no keys needed)
cd backend && pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000     # http://127.0.0.1:8000/docs

# Live mode (agent + real ArmorIQ)
pip install armoriq-sdk google-genai
export AFTERMATH_RUNNER=live ARMORIQ_API_KEY=... GEMINI_API_KEY=...

# Frontend
cd aftermath-frontend && npm install
VITE_DEMO_MODE=false npm run dev               # http://localhost:5173

# Tests: 150 backend + 39 sandbox
cd backend && pytest -q
```

## ArmorIQ policy and tool tiering (honest note)

ArmorIQ policies in the platform editor are tool-level (allow / hold / block); they have
no numeric amount condition. So the refund limit is expressed by **which tool is called**:

| Amount | Tool requested | ArmorIQ policy | Result |
| --- | --- | --- | --- |
| within the refund limit (e.g. INR 500) | `aftermath-mcp-cosmic.issue_refund_tool` | allow | ALLOW |
| above the limit (e.g. injected INR 50,000) | `aftermath-mcp-cosmic.issue_large_refund_tool` | block | BLOCK |

The live runner picks the tool from the amount and the limit. The MCP also caps amounts
itself (`issue_refund_tool` rejects amounts above `MCP_REFUND_CAP`). The amount threshold is
therefore enforced by tool tiering plus the MCP cap, not by a numeric ArmorIQ constraint.
ArmorIQ's proxy calls the MCP itself, so the server in `mcp_public/server.py` (streamable HTTP, /mcp) must be
reachable over public HTTPS and registered in the platform (`armoriq.yaml` / Inventory).

## Status (honest)

- Real ArmorIQ **deny** verified end-to-end through the live API (injection
  scenario: agent proposed the injected INR 50,000, ArmorIQ blocked it, verdict
  PASS, regression fixture created, evidence id recorded).
- Real ArmorIQ **allow** verified end-to-end: INR 500 refund -> `issue_refund_tool` -> ALLOWED_BY_ARMORIQ.
  Injected INR 50,000 -> `issue_large_refund_tool` -> BLOCKED_BY_ARMORIQ_POLICY; account email change ->
  `change_account_email_tool` -> blocked. Platform setup: MCP `aftermath-mcp-cosmic` registered in the
  workspace (public Render service) and policy `aftermath-mcp-cosmic-tiered` active. Rule tool names in the
  ArmorIQ policy must be qualified (`<mcp>.<tool>`) for them to match.
- Gemini path is implemented but untested live (no key yet); without it the
  agent's deterministic fallback is used and labeled in the evidence.
- Money is integer paise in the backend (`amount_minor`), major units in agent
  proposals; conversion happens once in the live runner.
