import hashlib, os, secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models import User

SECRET=os.getenv('SECRET_KEY','change-me'); ALGORITHM='HS256'; oauth2=OAuth2PasswordBearer(tokenUrl='/api/auth/login')
def hash_password(value): return bcrypt.hashpw(value.encode(),bcrypt.gensalt(12)).decode()
def verify_password(value,hashed): return bcrypt.checkpw(value.encode(),hashed.encode())
def token(user,kind='access'):
    delta=timedelta(minutes=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES','30'))) if kind=='access' else timedelta(days=int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS','7')))
    return jwt.encode({'sub':str(user.id),'role':user.role.value,'type':kind,'exp':datetime.now(timezone.utc)+delta},SECRET,algorithm=ALGORITHM)
def decode(value,kind='access'):
    try:
        data=jwt.decode(value,SECRET,algorithms=[ALGORITHM])
        if data.get('type')!=kind: raise ValueError()
        return data
    except (JWTError,ValueError): raise HTTPException(status.HTTP_401_UNAUTHORIZED,'Invalid or expired token')
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def random_token(): return secrets.token_urlsafe(32)
def current_user(value:str=Depends(oauth2),db:Session=Depends(get_db)):
    user=db.get(User,int(decode(value)['sub']))
    if not user: raise HTTPException(401,'User no longer exists')
    return user
def admin_user(user:User=Depends(current_user)):
    if user.role.value!='admin': raise HTTPException(403,'Admin access required')
    return user
