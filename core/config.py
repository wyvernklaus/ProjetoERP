from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Segurança
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"

    # E-mail
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_REMETENTE: str = ""
    EMAIL_SENHA_APP: str = ""

    # Ambiente
    AMBIENTE: str = "desenvolvimento"
    URL_BASE: str = "http://localhost:1687"

    # Cookie
    COOKIE_SECURE: bool = False
    COOKIE_MAX_AGE_HORAS: int = 12

    @property
    def producao(self) -> bool:
        return self.AMBIENTE.lower() == "producao"

settings = Settings()