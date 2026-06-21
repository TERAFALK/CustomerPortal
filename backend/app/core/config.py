from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Databas
    DATABASE_URL: str = "postgresql+asyncpg://insight:insight@db:5432/insight"

    # App-säkerhet
    SECRET_KEY: str = "dev-secret-byt-i-produktion"
    # Generera med: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Tillåtna CORS-origins (kommaseparerade i .env, t.ex. "https://portal.terafalk.com")
    ALLOWED_ORIGINS: list[str] = ["http://localhost", "http://localhost:3000"]

    # Microsoft Graph — TERAFALK:s avsändar-app (single-tenant, för e-post)
    GRAPH_TENANT_ID: str = ""
    GRAPH_CLIENT_ID: str = ""
    GRAPH_CLIENT_SECRET: str = ""
    GRAPH_SENDER: str = "noreply@terafalk.com"

    # Microsoft 365 kundintegration — TERAFALK:s multi-tenant app
    MS_APP_CLIENT_ID: str = ""
    MS_APP_CLIENT_SECRET: str = ""
    MS_APP_REDIRECT_URI: str = ""  # t.ex. https://insight.terafalk.com/api/auth/microsoft/callback

    # Första admin
    FIRST_ADMIN_EMAIL: str = "admin@terafalk.com"
    FIRST_ADMIN_PASSWORD: str = "changeme"

    # Rapport-output
    REPORTS_OUTPUT_DIR: str = "/app/reports_output"

    # Schemaläggning (cron-format: dag i månaden, timme, minut)
    REPORT_SCHEDULE_DAY: int = 1
    REPORT_SCHEDULE_HOUR: int = 8
    REPORT_SCHEDULE_MINUTE: int = 0


settings = Settings()
