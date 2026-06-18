from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.domain import GeneratedFile, ProjectSpec, Question, QuestionType
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)

_APP_MAIN_PY = """\
\"\"\"Main application entry point.\"\"\"

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="FastAPI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}
"""

_APP_MODELS_PY = """\
\"\"\"SQLAlchemy models.\"\"\"

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
"""

_APP_SCHEMAS_PY = """\
\"\"\"Pydantic schemas.\"\"\"

from datetime import datetime

from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str


class ItemResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
"""

_APP_DATABASE_PY = """\
\"\"\"Database setup.\"\"\"

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
"""

_APP_ROUTES_HEALTH_PY = """\
\"\"\"Health check endpoint.\"\"\"

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
"""

_APP_MIDDLEWARE_AUTH_PY = """\
\"\"\"JWT authentication middleware.\"\"\"

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
"""

_APP_ROUTES_AUTH_PY = """\
\"\"\"Authentication routes.\"\"\"

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from jose import jwt
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login")
async def login() -> dict[str, str]:
    return {"message": "Login endpoint — implement me"}


@router.post("/refresh")
async def refresh() -> dict[str, str]:
    return {"message": "Refresh endpoint — implement me"}


@router.get("/me")
async def read_current_user() -> dict[str, str]:
    return {"message": "Me endpoint — implement me"}
"""


class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "fastapi"
    display_name = "FastAPI"
    description = "FastAPI backend with SQLAlchemy + Pydantic"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("fastapi", {})

    def questions(self) -> list[Question]:
        return [
            Question(
                key="orm",
                label="ORM",
                question_type=QuestionType.CHOICE,
                required=True,
                default="sqlalchemy",
                description="ORM to use for database access",
                options=["sqlalchemy", "none"],
            ),
            Question(
                key="auth",
                label="Authentication",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include JWT authentication",
            ),
            Question(
                key="include_alembic",
                label="Include Alembic",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include Alembic for database migrations",
            ),
        ]

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        config = self._config(spec)
        orm = config.get("orm", "sqlalchemy")
        auth = config.get("auth", False)

        reqs = [
            "fastapi>=0.115",
            "uvicorn[standard]>=0.34",
        ]
        if orm == "sqlalchemy":
            reqs.append("sqlalchemy>=2.0")
            reqs.append("aiosqlite>=0.20")
        if auth:
            reqs.append("python-jose[cryptography]>=3.3")
            reqs.append("passlib[bcrypt]>=1.7")

        files = [
            GeneratedFile(
                path=Path("app/__init__.py"),
                content='"""FastAPI application package."""\n',
            ),
            GeneratedFile(path=Path("app/main.py"), content=_APP_MAIN_PY),
            GeneratedFile(path=Path("app/schemas.py"), content=_APP_SCHEMAS_PY),
            GeneratedFile(path=Path("app/routes/__init__.py"), content='"""Routes package."""\n'),
            GeneratedFile(path=Path("app/routes/health.py"), content=_APP_ROUTES_HEALTH_PY),
            GeneratedFile(path=Path("requirements.txt"), content="\n".join(reqs) + "\n"),
        ]

        if orm == "sqlalchemy":
            files.append(GeneratedFile(path=Path("app/models.py"), content=_APP_MODELS_PY))
            files.append(GeneratedFile(path=Path("app/database.py"), content=_APP_DATABASE_PY))

        if auth:
            files.append(
                GeneratedFile(
                    path=Path("app/middleware/__init__.py"), content='"""Middleware package."""\n'
                )
            )
            files.append(
                GeneratedFile(path=Path("app/middleware/auth.py"), content=_APP_MIDDLEWARE_AUTH_PY)
            )
            files.append(
                GeneratedFile(path=Path("app/routes/auth.py"), content=_APP_ROUTES_AUTH_PY)
            )

        return files

    def directories(self, spec: ProjectSpec) -> list[str]:
        config = self._config(spec)
        include_alembic = config.get("include_alembic", False)
        auth = config.get("auth", False)

        dirs = ["app/", "app/routes/"]
        if include_alembic:
            dirs.append("alembic/")
        if auth:
            dirs.append("app/middleware/")
        return dirs

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        config = self._config(spec)
        orm = config.get("orm", "sqlalchemy")
        auth = config.get("auth", False)

        deps = ["fastapi>=0.115", "uvicorn[standard]>=0.34"]
        if orm == "sqlalchemy":
            deps.append("sqlalchemy>=2.0")
            deps.append("aiosqlite>=0.20")
        if auth:
            deps.append("python-jose[cryptography]>=3.3")
            deps.append("passlib[bcrypt]>=1.7")
        return deps

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: Any) -> None:
        deps = ["uv", "add", "fastapi>=0.115", "uvicorn[standard]>=0.34"]
        config = self._config(spec)
        if config.get("orm", "sqlalchemy") == "sqlalchemy":
            deps.append("sqlalchemy>=2.0")
            deps.append("aiosqlite>=0.20")
        if config.get("auth", False):
            deps.append("python-jose[cryptography]>=3.3")
            deps.append("passlib[bcrypt]>=1.7")
        executor.run(deps, cwd=target_dir)
