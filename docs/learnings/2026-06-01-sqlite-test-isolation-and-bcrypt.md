# 2026-06-01 SQLite Test Isolation and Direct Bcrypt Usage

## Pattern

- **FastAPI / SQLAlchemy Test Isolation**: Replace file-based SQLite databases in `conftest.py` with in-memory `sqlite+aiosqlite:///:memory:` engines and FastAPI `get_db` dependency overrides. This prevents file-locking, leftover table state, and UNIQUE constraint collisions across test runs.
- **Python 3.14 / Bcrypt Compatibility**: Avoid `passlib[bcrypt]` on modern Python runtimes (3.14+) due to unmaintained internal version inspection logic (`AttributeError: module 'bcrypt' has no attribute '__about__'`). Use standard `bcrypt` directly (`bcrypt.hashpw` and `bcrypt.checkpw`).

## Validated Commands

- Test execution: `src/backend/.venv/bin/python -m pytest tests/backend/ -v`
- Bcrypt usage:

  ```python
  import bcrypt

  def hash_password(password: str) -> str:
      return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

  def verify_password(plain: str, hashed: str) -> bool:
      return bcrypt.checkpw(plain.encode(), hashed.encode())
  ```

## Limits and Caveats

- In-memory SQLite with `aiosqlite` requires keeping an active connection open if using shared memory across sessions, or recreating tables per test using `Base.metadata.create_all`.
