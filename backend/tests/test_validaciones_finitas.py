import pytest
from pydantic import ValidationError

from app.schemas.equipo import ParametrosNominales
from app.schemas.orden import LecturasAgua


@pytest.mark.parametrize("schema", [LecturasAgua, ParametrosNominales])
@pytest.mark.parametrize("valor", [float("inf"), float("-inf"), float("nan")])
def test_lecturas_y_referencias_rechazan_no_finitos(schema, valor):
    datos = dict(tds_entrada_ppm=valor, tds_post_membrana_ppm=8, tds_producto_final_ppm=5, ph=7,
                 conductividad_us_cm=15, resistividad_mohm_cm=1.2, litros_consumidos_red=500, litros_agua_pura=420)
    with pytest.raises(ValidationError):
        schema(**datos)
