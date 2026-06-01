# 2026-06-01 CI Missing python-multipart

## What Failed
- First GitHub Actions CI run after pushing Smartshark failed in backend test collection.
- Error: `RuntimeError: Form data requires "python-multipart" to be installed`.

## Suspected Cause
- FastAPI routes use form/upload handling, but `python-multipart` was missing from both root and backend project dependency declarations.
- Local verification used an existing backend virtualenv where `python-multipart` was already installed, so the dependency gap only appeared in clean CI.

## What Was Tried
- Read the CI log with `gh run view --repo vforvaick/smartshark 26772305706 --job 78914689054 --log`.
- Added `python-multipart>=0.0.20` to `pyproject.toml` and `src/backend/pyproject.toml`.
- Re-ran local backend tests and frontend checks.
- Pushed fix and re-ran CI.

## Safer Next Step
- Treat clean CI as the authority for dependency completeness.
- When local venv passes but CI fails during import/collection, compare dependency declarations against imports/framework runtime requirements before changing app logic.
