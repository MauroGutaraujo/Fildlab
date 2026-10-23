from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PoliticaSupervision(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RUL_", extra="ignore")
    duracion_max_segundos: int = Field(default=600, ge=1, le=3600)
    latido_segundos: int = Field(default=15, ge=1, le=60)
    silencio_segundos: int = Field(default=90, ge=3, le=3600)
    gracia_cron_horas: int = Field(default=2, ge=1, le=12)

    @model_validator(mode="after")
    def margen_de_latido(self):
        if self.silencio_segundos < 3*self.latido_segundos:
            raise ValueError("El silencio debe tolerar al menos tres intervalos de latido")
        return self
