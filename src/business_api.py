"""Local synthetic employee API, durable SQLite tasks, server-bound identities."""
import json
import hashlib
import re
import secrets
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.application_store import ApplicationStore, Conflict
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator
from src.rules_api import TravelDetails, TravelHeader
from src.material_parser import MAX_BYTES, parse_expense_csv
from src.narrative import EXTRACTOR_VERSION,parse_narrative,validate_candidate
from src.workflow_client import WorkflowClient, WorkflowCallError
from src.web_sessions import DemoSessions, DemoLogin, COOKIE, TTL
from src.policy_data import load_policy, render_clauses

ROOT = Path(__file__).resolve().parents[1]


class MaterialApplication(TravelHeader):
    material_id: Annotated[StrictStr,Field(min_length=1,max_length=100)]

    @field_validator('trip_start_date','trip_end_date','submitted_date')
    @classmethod
    def valid_date(cls,value):
        if value is not None:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('ISO date required')
            date.fromisoformat(value)
        return value


class ExtractionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    narrative_material_id: Annotated[StrictStr,Field(min_length=1,max_length=100)]
    csv_material_id: Annotated[StrictStr,Field(min_length=1,max_length=100)]


class ExtractedApplication(BaseModel):
    model_config=ConfigDict(extra='forbid')
    extraction_id: Annotated[StrictStr,Field(min_length=1,max_length=100)]


class ReviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision: Literal['reviewed','needs_materials','follow_up']
    note: Annotated[StrictStr,Field(min_length=5,max_length=2000)]

    @field_validator('note')
    @classmethod
    def meaningful_note(cls,value):
        if len(value.strip())<5:raise ValueError('Review note required')
        return value.strip()


def create_app(db_path=None, users=None, workflow=None):
    if users is None:
        users = json.loads((ROOT/'.local/business-auth.json').read_text(encoding='utf-8'))['users']
    if not users or any(len(u.get('token','')) < 32 or not u.get('employee_id') for u in users):
        raise RuntimeError('Configure private demo identities')
    if len({u['token'] for u in users}) != len(users) or len({u['employee_id'] for u in users}) != len(users):
        raise RuntimeError('Duplicate identity binding')
    if workflow is None:
        config = json.loads((ROOT/'.local/precheck-app-api.json').read_text(encoding='utf-8'))
        workflow = WorkflowClient(config['api_key'], config['api_base'])
    store = ApplicationStore(db_path or ROOT/'.local/business/applications.sqlite3')
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='precheck')

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        yield
        executor.shutdown(wait=True)

    app = FastAPI(title='Synthetic expense applications',version='0.1.0',lifespan=lifespan)
    sessions=DemoSessions()
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

    @app.middleware('http')
    async def web_boundary(request: Request,call_next):
        if request.method not in ('GET','HEAD','OPTIONS') and (request.url.path.startswith('/web/') or
                (request.cookies.get(COOKIE) and not request.headers.get('authorization'))):
            if request.headers.get('origin')!=f'{request.url.scheme}://{request.url.netloc}':
                return JSONResponse(status_code=403,content={'detail':'Same-origin request required'})
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422,content={'detail':'Invalid request'})

    def identity(request: Request,authorization: str | None = Header(default=None)):
        if authorization is None:
            session=sessions.get(request.cookies.get(COOKIE))
            if session:return session
        value = authorization or ''
        for user in users:
            if secrets.compare_digest(value, 'Bearer '+user['token']):
                return dict(user,role='employee')
        raise HTTPException(401,'Invalid demo credential',headers={'WWW-Authenticate':'Bearer'})

    def allowed(user):
        # Existing rule service is deliberately scoped to DEMO-001 only.
        if user['employee_id'] != 'DEMO-001' or user.get('role')!='employee':
            raise HTTPException(403,'Employee outside current precheck scope')

    def execute(job_id):
        payload = store.claim(job_id)
        if payload is None:
            return
        try:
            result = workflow.run(payload)
        except WorkflowCallError as exc:
            known_failure = exc.kind=='workflow_failed' or (exc.kind=='http_error' and exc.http_status in (400,401,403,404,422,429))
            store.finish(job_id,'failed' if known_failure else 'indeterminate',error=exc.kind,run_id=exc.workflow_run_id)
        except Exception:
            store.finish(job_id,'indeterminate',error='internal_error')
        else:
            store.finish(job_id,'completed',result=result,run_id=result['workflow_run_id'])

    def extract(id):
        materials=store.claim_extraction(id)
        if materials is None:return
        document,csv=materials
        try:
            candidate=workflow.extract(document['text'])
            validation=validate_candidate(document,candidate['raw_model'],csv['items'])
            result=dict(candidate,validation=validation,source_sha256=document['sha256'],csv_sha256=csv['sha256'])
        except WorkflowCallError as exc:
            known=exc.kind=='workflow_failed' or (exc.kind=='http_error' and exc.http_status in (400,401,403,404,422,429))
            store.finish_extraction(id,'failed' if known else 'indeterminate',error=exc.kind,run_id=exc.workflow_run_id)
        except Exception:
            store.finish_extraction(id,'indeterminate',error='internal_error')
        else:
            store.finish_extraction(id,'completed',result=result,run_id=candidate['workflow_run_id'])

    @app.get('/health')
    def health():
        return {'status':'ok','mode':'synthetic_demo','storage':'sqlite'}

    @app.get('/v1/me')
    def me(user=Depends(identity)):
        return {'employee_id':user['employee_id'],'employee_type':'ordinary' if user['role']=='employee' else None,
                'role':user['role'],'display_name':user.get('display_name',user['employee_id']),
                'authentication':'local_demo','notice':'仅本机合成演示，可选择角色，不是正式登录'}

    @app.post('/web/session')
    def demo_session(body: DemoLogin,request: Request,response: Response):
        token=sessions.create(body.profile,request.cookies.get(COOKIE))
        response.set_cookie(COOKIE,token,httponly=True,samesite='strict',max_age=TTL,secure=request.url.scheme=='https',path='/')
        return {'mode':'synthetic_demo'}

    @app.delete('/web/session')
    def logout(request: Request,response: Response):
        sessions.remove(request.cookies.get(COOKIE));response.delete_cookie(COOKIE,path='/')
        return {'status':'signed_out'}

    def finance(user=Depends(identity)):
        if user.get('role')!='finance':raise HTTPException(403,'Finance role required')
        return user

    @app.get('/v1/applications')
    def list_applications(limit: int=Query(default=30,ge=1,le=100),offset: int=Query(default=0,ge=0),user=Depends(identity)):
        return store.applications(user['employee_id'],limit,offset)

    @app.get('/v1/extractions')
    def list_extractions(user=Depends(identity)):
        return {'items':store.extractions(user['employee_id'])}

    @app.get('/v1/review-queue')
    def review_queue(limit: int=Query(default=30,ge=1,le=100),offset: int=Query(default=0,ge=0),user=Depends(finance)):
        return store.applications(None,limit,offset)

    @app.get('/v1/review-applications/{application_id}')
    def review_application(application_id: str,user=Depends(finance)):
        result=store.review_bundle(application_id)
        if result is None:raise HTTPException(404,'Application not found')
        return result

    @app.post('/v1/review-applications/{application_id}/reviews')
    def review(application_id: str,body: ReviewInput,response: Response,
               idempotency_key: Annotated[str,Header(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9._:-]+$')],user=Depends(finance)):
        if store.review_bundle(application_id) is None:raise HTTPException(404,'Application not found')
        try:result,created=store.save_review(application_id,user['employee_id'],idempotency_key,body.decision,body.note)
        except Conflict:raise HTTPException(409,'Review already recorded or idempotency conflict') from None
        except ValueError:raise HTTPException(422,'Completed precheck required for review') from None
        response.status_code=201 if created else 200
        return result

    @app.get('/v1/policies/{version}')
    def policy(version: str,user=Depends(identity)):
        source=load_policy();matched=[v for v in source['versions'] if v['version']==version]
        if not matched:raise HTTPException(404,'Policy version not found')
        return dict(version=version,effective_from=matched[0]['effective_from'],effective_until=matched[0]['effective_until'],
                    policy_snapshot_sha256=hashlib.sha256(json.dumps(source,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
                    source='原创合成制度正文；规则报告条款对照，非本轮RAG检索',clauses=render_clauses(source,matched[0]))

    @app.get('/examples/{name}')
    def examples(name: str):
        if name not in ('trip-note-001.md','expense-items-001.csv'):raise HTTPException(404,'Example not found')
        return FileResponse(ROOT/'data/examples'/name,filename=name)

    @app.get('/')
    def web():return FileResponse(ROOT/'web/index.html')

    app.mount('/assets',StaticFiles(directory=ROOT/'web'),name='assets')

    @app.post('/v1/materials')
    async def upload(request: Request,response: Response,filename: Annotated[str,Query(min_length=1,max_length=100)],
                     user=Depends(identity)):
        allowed(user)
        if ('/' in filename or '\\' in filename or ':' in filename or
                any(ord(c)<32 for c in filename)):
            raise HTTPException(422,'Invalid material name')
        kind=Path(filename).suffix.lower().lstrip('.')
        mime=request.headers.get('content-type','').split(';')[0].lower()
        accepted={'csv':{'text/csv'},'md':{'text/markdown','text/plain'},'pdf':{'application/pdf'}}
        if kind not in accepted or mime not in accepted[kind]:
            raise HTTPException(415,'Supported materials: UTF-8 CSV, Markdown, text PDF')
        limit=2*1024*1024 if kind=='pdf' else MAX_BYTES
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>limit:
                raise HTTPException(413,'Material exceeds format size limit')
            raw.extend(chunk)
        parsing = parse_expense_csv(bytes(raw)) if kind=='csv' else parse_narrative(bytes(raw),kind)
        material_id,created = store.save_material(user['employee_id'],filename,bytes(raw),parsing)
        response.status_code = 422 if parsing['status']=='invalid' else 201 if created else 200
        return store.material(material_id,user['employee_id'])

    @app.get('/v1/materials/{material_id}')
    def get_material(material_id: str,user=Depends(identity)):
        record = store.material(material_id,user['employee_id'])
        if record is None:raise HTTPException(404,'Material not found')
        return record

    @app.post('/v1/extractions')
    def start_extraction(details: ExtractionRequest,response: Response,user=Depends(identity)):
        allowed(user)
        document=store.material(details.narrative_material_id,user['employee_id'])
        csv=store.material(details.csv_material_id,user['employee_id'])
        if document is None or csv is None:raise HTTPException(404,'Material not found')
        if (document.get('kind')!='narrative' or document['status']!='parsed' or csv['status']!='parsed' or
                not isinstance(csv.get('items'),list) or not csv['items']):
            raise HTTPException(422,'Provide a readable narrative and valid CSV')
        id,created=store.enqueue_extraction(user['employee_id'],details.narrative_material_id,details.csv_material_id,EXTRACTOR_VERSION)
        if created:executor.submit(extract,id)
        response.status_code=202 if created else 200
        return store.extraction(id,user['employee_id'])

    @app.get('/v1/extractions/{extraction_id}')
    def get_extraction(extraction_id: str,user=Depends(identity)):
        record=store.extraction(extraction_id,user['employee_id'])
        if record is None:raise HTTPException(404,'Extraction not found')
        return record

    @app.post('/v1/applications/from-extraction')
    def from_extraction(details: ExtractedApplication,response: Response,
                        idempotency_key: Annotated[str,Header(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9._:-]+$')],
                        user=Depends(identity)):
        allowed(user)
        record=store.extraction(details.extraction_id,user['employee_id'])
        if record is None:raise HTTPException(404,'Extraction not found')
        if record['status']!='completed' or record['result']['validation']['status']!='validated':
            raise HTTPException(422,'Extraction requires materials or manual verification')
        csv=store.material(record['csv_id'],user['employee_id'])
        try:
            data=TravelDetails.model_validate(dict(record['result']['validation']['values'],expense_items=csv['items']))
        except (ValidationError,TypeError):raise HTTPException(422,'Invalid extracted fields') from None
        payload=data.model_dump(exclude_none=True)
        payload.update(employee_id=user['employee_id'],employee_type='ordinary')
        try:
            id,created=store.create(user['employee_id'],idempotency_key,payload,record['csv_id'],record['narrative_id'],details.extraction_id)
        except Conflict:raise HTTPException(409,'Idempotency key conflicts with stored application') from None
        response.status_code=201 if created else 200
        return store.application(id,user['employee_id'])

    @app.post('/v1/applications/from-material')
    def from_material(details: MaterialApplication,response: Response,
                      idempotency_key: Annotated[str,Header(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9._:-]+$')],
                      user=Depends(identity)):
        allowed(user)
        material = store.material(details.material_id,user['employee_id'])
        if material is None:raise HTTPException(404,'Material not found')
        if material['status']!='parsed' or not material.get('items'):raise HTTPException(422,'Valid CSV required before application creation')
        try:
            validated = TravelDetails.model_validate(dict(details.model_dump(exclude={'material_id'},exclude_none=True),
                                                          expense_items=material['items']))
        except ValidationError:
            raise HTTPException(422,'Invalid parsed application') from None
        payload = validated.model_dump(exclude_none=True)
        payload.update(employee_id=user['employee_id'],employee_type='ordinary')
        try:
            id,created = store.create(user['employee_id'],idempotency_key,payload,details.material_id)
        except Conflict:
            raise HTTPException(409,'Idempotency key conflicts with stored application') from None
        response.status_code = 201 if created else 200
        return store.application(id,user['employee_id'])

    @app.post('/v1/applications')
    def create(details: TravelDetails, response: Response,
               idempotency_key: Annotated[str,Header(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9._:-]+$')],
               user=Depends(identity)):
        allowed(user)
        ids = [i.item_id.strip() for i in details.expense_items]
        if any(not id for id in ids) or len(set(ids)) != len(ids):
            raise HTTPException(422,'Item IDs must be unique and nonempty')
        payload = details.model_dump(exclude_none=True)
        payload.update(employee_id=user['employee_id'],employee_type='ordinary')
        try:
            id, created = store.create(user['employee_id'],idempotency_key,payload)
        except Conflict:
            raise HTTPException(409,'Idempotency key conflicts with stored application') from None
        response.status_code = 201 if created else 200
        return store.application(id,user['employee_id'])

    @app.get('/v1/applications/{application_id}')
    def get_application(application_id: str,user=Depends(identity)):
        record = store.application(application_id,user['employee_id'])
        if record is None:
            raise HTTPException(404,'Application not found')
        return record

    @app.post('/v1/applications/{application_id}/precheck')
    def start(application_id: str,response: Response,user=Depends(identity)):
        job_id, created = store.enqueue(application_id,user['employee_id'])
        if job_id is None:
            raise HTTPException(404,'Application not found')
        if created:
            executor.submit(execute,job_id)
        response.status_code = 202 if created else 200
        return store.job(job_id,user['employee_id'])

    @app.get('/v1/prechecks/{job_id}')
    def get_job(job_id: str,user=Depends(identity)):
        job = store.job(job_id,user['employee_id'])
        if job is None:
            raise HTTPException(404,'Precheck not found')
        return job

    return app
