"""Script para actualizar la base de datos de producción con las 5 empresas reales de Fildlab
y sus 10 equipos de tratamiento de agua con los parámetros físico-químicos clínicos exactos:
- Bermalab (2 equipos)
- Escalabs (2 equipos)
- Sano del Norte (1 equipo)
- Detectalab (1 equipo)
- Inkamay (4 equipos)

Parámetros clínicos validados:
- TDS entrada: > 300 ppm
- TDS post-membrana: 4 - 15 ppm
- TDS salida: 0.04 - 0.5 ppm
- Conductividad: < 0.5 µS/cm
- Resistividad: > 3 MΩ·cm
- pH: 6.5 - 7.5
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import normalize_async_url
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.equipo import Equipo

EMPRESAS_DATA = [
    {
        "cliente": {
            "ruc": "20603456781",
            "razon_social": "BERMALAB LABORATORIO CLINICO ESPECIALIZADO S.A.C.",
            "direccion": "Av. Mansiche 814, Urb. Santa Inés, Trujillo",
        },
        "contrato": {
            "monto_mensual_soles": Decimal("2200.00"),
            "sla_horas_max_respuesta": 4,
        },
        "equipos": [
            {
                "serie": "OI-BERM-001",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 240,
                "parametros": {
                    "tds_entrada_ppm": 395.0,
                    "tds_post_membrana_ppm": 8.5,
                    "tds_producto_final_ppm": 0.12,
                    "ph": 6.9,
                    "conductividad_us_cm": 0.24,
                    "resistividad_mohm_cm": 5.8,
                    "litros_consumidos_red": 96000.0,
                    "litros_agua_pura": 67200.0,
                },
            },
            {
                "serie": "AB-BERM-002",
                "tipo_sistema": "ABLANDADOR",
                "antiguedad_dias": 240,
                "parametros": {
                    "tds_entrada_ppm": 395.0,
                    "tds_post_membrana_ppm": 0.0,
                    "tds_producto_final_ppm": 390.0,
                    "ph": 7.3,
                    "conductividad_us_cm": 610.0,
                    "resistividad_mohm_cm": 0.0,
                    "litros_consumidos_red": 115000.0,
                    "litros_agua_pura": 115000.0,
                },
            },
        ],
    },
    {
        "cliente": {
            "ruc": "20481977341",
            "razon_social": "ESCALABS CENTRO DE ANALISIS CLINICOS S.A.C.",
            "direccion": "Jr. Ayacucho 445, Centro Histórico, Trujillo",
        },
        "contrato": {
            "monto_mensual_soles": Decimal("2400.00"),
            "sla_horas_max_respuesta": 4,
        },
        "equipos": [
            {
                "serie": "OI-ESCA-001",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 310,
                "parametros": {
                    "tds_entrada_ppm": 410.0,
                    "tds_post_membrana_ppm": 6.8,
                    "tds_producto_final_ppm": 0.08,
                    "ph": 7.0,
                    "conductividad_us_cm": 0.16,
                    "resistividad_mohm_cm": 8.5,
                    "litros_consumidos_red": 145000.0,
                    "litros_agua_pura": 101500.0,
                },
            },
            {
                "serie": "OI-ESCA-002",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 180,
                "parametros": {
                    "tds_entrada_ppm": 410.0,
                    "tds_post_membrana_ppm": 5.2,
                    "tds_producto_final_ppm": 0.05,
                    "ph": 7.1,
                    "conductividad_us_cm": 0.10,
                    "resistividad_mohm_cm": 11.2,
                    "litros_consumidos_red": 72000.0,
                    "litros_agua_pura": 50400.0,
                },
            },
        ],
    },
    {
        "cliente": {
            "ruc": "20608765432",
            "razon_social": "POLICLINICO SANO DEL NORTE S.A.C.",
            "direccion": "Av. Túpac Amaru 1250, Alto Mochica, Trujillo",
        },
        "contrato": {
            "monto_mensual_soles": Decimal("1800.00"),
            "sla_horas_max_respuesta": 4,
        },
        "equipos": [
            {
                "serie": "OI-SANO-001",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 150,
                "parametros": {
                    "tds_entrada_ppm": 360.0,
                    "tds_post_membrana_ppm": 9.4,
                    "tds_producto_final_ppm": 0.18,
                    "ph": 6.8,
                    "conductividad_us_cm": 0.35,
                    "resistividad_mohm_cm": 4.5,
                    "litros_consumidos_red": 68000.0,
                    "litros_agua_pura": 47600.0,
                },
            },
        ],
    },
    {
        "cliente": {
            "ruc": "20609871234",
            "razon_social": "DETECTALAB LABORATORIO DE BIOLOGIA MOLECULAR S.A.C.",
            "direccion": "Av. Juan Pablo II 420, Urb. San Andrés, Trujillo",
        },
        "contrato": {
            "monto_mensual_soles": Decimal("2600.00"),
            "sla_horas_max_respuesta": 2,  # Crítico
        },
        "equipos": [
            {
                "serie": "OI-DETEC-001",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 90,
                "parametros": {
                    "tds_entrada_ppm": 340.0,
                    "tds_post_membrana_ppm": 4.5,
                    "tds_producto_final_ppm": 0.04,
                    "ph": 7.0,
                    "conductividad_us_cm": 0.08,
                    "resistividad_mohm_cm": 15.6,
                    "litros_consumidos_red": 38000.0,
                    "litros_agua_pura": 26600.0,
                },
            },
        ],
    },
    {
        "cliente": {
            "ruc": "20605678912",
            "razon_social": "CENTRO MEDICO INTEGRAL INKAMAY S.A.C.",
            "direccion": "Av. Huamán 530, Víctor Larco Herrera, Trujillo",
        },
        "contrato": {
            "monto_mensual_soles": Decimal("4800.00"),
            "sla_horas_max_respuesta": 2,  # Crítico
        },
        "equipos": [
            {
                "serie": "OI-INKA-001",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 420,
                "parametros": {
                    "tds_entrada_ppm": 435.0,
                    "tds_post_membrana_ppm": 11.8,
                    "tds_producto_final_ppm": 0.22,
                    "ph": 7.1,
                    "conductividad_us_cm": 0.42,
                    "resistividad_mohm_cm": 3.8,
                    "litros_consumidos_red": 240000.0,
                    "litros_agua_pura": 168000.0,
                },
            },
            {
                "serie": "OI-INKA-002",
                "tipo_sistema": "OSMOSIS_INVERSA",
                "antiguedad_dias": 210,
                "parametros": {
                    "tds_entrada_ppm": 435.0,
                    "tds_post_membrana_ppm": 7.2,
                    "tds_producto_final_ppm": 0.09,
                    "ph": 6.9,
                    "conductividad_us_cm": 0.18,
                    "resistividad_mohm_cm": 7.2,
                    "litros_consumidos_red": 110000.0,
                    "litros_agua_pura": 77000.0,
                },
            },
            {
                "serie": "AB-INKA-003",
                "tipo_sistema": "ABLANDADOR",
                "antiguedad_dias": 420,
                "parametros": {
                    "tds_entrada_ppm": 435.0,
                    "tds_post_membrana_ppm": 0.0,
                    "tds_producto_final_ppm": 425.0,
                    "ph": 7.4,
                    "conductividad_us_cm": 680.0,
                    "resistividad_mohm_cm": 0.0,
                    "litros_consumidos_red": 320000.0,
                    "litros_agua_pura": 320000.0,
                },
            },
            {
                "serie": "FIL-INKA-004",
                "tipo_sistema": "FILTRO",
                "antiguedad_dias": 420,
                "parametros": {
                    "tds_entrada_ppm": 435.0,
                    "tds_post_membrana_ppm": 0.0,
                    "tds_producto_final_ppm": 430.0,
                    "ph": 7.2,
                    "conductividad_us_cm": 670.0,
                    "resistividad_mohm_cm": 0.0,
                    "litros_consumidos_red": 350000.0,
                    "litros_agua_pura": 350000.0,
                },
            },
        ],
    },
]


async def poblar_empresas(db_url: str) -> None:
    async_url, connect_args = normalize_async_url(db_url)
    engine = create_async_engine(async_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    hoy = date.today()

    async with session_factory() as session:
        print("Iniciando actualización de las 5 empresas y sus 10 equipos...\n")

        for emp in EMPRESAS_DATA:
            # 1. Asegurar Cliente
            c_info = emp["cliente"]
            cliente = (await session.execute(select(Cliente).where(Cliente.ruc == c_info["ruc"]))).scalar_one_or_none()
            if not cliente:
                cliente = Cliente(**c_info)
                session.add(cliente)
                print(f"[+] Cliente creado: {cliente.razon_social} (RUC: {cliente.ruc})")
            else:
                cliente.razon_social = c_info["razon_social"]
                cliente.direccion = c_info["direccion"]
                print(f"[*] Cliente actualizado: {cliente.razon_social}")
            await session.flush()

            # 2. Asegurar Contrato
            ct_info = emp["contrato"]
            contrato = (
                await session.execute(
                    select(Contrato).where(Contrato.cliente_ruc == cliente.ruc, Contrato.estado == "ACTIVO")
                )
            ).scalar_one_or_none()

            if not contrato:
                contrato = Contrato(
                    cliente_ruc=cliente.ruc,
                    fecha_inicio=hoy - timedelta(days=180),
                    fecha_fin=hoy + timedelta(days=185),
                    monto_mensual_soles=ct_info["monto_mensual_soles"],
                    sla_horas_max_respuesta=ct_info["sla_horas_max_respuesta"],
                    estado="ACTIVO",
                )
                session.add(contrato)
                await session.flush()
                print(f"    [+] Contrato creado: ID {contrato.id} (SLA: {contrato.sla_horas_max_respuesta}h)")
            else:
                contrato.monto_mensual_soles = ct_info["monto_mensual_soles"]
                contrato.sla_horas_max_respuesta = ct_info["sla_horas_max_respuesta"]

            # 3. Asegurar Equipos
            for eq_data in emp["equipos"]:
                equipo = (await session.execute(select(Equipo).where(Equipo.serie == eq_data["serie"]))).scalar_one_or_none()
                f_instalacion = hoy - timedelta(days=eq_data["antiguedad_dias"])
                if not equipo:
                    equipo = Equipo(
                        serie=eq_data["serie"],
                        cliente_ruc=cliente.ruc,
                        contrato_id=contrato.id,
                        tipo_sistema=eq_data["tipo_sistema"],
                        fecha_instalacion=f_instalacion,
                        parametros_nominales=eq_data["parametros"],
                    )
                    session.add(equipo)
                    print(f"        [+] Equipo registrado: {equipo.serie} ({equipo.tipo_sistema}) - TDS Salida: {eq_data['parametros']['tds_producto_final_ppm']} ppm, Res: {eq_data['parametros']['resistividad_mohm_cm']} Mohm-cm")
                else:
                    equipo.cliente_ruc = cliente.ruc
                    equipo.contrato_id = contrato.id
                    equipo.tipo_sistema = eq_data["tipo_sistema"]
                    equipo.parametros_nominales = eq_data["parametros"]
                    print(f"        [*] Equipo actualizado: {equipo.serie} ({equipo.tipo_sistema})")

            await session.commit()

        print("\n¡Las 5 empresas y sus 10 equipos han sido cargados con éxito!")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from app.core.config import get_settings
        url = get_settings().database_url

    asyncio.run(poblar_empresas(url))
