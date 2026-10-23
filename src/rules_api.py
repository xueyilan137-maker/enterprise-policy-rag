"""Internal synthetic precheck service. A service token is not employee login."""
import os
import secrets
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from src.expense_rules import precheck

Money = Annotated[StrictStr, Field(pattern=r'^(?:0|[1-9]\d{0,11})\.\d{2}$')]


class ExpenseItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item_id: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    category: StrictStr
    amount: Money
    expense_date: StrictStr | None = None
    receipt_id: StrictStr | None = None
    receipt_present: StrictBool | None = None
    meal_provided: StrictBool | None = None
    check_in: StrictStr | None = None
    check_out: StrictStr | None = None
    nights: StrictInt | None = None
    route: StrictStr | None = None
    seat_class: StrictStr | None = None
    prior_approval_present: StrictBool | None = None


class TravelHeader(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: StrictStr | None = None
    destination: StrictStr | None = None
    destination_region: StrictStr | None = None
    trip_start_date: StrictStr | None = None
    trip_end_date: StrictStr | None = None
    submitted_date: StrictStr | None = None
    total_amount: Money


class TravelDetails(TravelHeader):
    expense_items: Annotated[list[ExpenseItem], Field(min_length=1, max_length=200)]


class Application(TravelDetails):
    employee_id: StrictStr
    employee_type: StrictStr | None = None


class Finding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str
    severity: Literal['needs_materials', 'needs_manual_review']
    item_ids: list[str]
    facts: dict[str, Any]
    clause_ids: list[str]


class Report(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str
    status: Literal['needs_materials', 'needs_manual_review', 'no_issues_found']
    is_precheck: Literal[True]
    policy_version: str | None
    rule_engine_version: str
    policy_snapshot_sha256: str
    findings: list[Finding]
    facts: dict[str, str | None]
    notice: str


def create_app(token=None):
    token = token or os.environ.get('RULES_API_TOKEN', '')
    if len(token) < 32:
        raise RuntimeError('Configure a service token of at least 32 characters')
    app = FastAPI(title='Synthetic expense precheck', version='0.1.0')

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # Never echo raw application data, token, or validator input in errors.
        return JSONResponse(status_code=422, content={'detail': 'Invalid structured application'})

    def authenticate(authorization: str | None = Header(default=None)):
        if not authorization or not secrets.compare_digest(authorization, 'Bearer '+token):
            raise HTTPException(401, 'Invalid service credential', headers={'WWW-Authenticate': 'Bearer'})

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'synthetic_demo'}

    @app.post('/v1/prechecks', response_model=Report, dependencies=[Depends(authenticate)])
    def check(application: Application):
        # Demo service-side identity binding; no caller-controlled employee history.
        if application.employee_id != 'DEMO-001':
            raise HTTPException(403, 'Employee outside demo credential scope')
        data = application.model_dump(exclude_none=True)
        data['employee_type'] = 'ordinary'
        try:
            result = precheck(data, previous_receipt_ids=())
        except ValueError:
            raise HTTPException(422, 'Invalid structured application') from None
        return Report(request_id=str(uuid4()), **result)

    return app
