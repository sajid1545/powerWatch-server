from datetime import date, datetime, time, timezone
from functools import lru_cache
import json
from urllib.error import URLError
from urllib.request import urlopen
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Area, Report, Schedule, User
from schemas import AreaCreate, LocationArea, ReportCreate, ReportOut, ReportUpdate, ScheduleCreate, ScheduleOut, ScheduleUpdate, UserOut
from security import admin_user, current_user

router=APIRouter(tags=['Resources'])
def response(message,data=None,**extra): return {'success':True,'message':message,'data':data,**extra}
@lru_cache(maxsize=80)
def bd_geo(path):
    try:
        with urlopen(f'https://bdapis.pro.bd/geo/v2.0/{path}',timeout=8) as result: return json.load(result).get('data',[])
    except (URLError,TimeoutError,ValueError): raise HTTPException(503,'Bangladesh location service is temporarily unavailable')
@router.get('/locations/divisions')
def divisions(): return response('Divisions loaded',bd_geo('divisions'))
@router.get('/locations/districts/{division_id}')
def districts(division_id:int): return response('Districts loaded',bd_geo(f'districts/{division_id}'))
@router.get('/locations/upazilas/{district_id}')
def upazilas(district_id:int): return response('Upazilas loaded',bd_geo(f'upazilas/{district_id}'))
@router.get('/locations/areas')
def location_areas():
    divisions={str(x['id']):x['name'] for x in bd_geo('divisions')}; districts=bd_geo('districts'); district_map={str(x['id']):x for x in districts}; rows=[]
    for item in bd_geo('upazilas'):
        district=district_map.get(str(item.get('district_id')),{}); rows.append({'id':item['id'],'name':item['name'],'bn_name':item.get('bn_name',''),'district':district.get('name',''),'division':divisions.get(str(district.get('division_id')),'')})
    return response('Bangladesh areas loaded',rows)
def paginate(query,page,limit):
    page=max(page,1); limit=min(max(limit,1),100); total=query.order_by(None).count(); return query.offset((page-1)*limit).limit(limit).all(),{'page':page,'limit':limit,'total':total,'totalPages':max(1,(total+limit-1)//limit)}
@router.get('/areas')
def areas(search:str='',status:str|None=None,page:int=1,limit:int=10,sort:str='name',db:Session=Depends(get_db)):
    q=db.query(Area); q=q.filter(or_(Area.name.ilike(f'%{search}%'),Area.district.ilike(f'%{search}%'),Area.zone.ilike(f'%{search}%'))) if search else q; q=q.filter(Area.status==status) if status else q; q=q.order_by(desc(Area.created_at) if sort=='newest' else asc(Area.name)); rows,meta=paginate(q,page,limit); return response('Areas loaded',rows,pagination=meta)
@router.post('/areas',status_code=201)
def create_area(data:AreaCreate,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=Area(**data.model_dump()); db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,'Area already exists')
    db.refresh(item); return response('Area created',item)
@router.post('/areas/resolve')
def resolve_area(data:LocationArea,user=Depends(current_user),db:Session=Depends(get_db)):
    item=db.query(Area).filter(Area.name==data.name,Area.district==data.district).first()
    if not item:
        item=Area(name=data.name,district=data.district,zone=data.division,description=f'{data.name}, {data.district}, Bangladesh',status='active'); db.add(item); db.commit(); db.refresh(item)
    return response('Area resolved',item)
@router.patch('/areas/{item_id}')
def update_area(item_id:int,data:AreaCreate,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=db.get(Area,item_id)
    if not item: raise HTTPException(404,'Area not found')
    for k,v in data.model_dump().items(): setattr(item,k,v)
    db.commit(); db.refresh(item); return response('Area updated',item)
@router.delete('/areas/{item_id}')
def delete_area(item_id:int,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=db.get(Area,item_id)
    if not item: raise HTTPException(404,'Area not found')
    if db.query(Schedule).filter(Schedule.area_id==item_id).first() or db.query(Report).filter(Report.area_id==item_id).first(): raise HTTPException(409,'Area is in use')
    db.delete(item); db.commit(); return response('Area deleted')
@router.get('/schedules')
def schedules(search:str='',status:str|None=None,area:int|None=None,areaName:str|None=None,district:str|None=None,startDate:date|None=None,endDate:date|None=None,page:int=1,limit:int=10,sort:str='newest',db:Session=Depends(get_db)):
    q=db.query(Schedule).options(joinedload(Schedule.area)).join(Area); q=q.filter(or_(Schedule.title.ilike(f'%{search}%'),Area.name.ilike(f'%{search}%'))) if search else q; q=q.filter(Schedule.status==status) if status else q; q=q.filter(Schedule.area_id==area) if area else q; q=q.filter(Area.name==areaName) if areaName else q; q=q.filter(Area.district==district) if district else q; q=q.filter(Schedule.outage_date>=startDate) if startDate else q; q=q.filter(Schedule.outage_date<=endDate) if endDate else q; order=asc(Schedule.title) if sort=='name' else (asc(Schedule.outage_date) if sort=='date' else desc(Schedule.created_at)); rows,meta=paginate(q.order_by(order),page,limit); return response('Schedules loaded',[ScheduleOut.model_validate(x) for x in rows],pagination=meta)
@router.get('/schedules/{item_id}')
def schedule(item_id:int,db:Session=Depends(get_db)):
    item=db.query(Schedule).options(joinedload(Schedule.area)).filter(Schedule.id==item_id).first()
    if not item: raise HTTPException(404,'Schedule not found')
    return response('Schedule loaded',ScheduleOut.model_validate(item))
@router.post('/schedules',status_code=201)
def create_schedule(data:ScheduleCreate,admin:User=Depends(admin_user),db:Session=Depends(get_db)):
    item=Schedule(**data.model_dump(),created_by=admin.id); db.add(item); db.commit(); db.refresh(item); return response('Schedule created',item)
@router.patch('/schedules/{item_id}')
def update_schedule(item_id:int,data:ScheduleUpdate,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=db.get(Schedule,item_id)
    if not item: raise HTTPException(404,'Schedule not found')
    values=data.model_dump(exclude_unset=True)
    for k,v in values.items(): setattr(item,k,v)
    if item.end_time<=item.start_time: raise HTTPException(422,'End time must be after start time')
    db.commit(); db.refresh(item); return response('Schedule updated',item)
@router.delete('/schedules/{item_id}')
def delete_schedule(item_id:int,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=db.get(Schedule,item_id)
    if not item: raise HTTPException(404,'Schedule not found')
    db.delete(item); db.commit(); return response('Schedule deleted')

@router.get('/reports')
def reports(search:str='',status:str|None=None,area:int|None=None,page:int=1,limit:int=10,sort:str='newest',user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Report).options(joinedload(Report.area),joinedload(Report.user)).join(User).join(Area); q=q.filter(Report.user_id==user.id) if user.role.value!='admin' else q
    if search: q=q.filter(or_(Report.title.ilike(f'%{search}%'),User.name.ilike(f'%{search}%'),User.email.ilike(f'%{search}%'),Area.name.ilike(f'%{search}%')))
    q=q.filter(Report.status==status) if status else q; q=q.filter(Report.area_id==area) if area else q; q=q.order_by(asc(Report.title) if sort=='name' else desc(Report.created_at)); rows,meta=paginate(q,page,limit); return response('Reports loaded',[ReportOut.model_validate(x) for x in rows],pagination=meta)
@router.get('/reports/{item_id}')
def report(item_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    item=db.query(Report).options(joinedload(Report.area),joinedload(Report.user)).filter(Report.id==item_id).first()
    if not item: raise HTTPException(404,'Report not found')
    if user.role.value!='admin' and item.user_id!=user.id: raise HTTPException(403,'Forbidden')
    return response('Report loaded',ReportOut.model_validate(item))
@router.post('/reports',status_code=201)
def create_report(data:ReportCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    item=Report(**data.model_dump(),user_id=user.id); db.add(item); db.commit(); db.refresh(item); return response('Outage report submitted',item)
@router.patch('/reports/{item_id}')
def update_report(item_id:int,data:ReportUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    item=db.get(Report,item_id)
    if not item: raise HTTPException(404,'Report not found')
    values=data.model_dump(exclude_unset=True)
    if user.role.value!='admin':
        if item.user_id!=user.id: raise HTTPException(403,'Forbidden')
        if item.status.value!='pending': raise HTTPException(409,'Only pending reports can be edited')
        values={k:v for k,v in values.items() if k in {'title','description','area_id'}}
    else:
        values={k:v for k,v in values.items() if k in {'status','admin_response'}}
        if values.get('status') in {'resolved','rejected'}: item.resolved_at=datetime.now(timezone.utc)
    for k,v in values.items(): setattr(item,k,v)
    db.commit(); db.refresh(item); return response('Report updated',item)
@router.delete('/reports/{item_id}')
def delete_report(item_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    item=db.get(Report,item_id)
    if not item: raise HTTPException(404,'Report not found')
    if user.role.value!='admin' and (item.user_id!=user.id or item.status.value!='pending'): raise HTTPException(403,'Only your pending reports can be deleted')
    db.delete(item); db.commit(); return response('Report deleted')
@router.get('/users')
def users(search:str='',role:str|None=None,area:int|None=None,page:int=1,limit:int=10,sort:str='newest',admin=Depends(admin_user),db:Session=Depends(get_db)):
    q=db.query(User).options(joinedload(User.area)); q=q.filter(or_(User.name.ilike(f'%{search}%'),User.email.ilike(f'%{search}%'),User.phone.ilike(f'%{search}%'))) if search else q; q=q.filter(User.role==role) if role else q; q=q.filter(User.area_id==area) if area else q; q=q.order_by(asc(User.name) if sort=='name' else desc(User.created_at)); rows,meta=paginate(q,page,limit); return response('Users loaded',[UserOut.model_validate(x) for x in rows],pagination=meta)
@router.get('/users/{item_id}')
def user_detail(item_id:int,admin=Depends(admin_user),db:Session=Depends(get_db)):
    item=db.query(User).options(joinedload(User.area)).filter(User.id==item_id).first()
    if not item: raise HTTPException(404,'User not found')
    return response('User loaded',UserOut.model_validate(item))
@router.get('/admin/stats')
def admin_stats(admin=Depends(admin_user),db:Session=Depends(get_db)):
    today=date.today(); data={'users':db.query(User).count(),'areas':db.query(Area).count(),'schedules':db.query(Schedule).count(),'today':db.query(Schedule).filter(Schedule.outage_date==today).count(),'ongoing':db.query(Schedule).filter(Schedule.status=='ongoing').count(),'pending':db.query(Report).filter(Report.status=='pending').count(),'resolved':db.query(Report).filter(Report.status=='resolved').count()}; return response('Statistics loaded',data)
@router.get('/dashboard/stats')
def dashboard_stats(user:User=Depends(current_user),db:Session=Depends(get_db)):
    today=date.today(); sf=[Schedule.area_id==user.area_id] if user.area_id else []; recent=db.query(Report).options(joinedload(Report.area),joinedload(Report.user)).filter(Report.user_id==user.id).order_by(desc(Report.updated_at)).limit(5).all(); data={'today':db.query(Schedule).filter(*sf,Schedule.outage_date==today).count(),'upcoming':db.query(Schedule).filter(*sf,Schedule.outage_date>today,Schedule.status=='scheduled').count(),'active':db.query(Schedule).filter(*sf,Schedule.status=='ongoing').count(),'pending':db.query(Report).filter(Report.user_id==user.id,Report.status=='pending').count(),'recent':[ReportOut.model_validate(x) for x in recent]}; return response('Dashboard loaded',data)
