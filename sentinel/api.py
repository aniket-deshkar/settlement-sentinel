import asyncio
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .store import Store
from .telemetry import tracer, RUNS, LATENCY, DECISIONS

app = FastAPI(title='Settlement Sentinel', version='1.0.0')
store = Store(os.getenv('DB_PATH','data/sentinel.db'))
security = HTTPBearer(auto_error=False)
# Shared credentials are deliberately limited to a local PoC. Production requires OIDC.
tokens = {'operator':os.getenv('OPERATOR_TOKEN','demo-operator'), 'reviewer':os.getenv('REVIEWER_TOKEN','demo-reviewer')}
if os.getenv('APP_ENV') == 'production' and (any(v.startswith('demo-') for v in tokens.values()) or tokens['operator']==tokens['reviewer']):
    raise RuntimeError('Production requires distinct non-demo credentials; see productionization gates.')
def role(required):
    def verify(cred: HTTPAuthorizationCredentials = Depends(security)):
        if not cred or not secrets.compare_digest(cred.credentials,tokens[required]):
            raise HTTPException(403,'This action requires the '+required+' credential')
        return required
    return verify
class Start(BaseModel):
    scenario: Literal['fee_mismatch','duplicate','high_value'] = 'fee_mismatch'
class Decision(BaseModel):
    version: int = Field(ge=1)
    decision: Literal['approve','reject']

@app.get('/health')
def health(): return {'status':'ok','mode':os.getenv('MODEL_MODE','demo')}
@app.get('/api/cases')
def cases(actor=Depends(role('operator'))): return store.all()
@app.post('/api/cases',status_code=201)
async def investigate(body: Start, actor=Depends(role('operator'))):
    from .workflow import investigate as run
    id = str(uuid.uuid4())
    store.create({'id':id,'scenario':body.scenario,'mode':os.getenv('MODEL_MODE','demo'),'created_at':time.time()})
    try:
        with tracer.start_as_current_span('investigation') as span, LATENCY.time():
            span.set_attribute('case.id',id)
            trace_id = format(span.get_span_context().trace_id,'032x')
            result = await asyncio.wait_for(run(id,body.scenario),timeout=90)
            result['trace_id'] = trace_id
            store.finish(id,result)
        RUNS.labels('success').inc()
    except Exception as exc:
        # Never expose exception strings: upstream errors can contain URLs or secrets.
        store.finish(id,{'error':'Investigation failed; no action is permitted. Check service configuration.','error_type':type(exc).__name__},'failed')
        RUNS.labels('failed').inc()
        raise HTTPException(502,{'case_id':id,'message':'Investigation failed safely'}) from exc
    return store.get(id)
@app.get('/api/cases/{id}')
def get_case(id: str, actor=Depends(role('operator'))):
    try: return store.get(id)
    except KeyError: raise HTTPException(404,'Case not found')
@app.post('/api/cases/{id}/decision')
def decide(id: str, body: Decision, actor=Depends(role('reviewer'))):
    try:
        with tracer.start_as_current_span('human_decision') as span:
            span.set_attribute('case.id',id)
            result = store.decide(id,body.version,body.decision,actor)
        DECISIONS.labels(body.decision).inc()
        return result
    except KeyError: raise HTTPException(404,'Case not found')
    except ValueError as exc: raise HTTPException(409,str(exc))
@app.get('/metrics')
def metrics(actor=Depends(role('operator'))): return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
@app.get('/')
def ui(): return FileResponse(Path(__file__).parent/'static'/'index.html')
