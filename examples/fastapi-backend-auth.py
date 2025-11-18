"""
FastAPI Backend - Authentication Implementation Example
Demonstrates JWT-based authentication for Promptheus multi-user platform
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Use env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

app = FastAPI(title="Promptheus API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ============================================================================
# MODELS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=12)


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: UUID
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    team_id: Optional[UUID] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    scopes: List[str] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PromptAnalyzeRequest(BaseModel):
    prompt: str
    provider: Optional[str] = "gemini"


class PromptRefineRequest(BaseModel):
    prompt: str
    answers: dict
    task_type: str = "generation"


class PromptTweakRequest(BaseModel):
    current_prompt: str
    tweak_instruction: str


class PromptHistoryResponse(BaseModel):
    id: UUID
    original_prompt: str
    refined_prompt: str
    task_type: Optional[str]
    provider: str
    model: str
    created_at: datetime
    is_shared: bool


# ============================================================================
# DATABASE (In-memory for demo - use PostgreSQL in production)
# ============================================================================

# Simulated database
users_db: dict[UUID, UserInDB] = {}
refresh_tokens_db: dict[str, dict] = {}
prompt_history_db: dict[UUID, dict] = {}


# ============================================================================
# AUTHENTICATION UTILITIES
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: UUID) -> str:
    """Create a refresh token."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_tokens_db[token] = {
        "user_id": user_id,
        "expires_at": expires_at,
        "revoked": False
    }

    return token


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        scopes: list = payload.get("scopes", [])

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(user_id=UUID(user_id), email=email, scopes=scopes)

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    """Get the current authenticated user."""
    token_data = verify_token(credentials.credentials)

    user = users_db.get(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Ensure user is active."""
    return current_user


# ============================================================================
# API KEY AUTHENTICATION (for CLI)
# ============================================================================

api_keys_db: dict[str, dict] = {}


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[UserInDB]:
    """Verify API key for CLI authentication."""
    if not x_api_key:
        return None

    key_data = api_keys_db.get(x_api_key)
    if not key_data or key_data.get("revoked"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )

    # Check expiry
    if key_data.get("expires_at") and key_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    # Update last used
    key_data["last_used_at"] = datetime.utcnow()

    user = users_db.get(key_data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


async def get_user_from_token_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> UserInDB:
    """Support both JWT tokens and API keys for authentication."""
    # Try API key first (for CLI)
    if x_api_key:
        user = await verify_api_key(x_api_key)
        if user:
            return user

    # Fall back to JWT token (for web)
    if credentials:
        return await get_current_user(credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    # Check if user already exists
    for user in users_db.values():
        if user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        if user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Create new user
    user_id = uuid4()
    user = UserInDB(
        id=user_id,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        created_at=datetime.utcnow()
    )

    users_db[user_id] = user

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at
    )


@app.post("/api/v1/auth/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Login with email and password."""
    # Find user by email
    user = None
    for u in users_db.values():
        if u.email == login_data.email:
            user = u
            break

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "scopes": ["prompts:read", "prompts:write"]
        },
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/v1/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    token_data = refresh_tokens_db.get(refresh_token)

    if not token_data or token_data["revoked"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token"
        )

    if token_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    user_id = token_data["user_id"]
    user = users_db.get(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "scopes": ["prompts:read", "prompts:write"]
        },
        expires_delta=access_token_expires
    )

    # Optionally rotate refresh token
    new_refresh_token = create_refresh_token(user.id)

    # Revoke old refresh token
    token_data["revoked"] = True

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/v1/auth/logout")
async def logout(
    refresh_token: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Logout by revoking refresh token."""
    token_data = refresh_tokens_db.get(refresh_token)
    if token_data:
        token_data["revoked"] = True

    return {"message": "Successfully logged out"}


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_active_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


# ============================================================================
# API KEY ENDPOINTS (for CLI)
# ============================================================================

class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = 30


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only shown once during creation
    prefix: str
    created_at: datetime
    expires_at: Optional[datetime]


@app.post("/api/v1/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Create a new API key for CLI authentication."""
    key_id = uuid4()
    key = f"sk-live-{secrets.token_urlsafe(32)}"

    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    api_keys_db[key] = {
        "id": key_id,
        "user_id": current_user.id,
        "name": key_data.name,
        "prefix": key[:15],
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "last_used_at": None,
        "revoked": False
    }

    return APIKeyResponse(
        id=key_id,
        name=key_data.name,
        key=key,  # Only shown during creation
        prefix=key[:15],
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )


@app.get("/api/v1/api-keys")
async def list_api_keys(current_user: UserInDB = Depends(get_current_active_user)):
    """List user's API keys (without full key values)."""
    user_keys = [
        {
            "id": data["id"],
            "name": data["name"],
            "prefix": data["prefix"],
            "created_at": data["created_at"],
            "last_used_at": data.get("last_used_at"),
            "expires_at": data.get("expires_at"),
            "revoked": data["revoked"]
        }
        for key, data in api_keys_db.items()
        if data["user_id"] == current_user.id
    ]
    return user_keys


@app.delete("/api/v1/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Revoke an API key."""
    for key, data in api_keys_db.items():
        if data["id"] == key_id and data["user_id"] == current_user.id:
            data["revoked"] = True
            return {"message": "API key revoked successfully"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="API key not found"
    )


# ============================================================================
# PROMPT ENDPOINTS (Core Promptheus functionality)
# ============================================================================

@app.post("/api/v1/prompts/analyze")
async def analyze_prompt(
    request: PromptAnalyzeRequest,
    current_user: UserInDB = Depends(get_user_from_token_or_api_key)
):
    """
    Analyze a prompt and generate clarifying questions.
    This integrates with the existing Promptheus logic.
    """
    # In production, this would call the actual provider logic
    # from src/promptheus/providers.py

    return {
        "task_type": "generation",
        "questions": [
            {
                "question": "What is the target audience for this content?",
                "type": "text",
                "required": True,
                "default": ""
            },
            {
                "question": "What tone should be used?",
                "type": "radio",
                "options": ["Professional", "Casual", "Technical", "Creative"],
                "required": True,
                "default": "Professional"
            },
            {
                "question": "Desired length?",
                "type": "radio",
                "options": ["Short (1-2 paragraphs)", "Medium (3-5 paragraphs)", "Long (6+ paragraphs)"],
                "required": False,
                "default": "Medium (3-5 paragraphs)"
            }
        ]
    }


@app.post("/api/v1/prompts/refine")
async def refine_prompt(
    request: PromptRefineRequest,
    current_user: UserInDB = Depends(get_user_from_token_or_api_key)
):
    """Refine a prompt based on user answers."""
    # In production, integrate with actual refinement logic
    refined = f"""# Refined Prompt

Original: {request.prompt}

Task Type: {request.task_type}
User Answers: {request.answers}

[Generated refined prompt would appear here based on actual AI processing]
"""

    # Save to history
    history_id = uuid4()
    prompt_history_db[history_id] = {
        "id": history_id,
        "user_id": current_user.id,
        "original_prompt": request.prompt,
        "refined_prompt": refined,
        "task_type": request.task_type,
        "provider": "gemini",
        "model": "gemini-2.0-flash-exp",
        "created_at": datetime.utcnow(),
        "is_shared": False
    }

    return {
        "refined_prompt": refined,
        "history_id": history_id
    }


@app.post("/api/v1/prompts/tweak")
async def tweak_prompt(
    request: PromptTweakRequest,
    current_user: UserInDB = Depends(get_user_from_token_or_api_key)
):
    """Apply iterative tweaks to a refined prompt."""
    tweaked = f"{request.current_prompt}\n\n[Tweaked based on: {request.tweak_instruction}]"

    return {"tweaked_prompt": tweaked}


@app.get("/api/v1/prompts/history", response_model=List[PromptHistoryResponse])
async def get_history(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_user_from_token_or_api_key)
):
    """Get user's prompt history."""
    user_history = [
        PromptHistoryResponse(
            id=entry["id"],
            original_prompt=entry["original_prompt"],
            refined_prompt=entry["refined_prompt"],
            task_type=entry.get("task_type"),
            provider=entry["provider"],
            model=entry["model"],
            created_at=entry["created_at"],
            is_shared=entry["is_shared"]
        )
        for entry in prompt_history_db.values()
        if entry["user_id"] == current_user.id
    ]

    # Sort by created_at descending
    user_history.sort(key=lambda x: x.created_at, reverse=True)

    return user_history[offset:offset + limit]


@app.delete("/api/v1/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: UUID,
    current_user: UserInDB = Depends(get_user_from_token_or_api_key)
):
    """Delete a prompt from history."""
    entry = prompt_history_db.get(prompt_id)
    if not entry or entry["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    del prompt_history_db[prompt_id]
    return {"message": "Prompt deleted successfully"}


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Create demo user on startup."""
    # Create a test user for development
    user_id = uuid4()
    users_db[user_id] = UserInDB(
        id=user_id,
        email="demo@promptheus.dev",
        username="demo",
        full_name="Demo User",
        hashed_password=get_password_hash("DemoPassword123!"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )

    print(f"""
    ╔════════════════════════════════════════════════════════╗
    ║  Promptheus API Server Started                         ║
    ║                                                        ║
    ║  Demo User Created:                                    ║
    ║    Email: demo@promptheus.dev                          ║
    ║    Password: DemoPassword123!                          ║
    ║                                                        ║
    ║  API Docs: http://localhost:8000/docs                  ║
    ╚════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
