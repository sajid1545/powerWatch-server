import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import PasswordReset, RefreshToken, User
from schemas import ForgotPassword, Login, ProfileUpdate, ResetPassword, Signup, TokenRefresh, UserOut
from security import current_user, decode, digest, hash_password, random_token, token, verify_password

router=APIRouter(prefix='/auth',tags=['Authentication'])
def user_data(user): return UserOut.model_validate(user).model_dump(mode='json')
@router.post('/signup',status_code=201)
def signup(data:Signup,db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==data.email.lower()).first(): raise HTTPException(409,'Email already registered')
    user=User(name=data.name.strip(),email=data.email.lower(),password_hash=hash_password(data.password),phone=data.phone,area_id=data.area_id); db.add(user); db.commit(); db.refresh(user)
    return {'success':True,'message':'Account created','data':{'user':user_data(user),**issue_tokens(user,db)}}
def issue_tokens(user,db):
    access,refresh=token(user),token(user,'refresh'); payload=decode(refresh,'refresh'); db.add(RefreshToken(user_id=user.id,token_hash=digest(refresh),expires_at=datetime.fromtimestamp(payload['exp'],timezone.utc))); db.commit(); return {'access_token':access,'refresh_token':refresh}
@router.post('/login')
def login(data:Login,db:Session=Depends(get_db)):
    user=db.query(User).options(joinedload(User.area)).filter(User.email==data.email.lower()).first()
    if not user or not verify_password(data.password,user.password_hash): raise HTTPException(401,'Invalid email or password')
    return {'success':True,'message':'Login successful','data':{'user':user_data(user),**issue_tokens(user,db)}}
@router.post('/refresh')
def refresh(data:TokenRefresh,db:Session=Depends(get_db)):
    payload=decode(data.refresh_token,'refresh'); saved=db.query(RefreshToken).filter(RefreshToken.token_hash==digest(data.refresh_token),RefreshToken.revoked==False).first()
    if not saved or saved.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(401,'Refresh token revoked')
    user=db.get(User,int(payload['sub'])); return {'success':True,'message':'Token refreshed','data':{'access_token':token(user)}}
@router.post('/logout')
def logout(data:TokenRefresh,db:Session=Depends(get_db)):
    saved=db.query(RefreshToken).filter(RefreshToken.token_hash==digest(data.refresh_token)).first()
    if saved: saved.revoked=True; db.commit()
    return {'success':True,'message':'Logged out','data':None}
@router.get('/me')
def me(user:User=Depends(current_user)): return {'success':True,'message':'Profile loaded','data':user_data(user)}
@router.post('/forgot-password')
def forgot(data:ForgotPassword,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.email==data.email.lower()).first(); raw=None
    if user:
        raw=random_token(); db.query(PasswordReset).filter(PasswordReset.user_id==user.id).delete(); db.add(PasswordReset(user_id=user.id,token_hash=digest(raw),expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))); db.commit()
    response={'success':True,'message':'If the account exists, reset instructions were generated','data':None}
    if os.getenv('ENVIRONMENT','development')=='development' and raw: response['data']={'reset_token':raw}
    return response
@router.post('/reset-password/{raw}')
def reset(raw:str,data:ResetPassword,db:Session=Depends(get_db)):
    item=db.query(PasswordReset).filter(PasswordReset.token_hash==digest(raw),PasswordReset.used==False,PasswordReset.expires_at>datetime.now(timezone.utc)).first()
    if not item: raise HTTPException(400,'Invalid or expired reset token')
    user=db.get(User,item.user_id); user.password_hash=hash_password(data.password); item.used=True; db.query(RefreshToken).filter(RefreshToken.user_id==user.id).update({'revoked':True}); db.commit(); return {'success':True,'message':'Password reset successful','data':None}
@router.patch('/profile')
def profile(data:ProfileUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    user.name=data.name.strip(); user.phone=data.phone; user.area_id=data.area_id; db.commit(); db.refresh(user); return {'success':True,'message':'Profile updated','data':user_data(user)}
