import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisProfile(str, enum.Enum):
    general = "general"
    f5_load_balancer = "f5_load_balancer"
    infoblox_dns = "infoblox_dns"
    verifone_intellinac = "verifone_intellinac"


class ProfileConfig(Base):
    __tablename__ = "profile_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    profile: Mapped[AnalysisProfile] = mapped_column(
        Enum(AnalysisProfile), default=AnalysisProfile.general
    )
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    mapping_questions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="profile_config"
    )
