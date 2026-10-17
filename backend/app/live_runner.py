"""Live runner: agent proposal -> ArmorIQ authorization -> gated sandbox mutation.

Replaces MockRunner when AFTERMATH_RUNNER=live. Every mutation is gated by a
real ArmorIQ decision (or an explicit agent refusal); evidence records the real
provider ('armoriq' or 'agent'), never 'mock'. If ArmorIQ is unreachable or
unconfigured the run fails with an honest error instead of fake evidence.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from . import armoriq
from .models import RunInput, RunResult
from .runner import SCENARIOS
from .sandbox import CUSTOMER_ID, SEED_REFUND_LIMIT_MINOR, Sandbox

# The agent package lives at the repository root (Member 3 area).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from agent.agent import propose_action
except Exception:  # pragma: no cover - agent package must exist on this branch
    propose_action = None

Emit = Callable[[str, str, dict], None]
MAX_AMOUNT_MINOR = 10_000_000


class LiveRunner:
    """Real integration runner. No model output can claim authorization."""

    mode = 'live'
    scenario_lookup: Callable[[str], dict | None] | None = None

    def __init__(self, refund_limit_minor: int = SEED_REFUND_LIMIT_MINOR):
        Sandbox(refund_limit_minor).close()  # validates the value early
        self.refund_limit_minor = refund_limit_minor

    @property
    def real_armoriq(self) -> bool:
        return bool(armoriq.status()['available'])

    def execute(self, run_id: str, inputs: RunInput, emit: Emit) -> RunResult:
        if propose_action is None:
            raise RuntimeError('Agent package (agent/) could not be imported.')
        if self.scenario_lookup:
            scenario = self.scenario_lookup(inputs.scenario_id)
            if scenario is None:
                raise LookupError('Scenario no longer exists.')
        else:
            scenario = SCENARIOS[inputs.scenario_id]
        amount_default = inputs.amount_minor if inputs.amount_minor is not None else scenario['amount_minor']
        ticket = inputs.ticket if inputs.ticket is not None else scenario['ticket']
        sandbox = Sandbox(self.refund_limit_minor)
        try:
            return self._run(sandbox, inputs, scenario, amount_default, ticket, emit)
        finally:
            sandbox.close()

    def _run(self, sandbox, inputs, scenario, amount_default, ticket, emit) -> RunResult:
        action = scenario['action']
        before = sandbox.snapshot()
        limit_major = before['refund_limit_minor'] / 100
        emit('run_started', 'Started isolated synthetic sandbox (live runner).',
             {'execution_mode': 'live'})
        emit('tool_read', 'read_ticket returned synthetic data.',
             {'tool': 'read_ticket', 'ticket': ticket})
        emit('tool_read', 'lookup_customer returned synthetic data.',
             {'tool': 'lookup_customer', 'customer': before})

        result, source = propose_action(ticket=ticket, customer_id=CUSTOMER_ID,
                                        refund_limit=limit_major)
        proposed = result.proposed_action

        if action == 'issue_refund':
            if proposed.action == 'issue_refund' and proposed.amount > 0:
                amount_minor = round(proposed.amount * 100)
            else:
                amount_minor = amount_default
            if not (0 < amount_minor <= MAX_AMOUNT_MINOR):
                amount_minor = amount_default
        else:
            amount_minor = None

        emit('action_proposed', f'Agent proposal (source: {source}). A proposal is not an authorization.',
             {'action': action, 'customer_id': CUSTOMER_ID, 'amount_minor': amount_minor,
              'proposal_source': source, 'agent_action': proposed.action,
              'agent_reason': proposed.reason, 'explanation': result.explanation})

        if proposed.action == 'deny_request' or action != 'issue_refund':
            # Agent-layer refusal (or a non-refund action the agent will not touch):
            # an explicit, honestly labeled block without ArmorIQ involvement.
            decision = 'blocked'
            provider = 'agent'
            reason = ('Agent declined the request at the proposal layer.'
                      if proposed.action == 'deny_request'
                      else 'Agent only proposes refunds; non-refund actions are not attempted.')
            emit('policy_decision', 'Agent-layer refusal. No ArmorIQ decision was requested.',
                 {'provider': provider, 'decision': decision, 'reason': reason})
        else:
            auth = armoriq.authorize(tool_name='issue_refund_tool', customer_id=CUSTOMER_ID,
                                     amount_major=amount_minor / 100, limit_major=limit_major,
                                     user_prompt=ticket)
            if auth['decision'] == 'unknown':
                raise RuntimeError('ArmorIQ authorization unavailable: ' + '; '.join(auth['reasons']))
            decision = 'allowed' if auth['decision'] == 'allow' else 'blocked'
            provider = 'armoriq'
            reason = '; '.join(auth['reasons']) or auth['status']
            emit('policy_decision', f"ArmorIQ governance decision ({auth['status']}).",
                 {'provider': provider, 'decision': decision, 'reason': reason,
                  'evidence_id': auth['evidence_id'], 'evidence_verified': auth['evidence_verified'],
                  'status': auth['status']})

        if decision == 'allowed':
            refund_id = sandbox.issue_refund(amount_minor)
            emit('tool_executed', 'issue_refund executed after a verified ArmorIQ allow.',
                 {'tool': 'issue_refund', 'amount_minor': amount_minor, 'refund_row_id': refund_id})
        else:
            emit('tool_blocked', 'Tool was not executed; sandbox state unchanged.',
                 {'tool': action})

        after = sandbox.snapshot()
        emit('state_verified', 'Captured before/after sandbox state.',
             {'state_before': before, 'state_after': after, 'state_mutated': before != after})
        return RunResult(action=action, decision=decision, reason=reason,
                         amount_minor=amount_minor if action == 'issue_refund' else None,
                         state_before=before, state_after=after, state_mutated=before != after,
                         execution_mode='live')
