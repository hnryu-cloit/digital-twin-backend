from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    cluster_id: Mapped[int] = mapped_column(Integer)
    persona_name: Mapped[str] = mapped_column(String(100))
    persona_name_en: Mapped[str] = mapped_column(String(100))
    age_range: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(500))
    key_characteristics: Mapped[list] = mapped_column(JSON)
    keywords: Mapped[list] = mapped_column(JSON)
    interests: Mapped[list] = mapped_column(JSON)
    segment_tags: Mapped[list] = mapped_column(JSON)
    preferred_channel: Mapped[str] = mapped_column(String(50))

    # KPI scores (0–100)
    purchase_intent: Mapped[float] = mapped_column(Float)
    brand_attitude: Mapped[float] = mapped_column(Float)
    marketing_acceptance: Mapped[float] = mapped_column(Float)
    future_value: Mapped[float] = mapped_column(Float)
    churn_risk: Mapped[float] = mapped_column(Float)

    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", backref="personas")