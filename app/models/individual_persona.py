from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, JSON, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class IndividualPersona(Base):
    __tablename__ = "individual_personas"

    id: Mapped[int] = mapped_column(primary_key=True)
    index: Mapped[int] = mapped_column(Integer, unique=True, index=True) # AI 파이프라인의 원본 인덱스
    
    # 기본 정보
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    job: Mapped[str] = mapped_column(String(100), nullable=True)
    personality: Mapped[str] = mapped_column(String(500), nullable=True)
    samsung_experience: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    # 수치 데이터 (기존 스키마 대응)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))
    
    # [option] 및 기타 필드들 (JSON으로 통합 저장하여 유연성 확보)
    all_data: Mapped[dict] = mapped_column(JSON)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
