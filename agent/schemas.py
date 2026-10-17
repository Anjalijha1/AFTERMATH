from typing import Literal
from pydantic import BaseModel, Field


class ProposedAction(BaseModel):
    action: Literal["issue_refund", "deny_request"]
    customer_id: str
    amount: float = Field(ge=0)
    reason: str


class AgentResult(BaseModel):
    proposed_action: ProposedAction
    explanation: str

