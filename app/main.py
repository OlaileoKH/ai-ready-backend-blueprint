import jwt
import time
from fastapi import FastAPI, status, Depends, BackgroundTasks, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models import TaskModel, UserModel
from app.schemas import TaskCreate, TaskResponse, UserCreate, UserResponse, TokenResponse
# Import the module explicitly to prevent any local naming collision errors
from app import security

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Secure AI-Ready Backend Blueprint")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
    )
    try:
        # Pass security.ALGORITHM explicitly inside a list string template
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- AUTH ROUTES ---


@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_input: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user_input.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = UserModel(
        email=user_input.email,
        hashed_password=security.hash_password(user_input.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Swagger sends the email inside the form_data.username field automatically
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
# --- PROTECTED TASK ROUTES ---

def heavy_processing_worker(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task:
            task.status = "processing"
            db.commit()
            time.sleep(7)
            task.status = "completed"
            task.is_completed = True
            db.commit()
    finally:
        db.close()

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_input: TaskCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    new_task_row = TaskModel(
        title=task_input.title,
        description=task_input.description,
        priority=task_input.priority,
        status="pending",
        user_id=current_user.id
    )
    db.add(new_task_row)
    db.commit()
    db.refresh(new_task_row)
    background_tasks.add_task(heavy_processing_worker, new_task_row.id)
    return new_task_row

@app.get("/tasks", response_model=List[TaskResponse])
async def get_all_tasks(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    return db.query(TaskModel).filter(TaskModel.user_id == current_user.id).all()
