import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from database import Base, engine
import models
from routers import auth, resources

Base.metadata.create_all(bind=engine)
app=FastAPI(title='PowerWatch API',version='1.0.0',description='Load shedding and power outage management API')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CLIENT_URL','http://localhost:5173').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(auth.router,prefix='/api'); app.include_router(resources.router,prefix='/api')
@app.get('/',response_class=HTMLResponse,include_in_schema=False)
def landing_page():
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PowerWatch API</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;color:#e8f1f8;font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;background:radial-gradient(circle at 15% 15%,rgba(22,199,255,.18),transparent 30%),radial-gradient(circle at 85% 85%,rgba(245,183,0,.18),transparent 30%),#061827}.card{width:min(880px,100%);padding:52px;border:1px solid rgba(255,255,255,.12);border-radius:28px;background:rgba(10,35,55,.72);box-shadow:0 30px 80px rgba(0,0,0,.35);backdrop-filter:blur(18px)}.top{display:flex;align-items:center;gap:14px}.logo{display:grid;place-items:center;width:52px;height:52px;border-radius:16px;background:#f5b700;color:#071a2b;font-size:29px;box-shadow:0 12px 30px rgba(245,183,0,.25)}h1{font-size:clamp(34px,7vw,68px);line-height:1;margin:38px 0 18px;letter-spacing:-.05em}h1 span{color:#f5b700}.lead{max-width:650px;color:#a9bdcc;font-size:18px;line-height:1.7}.status{display:inline-flex;align-items:center;gap:9px;margin-top:24px;padding:9px 14px;border-radius:999px;background:rgba(16,185,129,.12);color:#73e2ae;font-weight:700;font-size:14px}.dot{width:9px;height:9px;border-radius:50%;background:#10b981;box-shadow:0 0 0 6px rgba(16,185,129,.12)}.links{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:38px}.link{padding:18px 20px;border:1px solid rgba(255,255,255,.12);border-radius:15px;color:#fff;text-decoration:none;font-weight:700;background:rgba(255,255,255,.04);transition:.2s}.link:hover{transform:translateY(-2px);border-color:#f5b700;background:rgba(245,183,0,.08)}.link small{display:block;color:#8299aa;font-weight:400;margin-top:5px}.footer{margin-top:36px;padding-top:22px;border-top:1px solid rgba(255,255,255,.1);display:flex;justify-content:space-between;color:#7890a2;font-size:13px}@media(max-width:600px){.card{padding:30px 24px}.links{grid-template-columns:1fr}.footer{flex-direction:column;gap:8px}}
</style></head><body><main class="card"><div class="top"><div class="logo">⚡</div><strong>PowerWatch</strong></div><h1>Power outage intelligence for <span>Bangladesh.</span></h1><p class="lead">The secure backend service for load-shedding schedules, community outage reports, Bangladesh-wide locations, and operational dashboards.</p><div class="status"><span class="dot"></span>API online and ready</div><div class="links"><a class="link" href="/docs">Swagger API Docs<small>Explore and test every endpoint</small></a><a class="link" href="/redoc">ReDoc Reference<small>Read structured API documentation</small></a><a class="link" href="/api/health">Health Check<small>Inspect current service availability</small></a><a class="link" href="https://power-watch-client.vercel.app/" target="_blank" rel="noopener">Open Frontend<small>Launch the live PowerWatch application</small></a></div><div class="footer"><span>PowerWatch API · v1.0.0</span><span>FastAPI + PostgreSQL</span></div></main></body></html>'''
@app.middleware('http')
async def disable_api_cache(request:Request,call_next):
    response=await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store, no-cache, must-revalidate'
        response.headers['Pragma']='no-cache'
    return response
@app.get('/api/health')
def health(): return {'success':True,'message':'PowerWatch API is healthy','data':None}
@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException): return JSONResponse(status_code=exc.status_code,content={'success':False,'message':str(exc.detail),'data':None},headers=exc.headers)
@app.exception_handler(Exception)
async def server_error(request:Request,exc:Exception):
    print(f'Unhandled {request.method} {request.url.path}: {exc!r}')
    return JSONResponse(status_code=500,content={'success':False,'message':'Internal server error','data':None})
