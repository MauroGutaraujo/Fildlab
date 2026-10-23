from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PoliticaVigencia(BaseSettings):
    # El batch no requiere secretos JWT ni lee .env para esta política.
    model_config = SettingsConfigDict(env_prefix="RUL_", extra="ignore")
    vigencia_horas: int = Field(default=48, ge=1, le=168)
