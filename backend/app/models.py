from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

SCENARIO_IDS = Literal['allowed_refund', 'excessive_refund', 'injection_refund', 'account_email_change']


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    scenario_id: SCENARIO_IDS
    # All money is INR minor units, never float. None uses the scenario default.
    amount_minor: int | None = Field(default=None, ge=0, le=10_000_000)
    ticket: str | None = Field(default=None, min_length=1, max_length=4000)


    @field_validator('ticket')
    @classmethod
    def ticket_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('Ticket cannot contain only whitespace.')
        return value


class RunAccepted(BaseModel):
    run_id: str
    status: Literal['queued', 'running', 'completed', 'failed']
    status_url: str
    execution_mode: Literal['mock'] = 'mock'


class Evidence(BaseModel):
    sequence: int
    timestamp: str
    kind: str
    message: str
    data: dict


class RunResult(BaseModel):
    action: Literal['issue_refund', 'change_account_email']
    decision: Literal['allowed', 'blocked']
    reason: str
    amount_minor: int | None
    currency: Literal['INR'] = 'INR'
    state_before: dict
    state_after: dict
    state_mutated: bool
    execution_mode: Literal['mock'] = 'mock'
    regression_id: str | None = None
    replay_of: str | None = None
    regression_passed: bool | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class RunView(BaseModel):
    run_id: str
    status: Literal['queued', 'running', 'completed', 'failed']
    execution_mode: Literal['mock'] = 'mock'
    input: RunInput
    created_at: str
    started_at: str | None
    finished_at: str | None
    result: RunResult | None
    error: ErrorDetail | None
    evidence: list[Evidence]
