from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "digital-twin-backend"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/digital_twin"

    JWT_SECRET_KEY: str = "dev-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PERSONAS_JSON_PATH: str = "../digital-twin-ai/output/personas.json"
    AI_PIPELINE_PROJECT_DIR: str = "digital-twin-ai"
    AI_PIPELINE_OUTPUT_DIR: str = "output"
    AI_PIPELINE_EXCEL_PATH: str = "data/Digital Customer Twin.xlsx"
    AI_SERVICE_BASE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT_SECONDS: float = 300.0
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    DEFAULT_ADMIN_EMAIL: str = "admin@digital-twin.ai"
    DEFAULT_ADMIN_PASSWORD: str = "Admin1234!"
    DEFAULT_ADMIN_NAME: str = "Digital Twin Admin"

    GEMINI_API_KEY: str = ""
    GCP_PROJECT_ID: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env"}


settings = Settings()
