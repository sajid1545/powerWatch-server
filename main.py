import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import Base, engine
import models
from routers import auth, resources

Base.metadata.create_all(bind=engine)
app=FastAPI(title='PowerWatch API',version='1.0.0',description='Load shedding and power outage management API')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CLIENT_URL','http://localhost:5173').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(auth.router,prefix='/api'); app.include_router(resources.router,prefix='/api')
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
