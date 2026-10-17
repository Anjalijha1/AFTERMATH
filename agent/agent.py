import json

from .schemas import AgentResult
from .scenarios import SCENARIOS
from .prompts import SYSTEM_PROMPT
from .llm_client import get_llm_response


def run_agent(scenario_name):
    scenario = SCENARIOS[scenario_name]

    customer_data = {
        "customer_id": scenario["customer_id"],
        "refund_limit": scenario["refund_limit"],
        "requested_amount": scenario["requested_amount"]
    }

    raw_response = get_llm_response(
        SYSTEM_PROMPT,
        scenario["ticket"],
        customer_data
    )

    result = AgentResult.model_validate_json(raw_response)

    action = result.proposed_action

    if action.customer_id != scenario["customer_id"]:
        raise ValueError("Unexpected customer ID in model output")

    if action.amount != scenario["requested_amount"]:
        raise ValueError("Proposed amount does not match the ticket")

    if (
        action.amount > scenario["refund_limit"]
        and action.action != "deny_request"
    ):
        raise ValueError("Unsafe proposal: refund exceeds supplied limit")

    return result


if __name__ == "__main__":
    for name in SCENARIOS:
        print(f"\nScenario: {name}")

        try:
            result = run_agent(name)
            print(result.model_dump_json(indent=2))
        except Exception as error:
            print(f"Agent error: {error}")

