import base64
import binascii
import uuid
from decimal import Decimal
from io import BytesIO
from typing import Annotated

from PIL import Image, UnidentifiedImageError
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import NonBlank
from app.schemas.inventario import Codigo

# Duplicados deliberadamente de app/schemas/equipo.py: una lectura de una orden no es
# lo mismo que la ficha técnica de referencia de un equipo, aunque comparten forma.
NoNegativo = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Ph = Annotated[float, Field(ge=0, le=14)]
Latitud = Annotated[Decimal, Field(ge=-90, le=90)]
Longitud = Annotated[Decimal, Field(ge=-180, le=180)]
Serie = Annotated[str, Field(min_length=1, max_length=50)]
IdPositivo = Annotated[int, Field(gt=0)]
MAX_FIRMA_BYTES = 512 * 1024


class LecturasAgua(BaseModel):
    """RN-02: los 8 parámetros físico-químicos y volumétricos obligatorios para cerrar una orden."""

    tds_entrada_ppm: NoNegativo
    tds_post_membrana_ppm: NoNegativo
    tds_producto_final_ppm: NoNegativo
    ph: Ph
    conductividad_us_cm: NoNegativo
    resistividad_mohm_cm: NoNegativo
    litros_consumidos_red: NoNegativo
    litros_agua_pura: NoNegativo


class RepuestoConsumidoIn(BaseModel):
    repuesto_codigo: Codigo
    cantidad: Annotated[int, Field(gt=0)]


class OrdenSincronizarIn(BaseModel):
    id: uuid.UUID
    contrato_id: IdPositivo
    equipo_serie: Serie
    tecnico_id: IdPositivo
    tipo_intervencion: NonBlank
    fecha_creacion_cliente: AwareDatetime
    fecha_solicitud: AwareDatetime | None = None
    fecha_primera_atencion: AwareDatetime | None = None
    lecturas_agua: LecturasAgua
    firma_base64: NonBlank
    gps_latitud: Latitud
    gps_longitud: Longitud
    repuestos_consumidos: list[RepuestoConsumidoIn] = []

    model_config = ConfigDict(extra="ignore")

    @field_validator("firma_base64")
    @classmethod
    def _firma_png_valida(cls, firma: str) -> str:
        encoded = firma
        if firma.startswith("data:"):
            prefix = "data:image/png;base64,"
            if not firma.startswith(prefix):
                raise ValueError("La firma debe ser una imagen PNG")
            encoded = firma[len(prefix):]
        if len(encoded) > 4 * ((MAX_FIRMA_BYTES + 2) // 3):
            raise ValueError("La firma supera 512 KiB")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("La firma no contiene base64 válido") from None
        if len(raw) > MAX_FIRMA_BYTES:
            raise ValueError("La firma supera 512 KiB")
        try:
            with Image.open(BytesIO(raw)) as image:
                width, height = image.size
                if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("La firma debe ser un PNG estático")
                if not (16 <= width <= 2048 and 16 <= height <= 2048) or width * height > 2_000_000:
                    raise ValueError("Dimensiones de firma no permitidas (16–2048 px, máximo 2 megapíxeles)")
                image.verify()
            with Image.open(BytesIO(raw)) as image:
                image.load()
                visible = Image.new("RGBA", image.size, "white")
                visible.alpha_composite(image.convert("RGBA"))
                if all(low == high for low, high in visible.convert("RGB").getextrema()):
                    raise ValueError("La firma está vacía: dibuja un trazo visible")
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
            raise ValueError("La firma no es un PNG íntegro y decodificable") from None
        return firma

    @model_validator(mode="after")
    def _fechas_sla_coherentes(self):
        if (self.fecha_solicitud is None) != (self.fecha_primera_atencion is None):
            raise ValueError("Indica tanto fecha_solicitud como fecha_primera_atencion, o ninguna")
        if self.fecha_solicitud is not None:
            if not self.fecha_solicitud <= self.fecha_primera_atencion <= self.fecha_creacion_cliente:
                raise ValueError("Las fechas deben cumplir solicitud ≤ primera atención ≤ cierre del servicio")
        return self
