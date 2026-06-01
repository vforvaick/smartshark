from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import AnalysisRun
from app.models.profile import AnalysisProfile, ProfileConfig
from app.models.user import User
from app.schemas.profile import (
    ProfileInfo,
    SetProfileRequest,
    ProfileConfigResponse,
    ProgressiveQuestionsResponse,
)
from app.services.profile import (
    PROFILE_DESCRIPTIONS,
    PROFILE_CHECK_WEIGHTING,
    get_profile_config_data,
    get_progressive_questions,
    set_run_profile,
    get_run_profile,
)

router = APIRouter(prefix="/api", tags=["profiles"])


@router.get("/profiles", response_model=list[ProfileInfo])
async def list_profiles(
    _user: User = Depends(get_current_user),
):
    """List all available analysis profiles with descriptions."""
    result = []
    for profile in AnalysisProfile:
        result.append(ProfileInfo(
            id=profile.value,
            description=PROFILE_DESCRIPTIONS[profile],
            is_default=(profile == AnalysisProfile.general),
        ))
    return result


@router.post(
    "/analysis-runs/{run_id}/profile",
    response_model=ProfileConfigResponse,
)
async def set_profile(
    run_id: int,
    body: SetProfileRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Set the analysis profile for a run. One profile per run, cannot be changed."""
    # Verify run exists
    run_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    if run_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    try:
        config = await set_run_profile(db, run_id, body.profile)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already set for this analysis run",
        )

    # Build response with check_weighting from service data
    config_data = get_profile_config_data(config.profile)
    return ProfileConfigResponse(
        id=config.id,
        analysis_run_id=config.analysis_run_id,
        profile=config.profile,
        assumptions=config.assumptions,
        limitations=config.limitations,
        check_weighting=config_data["check_weighting"],
        mapping_questions=config.mapping_questions,
        created_at=config.created_at,
    )


@router.get(
    "/analysis-runs/{run_id}/profile",
    response_model=ProfileConfigResponse,
)
async def get_profile(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the current profile config for an analysis run."""
    # Verify run exists
    run_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    if run_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    config = await get_run_profile(db, run_id)
    if config is None:
        # Return default general profile config
        config_data = get_profile_config_data(AnalysisProfile.general)
        return ProfileConfigResponse(
            id=0,
            analysis_run_id=run_id,
            profile=AnalysisProfile.general,
            assumptions=config_data["assumptions"],
            limitations=config_data["limitations"],
            check_weighting=config_data["check_weighting"],
            mapping_questions=[],
            created_at=None,  # type: ignore  — no DB record
        )

    config_data = get_profile_config_data(config.profile)
    return ProfileConfigResponse(
        id=config.id,
        analysis_run_id=config.analysis_run_id,
        profile=config.profile,
        assumptions=config.assumptions,
        limitations=config.limitations,
        check_weighting=config_data["check_weighting"],
        mapping_questions=config.mapping_questions,
        created_at=config.created_at,
    )


@router.get(
    "/analysis-runs/{run_id}/profile/questions",
    response_model=ProgressiveQuestionsResponse,
)
async def get_profile_questions(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get progressive context questions based on the run's profile and prescan data."""
    # Verify run exists
    run_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    if run_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    config = await get_run_profile(db, run_id)
    profile = config.profile if config else AnalysisProfile.general
    questions = get_progressive_questions(profile, prescan_data=None)
    return ProgressiveQuestionsResponse(questions=questions)
