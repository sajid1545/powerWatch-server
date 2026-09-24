from datetime import date, datetime, time
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class AreaOut(ORM): id:int; name:str; district:str; zone:str; description:str|None=None; status:str; created_at:datetime
class AreaCreate(BaseModel): name:str=Field(min_length=2,max_length=120); district:str=Field(min_length=2,max_length=120); zone:str=Field(min_length=1,max_length=120); description:str|None=None; status:Literal['active','inactive']='active'
class UserOut(ORM): id:int; name:str; email:EmailStr; phone:str|None=None; role:str; area_id:int|None=None; area:AreaOut|None=None; created_at:datetime
class Signup(BaseModel): name:str=Field(min_length=2,max_length=120); email:EmailStr; password:str=Field(min_length=8,max_length=72); phone:str|None=None; area_id:int|None=None
class Login(BaseModel): email:EmailStr; password:str
class ProfileUpdate(BaseModel): name:str=Field(min_length=2,max_length=120); phone:str|None=None; area_id:int|None=None
class TokenRefresh(BaseModel): refresh_token:str
class ForgotPassword(BaseModel): email:EmailStr
class ResetPassword(BaseModel): password:str=Field(min_length=8,max_length=72)
class ScheduleBase(BaseModel):
    title:str=Field(min_length=2,max_length=200); area_id:int; outage_date:date; start_time:time; end_time:time; reason:str=Field(min_length=3); status:Literal['scheduled','ongoing','completed','cancelled']='scheduled'
    @model_validator(mode='after')
    def times(self):
        if self.end_time<=self.start_time: raise ValueError('End time must be after start time')
        return self
class ScheduleCreate(ScheduleBase): pass
class ScheduleUpdate(BaseModel): title:str|None=None; area_id:int|None=None; outage_date:date|None=None; start_time:time|None=None; end_time:time|None=None; reason:str|None=None; status:Literal['scheduled','ongoing','completed','cancelled']|None=None
class ScheduleOut(ORM): id:int; title:str; area_id:int; area:AreaOut; outage_date:date; start_time:time; end_time:time; reason:str; status:str; created_by:int; created_at:datetime; updated_at:datetime
class ReportCreate(BaseModel): area_id:int; title:str=Field(min_length=2,max_length=200); description:str=Field(min_length=10)
class ReportUpdate(BaseModel): area_id:int|None=None; title:str|None=Field(default=None,min_length=2,max_length=200); description:str|None=Field(default=None,min_length=10); status:Literal['pending','investigating','resolved','rejected']|None=None; admin_response:str|None=None
class ReportOut(ORM): id:int; user_id:int; user:UserOut; area_id:int; area:AreaOut; title:str; description:str; reported_at:datetime; status:str; admin_response:str|None=None; resolved_at:datetime|None=None; created_at:datetime; updated_at:datetime
