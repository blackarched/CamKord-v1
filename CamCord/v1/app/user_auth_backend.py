user_auth_backend.py

Production-ready user authentication backend using FastAPI with JWT

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Local imports
from .database import SessionLocal, User as DBUser
from .config import settings # Added import
# from .schemas import UserLogin # OAuth2PasswordRequestForm is used instead

# SECRET_KEY is now sourced from settings
ALGORITHM = "HS256" # Algorithm is kept hardcoded as per current design
# ACCESS_TOKEN_EXPIRE_MINUTES is sourced from settings where used. Removed global here.

auth_router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Preserved
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # tokenUrl should match the path of login_for_access_token

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Token(BaseModel): # Preserved
    access_token: str
    token_type: str

class TokenData(BaseModel): # Preserved
    username: str | None = None

# New Pydantic model for user public information (replaces old User and UserInDB)
class UserPublicInfo(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        orm_mode = True

# Modified authenticate_user
def authenticate_user(db: Session, username: str, password: str) -> DBUser | None:
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if not user:
        return None
    # Use pwd_context for verification if DBUser.verify_password is not using a compatible scheme
    # Assuming DBUser.verify_password is compatible as per database.py structure
    if not user.verify_password(password): 
        return None
    return user

# create_access_token remains the same
def create_access_token(data: dict, expires_delta: timedelta | None = None): # Preserved
    to_encode = data.copy()
    # Using settings.ACCESS_TOKEN_EXPIRE_MINUTES for consistency
    effective_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if expires_delta is None else int(expires_delta.total_seconds() / 60)
    expire = datetime.utcnow() + timedelta(minutes=effective_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM) # Use settings.SECRET_KEY

# Modified get_current_user
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> DBUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM]) # Use settings.SECRET_KEY
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = db.query(DBUser).filter(DBUser.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user # Returns the SQLAlchemy DBUser object

@auth_router.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db=db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Using settings.ACCESS_TOKEN_EXPIRE_MINUTES for consistency
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/auth/me", response_model=UserPublicInfo) # Updated response_model
async def read_users_me(current_user: DBUser = Depends(get_current_user)): # current_user is now DBUser
    return current_user # FastAPI will convert DBUser to UserPublicInfo due to orm_mode

