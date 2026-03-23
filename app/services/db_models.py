"""SQLAlchemy ORM models for SQLite persistence."""
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
        }


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    data_sources = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    status = Column(String, default="draft")
    progress = Column(Integer, default=0)
    response_count = Column(Integer, default=0)
    target_responses = Column(Integer, default=1000)
    surveys_count = Column(Integer, default=0)
    reports_count = Column(Integer, default=0)
    persona_count = Column(Integer, default=0)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "purpose": self.purpose,
            "description": self.description,
            "data_sources": self.data_sources or [],
            "tags": self.tags or [],
            "status": self.status,
            "progress": self.progress,
            "response_count": self.response_count,
            "target_responses": self.target_responses,
            "surveys_count": self.surveys_count,
            "reports_count": self.reports_count,
            "persona_count": self.persona_count,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }


class PersonaModel(Base):
    __tablename__ = "personas"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, default=0)
    gender = Column(String, default="")
    occupation = Column(String, default="")
    segment = Column(String, default="")
    keywords = Column(JSON, default=list)
    interests = Column(JSON, default=list)
    preferred_channel = Column(String, default="")
    purchase_intent = Column(Float, default=0.0)
    marketing_acceptance = Column(Float, default=0.0)
    brand_attitude = Column(Float, default=0.0)
    future_value = Column(Float, default=0.0)
    profile = Column(Text, default="")
    purchase_history = Column(JSON, default=list)
    activity_logs = Column(JSON, default=list)
    cot = Column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "segment": self.segment,
            "keywords": self.keywords or [],
            "interests": self.interests or [],
            "preferred_channel": self.preferred_channel,
            "purchase_intent": self.purchase_intent,
            "marketing_acceptance": self.marketing_acceptance,
            "brand_attitude": self.brand_attitude,
            "future_value": self.future_value,
            "profile": self.profile,
            "purchase_history": self.purchase_history or [],
            "activity_logs": self.activity_logs or [],
            "cot": self.cot or [],
        }


class SurveyQuestionModel(Base):
    __tablename__ = "survey_questions"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    options = Column(JSON, default=list)
    order = Column(Integer, default=0)
    status = Column(String, default="draft")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "text": self.text,
            "type": self.type,
            "options": self.options or [],
            "order": self.order,
            "status": self.status,
        }


class SimulationModel(Base):
    __tablename__ = "simulations"

    project_id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    status = Column(String, default="idle")
    progress = Column(Integer, default=0)
    completed_responses = Column(Integer, default=0)
    target_responses = Column(Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "completed_responses": self.completed_responses,
            "target_responses": self.target_responses,
        }


class SimulationResponseModel(Base):
    __tablename__ = "simulation_responses"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    persona_name = Column(String, default="")
    segment = Column(String, default="")
    question_id = Column(String, default="")
    question_text = Column(Text, default="")
    selected_option = Column(String, default="")
    rationale = Column(Text, default="")
    integrity_score = Column(Float, default=0.0)
    timestamp = Column(DateTime, nullable=False)
    cot = Column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "persona_name": self.persona_name,
            "segment": self.segment,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "selected_option": self.selected_option,
            "rationale": self.rationale,
            "integrity_score": self.integrity_score,
            "timestamp": self.timestamp,
            "cot": self.cot or [],
        }


class ReportModel(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, default="strategy")
    format = Column(String, default="PDF")
    size = Column(String, default="")
    created_at = Column(DateTime, nullable=False)
    sections = Column(JSON, default=list)
    kpis = Column(JSON, default=list)
    charts = Column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "type": self.type,
            "format": self.format,
            "size": self.size,
            "created_at": self.created_at,
            "sections": self.sections or [],
            "kpis": self.kpis or [],
            "charts": self.charts or [],
        }


class RevokedTokenModel(Base):
    __tablename__ = "revoked_tokens"

    token = Column(String, primary_key=True)
    revoked_at = Column(DateTime, nullable=False)