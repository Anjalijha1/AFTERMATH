from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCENARIO_ID_PATTERN = r'^[a-z0-9_]{3,40}$'
ACTIONS = Literal['issue_refund', 'change_account_email']


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    scenario_id: str = Field(pattern=SCENARIO_ID_PATTERN)
    # All money is INR minor units, never float. None uses the scenario default.
    amount_minor: int | None = Field(default=None, ge=0, le=10_000_000)
    ticket: str | None = Field(default=None, min_length=1, max_length=4000)


    @field_validator('ticket')
    @classmethod
    def ticket_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('Ticket cannot contain only whitespace.')
        return value


class ScenarioIn(BaseModel):
    """A saved synthetic test scenario (design doc: POST /api/scenarios).

    expected_decision is what the developer expects the policy to do. The runner never
    reads it to decide anything; it is only compared with the actual decision later.
    """
    model_config = ConfigDict(extra='forbid', strict=True)
    scenario_id: str = Field(pattern=SCENARIO_ID_PATTERN)
    name: str = Field(min_length=1, max_length=80)
    action: ACTIONS
    amount_minor: int = Field(ge=0, le=10_000_000)
    ticket: str = Field(min_length=1, max_length=4000)
    expected_decision: Literal['allowed', 'blocked']

    @field_validator('name', 'ticket')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Must not be blank.')
        return value

    @model_validator(mode='after')
    def action_contract(self):
        if self.action == 'change_account_email' and self.amount_minor != 0:
            raise ValueError('Email change scenarios must use amount_minor 0.')
        if self.action == 'issue_refund' and self.amount_minor == 0:
            raise ValueError('Refund scenarios need a positive amount_minor.')
        return self


class RunAccepted(BaseModel):
    run_id: str
    status: Literal['queued', 'running', 'completed', 'failed']
    status_url: str
    execution_mode: Literal['mock'] = 'mock'


class Evidence(BaseModel):
    sequence: int
    timestamp: str
    kind: str
    # AFTERMATH design-doc event name (compat alias of kind). None when no doc name exists.
    event_type: str | None = None
    message: str
    data: dict


class RunResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['issue_refund', 'change_account_email']
    decision: Literal['allowed', 'blocked']
    reason: str = Field(min_length=1, max_length=1000)
    amount_minor: int | None = Field(ge=0, le=10_000_000)
    currency: Literal['INR'] = 'INR'
    state_before: dict
    state_after: dict
    state_mutated: bool
    execution_mode: Literal['mock'] = 'mock'
    regression_id: str | None = None
    replay_of: str | None = None
    regression_passed: bool | None = None


    @model_validator(mode='after')
    def valid_action_contract(self):
        if not self.reason.strip():
            raise ValueError('Result reason must not be blank')
        if self.action == 'issue_refund' and self.amount_minor is None:
            raise ValueError('Refund result requires an integer minor-unit amount')
        if self.action == 'change_account_email' and self.amount_minor is not None:
            raise ValueError('Email change result must not have a refund amount')
        return self


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
