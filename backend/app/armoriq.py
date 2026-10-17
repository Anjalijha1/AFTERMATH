"""ArmorIQ authorization adapter for the live runner.

Ported from feat/member4-security-regression (Member 4) and adapted to the
Member 1 backend contract. Truthful boundary:
- With the official armoriq-sdk package AND ARMORIQ_API_KEY set, authorization
  goes through the real ArmorIQ governance flow (capture_plan -> intent token
  -> invoke_with_policy). A PolicyBlockedException is a genuine ArmorIQ denial
  and is returned as a verified deny.
- Without the SDK or key, authorize() returns decision 'unknown' with exactly
  what is missing. It never manufactures evidence.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from armoriq_sdk import (
        ArmorIQClient,
        ConfigurationException,
        IntentMismatchException,
        InvalidTokenException,
        InvokeOptions,
        MCPInvocationException,
        PolicyBlockedException,
        PolicyHoldException,
        TokenExpiredException,
    )
    ARMORIQ_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on local environment
    ARMORIQ_SDK_AVAILABLE = False

MCP_ID = os.getenv('AFTERMATH_ARMORIQ_MCP_ID', 'aftermath-mcp-public')
USER_EMAIL = os.getenv('AFTERMATH_ARMORIQ_USER_EMAIL', 'support@synthetic.local')


def status() -> dict[str, Any]:
    """Report whether a live ArmorIQ authorization is possible right now."""
    api_key = os.getenv('ARMORIQ_API_KEY', '').strip()
    configured = bool(api_key) and api_key != 'your_armoriq_api_key_here'
    missing: list[str] = []
    if not ARMORIQ_SDK_AVAILABLE:
        missing.append("ArmorIQ SDK ('pip install armoriq-sdk') is not installed")
    if not configured:
        missing.append('ARMORIQ_API_KEY environment variable is not set')
    return {
        'available': ARMORIQ_SDK_AVAILABLE and configured,
        'sdk_installed': ARMORIQ_SDK_AVAILABLE,
        'api_key_configured': configured,
        'missing': missing,
    }


def _client():
    config_path = os.getenv('AFTERMATH_ARMORIQ_CONFIG', '').strip()
    if config_path and os.path.isfile(config_path):
        return ArmorIQClient.from_config(config_path)
    return ArmorIQClient(api_key=os.getenv('ARMORIQ_API_KEY'))


def _unknown(status_code: str, reasons: list[str]) -> dict[str, Any]:
    return {'decision': 'unknown', 'evidence_verified': False, 'evidence_source': 'armoriq',
            'evidence_id': '', 'status': status_code, 'reasons': reasons, 'raw_evidence': {}}


def authorize(*, tool_name: str, customer_id: str, amount_major: float,
              limit_major: float, user_prompt: str = '') -> dict[str, Any]:
    """Ask ArmorIQ whether the planned tool call is allowed.

    Returns standardized evidence. decision is 'allow', 'deny' or 'unknown';
    only allow/deny carry verified ArmorIQ evidence.
    """
    if not status()['available']:
        return _unknown('UNAVAILABLE', status()['missing'])

    try:
        client = _client()
        plan = {
            'goal': f'Process refund request for customer {customer_id}',
            'steps': [{
                'action': tool_name,
                'mcp': MCP_ID,
                'params': {'customer_id': customer_id, 'amount': amount_major},
            }],
        }
        captured = client.capture_plan(
            llm='aftermath-eval',
            prompt=user_prompt or f'Refund of {amount_major:g} requested for customer {customer_id}',
            plan=plan,
            metadata={'customer_id': customer_id, 'amount_minor': round(amount_major * 100)},
        )
        token = client.get_intent_token(captured, validity_seconds=300)
        options = InvokeOptions(user_email=USER_EMAIL, requester_limit=limit_major,
                                wait_for_approval=False)
        result = client.invoke_with_policy(
            mcp=MCP_ID, action=tool_name, intent_token=token,
            params={'customer_id': customer_id, 'amount': amount_major}, options=options,
        )
        evidence_id = getattr(result, 'invocation_id', '') or getattr(token, 'token_id', '')
        return {
            'decision': 'allow', 'evidence_verified': True, 'evidence_source': 'armoriq',
            'evidence_id': str(evidence_id), 'status': 'ALLOWED_BY_ARMORIQ',
            'reasons': ['ArmorIQ policy authorized the requested tool call'],
            'raw_evidence': {
                'token_id': str(getattr(token, 'token_id', '')),
                'invocation_status': str(getattr(result, 'status', 'success')),
            },
        }
    except PolicyBlockedException as exc:
        evidence_id = getattr(token, 'token_id', '') if 'token' in locals() else ''
        return {
            'decision': 'deny', 'evidence_verified': True, 'evidence_source': 'armoriq',
            'evidence_id': str(evidence_id), 'status': 'BLOCKED_BY_ARMORIQ_POLICY',
            'reasons': [f'ArmorIQ policy denied the action: {exc}'],
            'raw_evidence': {'exception': 'PolicyBlockedException', 'reason': str(exc)[:500]},
        }
    except PolicyHoldException as exc:
        return {
            'decision': 'deny', 'evidence_verified': True, 'evidence_source': 'armoriq',
            'evidence_id': str(getattr(exc, 'delegation_id', '') or ''),
            'status': 'HELD_FOR_APPROVAL',
            'reasons': [f'ArmorIQ placed the action on hold: {exc}'],
            'raw_evidence': {'exception': 'PolicyHoldException', 'reason': str(exc)[:500]},
        }
    except ConfigurationException as exc:
        return _unknown('UNCONFIGURED', [f'ArmorIQ configuration error: {exc}'])
    except (InvalidTokenException, IntentMismatchException, TokenExpiredException) as exc:
        return _unknown('TOKEN_ERROR', [f'ArmorIQ token error: {exc}'])
    except MCPInvocationException as exc:
        return _unknown('MCP_ERROR', [f'ArmorIQ MCP invocation error: {exc}'])
    except Exception as exc:  # noqa: BLE001 - never crash the run loop silently
        return _unknown('ERROR', [f'ArmorIQ unexpected error: {type(exc).__name__}: {exc}'])
