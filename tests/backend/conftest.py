import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base, get_db
from app.main import create_app
from app.services.seed import ensure_admin_exists

# In-memory SQLite for tests — no file conflicts between tests
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)
_test_session = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with _test_session() as session:
        yield session


@pytest.fixture
def app():
    _app = create_app()
    _app.dependency_overrides[get_db] = _override_get_db
    return _app


@pytest.fixture(autouse=True)
async def setup_db(app):
    """Create fresh tables and seed admin for each test using in-memory DB."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    async with _test_session() as db:
        await ensure_admin_exists(db, settings.admin_default_password)

    yield

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Log in as the seeded admin and return the access token."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin",
    })
    assert response.status_code == 200
    return response.json()["access_token"]
