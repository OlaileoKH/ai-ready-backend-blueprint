import jwt
import time
from fastapi import FastAPI, status, Depends, BackgroundTasks, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse

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

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    # Keep the 'r' for a raw string to protect JavaScript variables
    html_content = r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI-Ready Task Dashboard</title>
        <style>
            :root {
                --primary: #4f46e5;
                --primary-hover: #4338ca;
                --success: #10b981;
                --success-hover: #059669;
                --background: #f8fafc;
                --card-bg: #ffffff;
                --text-main: #0f172a;
                --text-muted: #64748b;
                --border: #e2e8f0;
            }

            body { 
                font-family: 'Inter', system-ui, -apple-system, sans-serif; 
                background: var(--background); 
                margin: 0; 
                padding: 40px 20px; 
                color: var(--text-main); 
                min-height: 100vh;
            }

            .container { 
                max-width: 1000px; 
                margin: 0 auto; 
                display: grid; 
                grid-template-columns: 1fr 1.8fr; 
                gap: 32px; 
            }

            @media (max-width: 768px) {
                .container { grid-template-columns: 1fr; }
            }

            .card { 
                background: var(--card-bg); 
                padding: 30px; 
                border-radius: 16px; 
                box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.04); 
                border: 1px solid var(--border);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .card:hover {
                box-shadow: 0 10px 25px -3px rgba(15, 23, 42, 0.08);
            }

            h2 { 
                margin-top: 0; 
                color: var(--text-main); 
                font-size: 20px;
                font-weight: 700;
                letter-spacing: -0.02em;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            input, textarea, select { 
                width: 100%; 
                padding: 12px 16px; 
                margin: 12px 0; 
                border: 1px solid var(--border); 
                border-radius: 8px; 
                box-sizing: border-box; 
                font-size: 14px;
                background-color: #f8fafc;
                transition: border-color 0.2s, background-color 0.2s, box-shadow 0.2s;
            }

            input:focus, textarea:focus, select:focus {
                outline: none;
                border-color: var(--primary);
                background-color: #fff;
                box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
            }

            button { 
                background: var(--primary); 
                color: white; 
                border: none; 
                padding: 14px; 
                width: 100%; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 15px; 
                font-weight: 600; 
                transition: background-color 0.2s, transform 0.1s, box-shadow 0.2s;
                box-shadow: 0 2px 4px rgba(79, 70, 229, 0.1);
            }

            button:hover { 
                background: var(--primary-hover); 
                box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
            }

            button:active {
                transform: scale(0.98);
            }

            /* --- PREMIUM REFRESH BUTTON CONFIGURATION --- */
            .refresh-btn {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
            }

            .refresh-btn:hover {
                background: linear-gradient(135deg, #059669 0%, #047857 100%);
                box-shadow: 0 6px 16px rgba(16, 185, 129, 0.3);
            }

            .refresh-btn svg {
                width: 16px;
                height: 16px;
                transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .refresh-btn:hover svg {
                transform: rotate(180deg);
            }

            .auth-toggle { 
                text-align: center; 
                margin-top: 16px; 
                color: var(--primary); 
                cursor: pointer; 
                font-size: 14px;
                font-weight: 500;
            }
            .auth-toggle:hover {
                text-decoration: underline;
            }

            .hidden { display: none; }

            .task-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid var(--border);
                padding-bottom: 12px;
                margin-bottom: 20px;
            }
            .task-header h2 { margin-bottom: 0; border: none; padding: 0; }

            /* --- MODERN TASK CARDS --- */
            .task-item { 
                border-left: 4px solid var(--primary); 
                padding: 16px; 
                margin: 14px 0; 
                background: #fff; 
                border-radius: 4px 12px 12px 4px; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                border-top: 1px solid var(--border);
                border-right: 1px solid var(--border);
                border-bottom: 1px solid var(--border);
                animation: fadeIn 0.3s ease forwards;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(6px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .task-title {
                font-weight: 600;
                font-size: 15px;
                color: var(--text-main);
                margin-bottom: 4px;
            }

            .task-meta {
                font-size: 13px;
                color: var(--text-muted);
            }

            /* --- VIBRANT BADGES --- */
            .status-badge { 
                padding: 6px 12px; 
                border-radius: 9999px; 
                font-size: 12px; 
                font-weight: 600; 
                text-transform: capitalize; 
                letter-spacing: 0.02em;
            }
            .status-pending { background: #fef3c7; color: #d97706; }
            .status-processing { background: #dbeafe; color: #2563eb; position: relative; animation: pulse 2s infinite; }
            .status-completed { background: #d1fae5; color: #059669; }

            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.6; }
                100% { opacity: 1; }
            }
        </style>
    </head>
    <body>
        <h1 style="text-align: center; color: var(--text-main); font-size: 28px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 48px;">🎯 AI-Ready Task Dashboard</h1>
        <div class="container">
            
            <!-- LEFT COLUMN: ACCOUNT INFRASTRUCTURE -->
            <div>
                <div class="card" id="auth-box">
                    <h2 id="auth-title">Account Login</h2>
                    <input type="email" id="auth-email" placeholder="Enter your email">
                    <input type="password" id="auth-password" placeholder="Enter your password">
                    <button id="auth-btn" onclick="handleAuth()">Login</button>
                    <div class="auth-toggle" id="auth-toggle-text" onclick="toggleAuthMode()">Don't have an account? Sign Up</div>
                </div>
                
                <div class="card hidden" id="profile-box">
                    <h2>Account Authorized</h2>
                    <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 24px;">Active user identity:<br><strong id="user-display" style="color: var(--text-main);"></strong></p>
                    <button style="background: #ef4444;" onclick="logout()">Disconnect Account</button>
                </div>
            </div>

            <!-- RIGHT COLUMN: CONTROL MONITOR PANEL -->
            <div>
                <div class="card" id="task-creator-box" style="opacity: 0.4; pointer-events: none; margin-bottom: 24px;">
                    <h2>Create Server Task</h2>
                    <p style="color: #ef4444; font-size: 14px; margin-top: -8px; margin-bottom: 16px;" id="lock-msg">⚠️ Security clearance required. Please log in.</p>
                    <input type="text" id="task-title" placeholder="Task Title (e.g., Run Model Assessment)">
                    <textarea id="task-desc" placeholder="Task Payload Description Data (Prompts, variables...)" rows="3"></textarea>
                    <select id="task-priority">
                        <option value="1">Priority Level 1 (Standard Core)</option>
                        <option value="3">Priority Level 3 (Elevated Queue)</option>
                        <option value="5">Priority Level 5 (High AI Priority)</option>
                    </select>
                    <button style="background: #10b981;" onclick="createTask()">Submit Task Pipeline</button>
                </div>

                <div class="card">
                    <div class="task-header">
                        <h2>Pipeline Stream Monitor</h2>
                        <button class="refresh-btn" style="width: auto; padding: 10px 18px;" onclick="fetchTasks()">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                            </svg>
                            Sync Engine Feed
                        </button>
                    </div>
                    <div id="task-list-container">
                        <p style="color: var(--text-muted); text-align: center; font-size: 14px;">Monitor stream waiting for active authentication...</p>
                    </div>
                </div>
            </div>

        </div>

        <script>
            let isSignUpMode = false;
            let authToken = localStorage.getItem("token") || "";
            let userEmail = localStorage.getItem("email") || "";

            window.onload = function() {
                if(authToken) { showLoggedInState(); fetchTasks(); }
            }

            function toggleAuthMode() {
                isSignUpMode = !isSignUpMode;
                document.getElementById("auth-title").innerText = isSignUpMode ? "Create Account" : "Account Login";
                document.getElementById("auth-btn").innerText = isSignUpMode ? "Sign Up" : "Login";
                document.getElementById("auth-toggle-text").innerText = isSignUpMode ? "Already have an account? Login" : "Don't have an account? Sign Up";
            }

            async function handleAuth() {
                const email = document.getElementById("auth-email").value;
                const password = document.getElementById("auth-password").value;
                
                if(!email || !password) return alert("Please fill in fields");

                if(isSignUpMode) {
                    const res = await fetch("/signup", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, password })
                    });
                    if(res.ok) {
                        alert("Account built! Switching to login...");
                        toggleAuthMode();
                    } else {
                        const err = await res.json();
                        alert("Error: " + err.detail);
                    }
                } else {
                    const formData = new URLSearchParams();
                    formData.append("username", email);
                    formData.append("password", password);

                    const res = await fetch("/login", {
                        method: "POST",
                        body: formData
                    });
                    if(res.ok) {
                        const data = await res.json();
                        authToken = data.access_token;
                        userEmail = email;
                        localStorage.setItem("token", authToken);
                        localStorage.setItem("email", userEmail);
                        showLoggedInState();
                        fetchTasks();
                    } else {
                        alert("Invalid login details.");
                    }
                }
            }

            function showLoggedInState() {
                document.getElementById("auth-box").classList.add("hidden");
                document.getElementById("profile-box").classList.remove("hidden");
                document.getElementById("user-display").innerText = userEmail;
                
                const creator = document.getElementById("task-creator-box");
                creator.style.opacity = "1";
                creator.style.pointerEvents = "auto";
                document.getElementById("lock-msg").classList.add("hidden");
            }

            function logout() {
                localStorage.clear();
                window.location.reload();
            }

            async function createTask() {
                const title = document.getElementById("task-title").value;
                const description = document.getElementById("task-desc").value;
                const priority = parseInt(document.getElementById("task-priority").value);

                const res = await fetch("/tasks", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + authToken
                    },
                    body: JSON.stringify({ title, description, priority })
                });

                if(res.ok) {
                    document.getElementById("task-title").value = "";
                    document.getElementById("task-desc").value = "";
                    fetchTasks();
                    for(let i=1; i<=4; i++) {
                        setTimeout(fetchTasks, i * 2000);
                    }
                }
            }

            async function fetchTasks() {
                if(!authToken) return;
                const res = await fetch("/tasks", {
                    headers: { "Authorization": "Bearer " + authToken }
                });
                if(res.ok) {
                    const tasks = await res.json();
                    const container = document.getElementById("task-list-container");
                    if(tasks.length === 0) {
                        container.innerHTML = '<p style="color: var(--text-muted); text-align: center; font-size: 14px;">No pipeline records found.</p>';
                        return;
                    }
                    container.innerHTML = tasks.map(t => `
                        <div class="task-item">
                            <div>
                                <div class="task-title">${t.title}</div>
                                <div class="task-meta">${t.description || 'No description provided.'} &bull; Priority: ${t.priority}</div>
                            </div>
                            <span class="status-badge status-${t.status}">${t.status}</span>
                        </div>
                    `).join("");
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

