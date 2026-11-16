"""Script para poblar la base de datos de producción con datos simulados realistas
para la empresa Fildlab Perú S.A.C. (sector salud en Trujillo).

Crea:
- Clientes (Clínicas, Hospitales y Laboratorios)
- Contratos de mantenimiento con SLAs de respuesta (2h a 4h)
- Equipos de ósmosis inversa, ablandadores y filtros con parámetros de agua
- Repuestos en almacén central con stock disponible
- Movimientos iniciales de entrada de inventario
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import normalize_async_url
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.repuesto import Repuesto, MovimientoInventario

CLIENTES = [
    {
        "ruc": "20132371981",
        "razon_social": "CLINICA SANCHEZ FERRER S.A.",
        "direccion": "Av. Los Ángeles 612, Urb. California, Trujillo",
    },
    {
        "ruc": "20481977341",
        "razon_social": "ESCALABS CENTRO DE ANALISIS CLINICOS S.A.C.",
        "direccion": "Jr. Ayacucho 445, Centro Histórico, Trujillo",
    },
    {
        "ruc": "20601234567",
        "razon_social": "CENTRO MEDICO HEMODIALISIS LA LIBERTAD S.A.C.",
        "direccion": "Av. América Sur 2140, Trujillo",
    },
    {
        "ruc": "20543210987",
        "razon_social": "LABORATORIO CLINICO ROE TRUJILLO S.A.C.",
        "direccion": "Av. Víctor Larco Herrera 850, Trujillo",
    },
]

REPUESTOS = [
    {
        "codigo": "MEM-RO-4040",
        "descripcion": "Membrana de Ósmosis Inversa Filmtec 4040 (2400 GPD)",
        "stock": 15,
        "costo": Decimal("680.00"),
    },
    {
        "codigo": "FIL-SED-20BB",
        "descripcion": "Cartucho Polipropileno 20\" Big Blue 5 micras",
        "stock": 50,
        "costo": Decimal("45.00"),
    },
    {
        "codigo": "FIL-CTO-20BB",
        "descripcion": "Cartucho Carbón Block 20\" Big Blue 5 micras",
        "stock": 35,
        "costo": Decimal("75.00"),
    },
    {
        "codigo": "RES-CAT-25L",
        "descripcion": "Resina Catiónica Fuerte Purolite C100E (Saco 25L)",
        "stock": 20,
        "costo": Decimal("320.00"),
    },
    {
        "codigo": "LAM-UV-30W",
        "descripcion": "Lámpara Germicida Ultravioleta 30W T5 4 pines",
        "stock": 12,
        "costo": Decimal("180.00"),
    },
    {
        "codigo": "SAL-PEL-25K",
        "descripcion": "Sal en Pellets para Regeneración de Ablandador (Saco 25kg)",
        "stock": 60,
        "costo": Decimal("42.00"),
    },
    {
        "codigo": "BOM-PRO-1/2",
        "descripcion": "Bomba de Paletas Rotativas Procon Serie 2 1/2 HP",
        "stock": 6,
        "costo": Decimal("850.00"),
    },
    {
        "codigo": "MAN-GLI-100",
        "descripcion": "Manómetro Acero Inox con Glicerina 0-100 PSI",
        "stock": 18,
        "costo": Decimal("65.00"),
    },
]


async def poblar_datos(db_url: str) -> None:
    async_url, connect_args = normalize_async_url(db_url)
    engine = create_async_engine(async_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Obtener usuario de Gerencia para registrar movimientos
        gerente = (
            await session.execute(select(Usuario).where(Usuario.rol == "GERENCIA"))
        ).scalars().first()

        if not gerente:
            raise SystemExit(
                "[!] No existe un usuario Gerencia. Créelo primero con "
                "python -m app.scripts.crear_usuarios_iniciales"
            )

        # 1. Clientes
        for c_data in CLIENTES:
            c = (await session.execute(select(Cliente).where(Cliente.ruc == c_data["ruc"]))).scalar_one_or_none()
            if not c:
                c = Cliente(ruc=c_data["ruc"], razon_social=c_data["razon_social"], direccion=c_data["direccion"])
                session.add(c)
                print(f"[+] Cliente creado: {c_data['razon_social']} (RUC: {c_data['ruc']})")
        await session.commit()

        # 2. Contratos
        hoy = date.today()
        contratos_data = [
            {
                "cliente_ruc": "20132371981",
                "fecha_inicio": hoy - timedelta(days=120),
                "fecha_fin": hoy + timedelta(days=245),
                "monto_mensual_soles": Decimal("2850.00"),
                "sla_horas_max_respuesta": 2,
            },
            {
                "cliente_ruc": "20481977341",
                "fecha_inicio": hoy - timedelta(days=60),
                "fecha_fin": hoy + timedelta(days=305),
                "monto_mensual_soles": Decimal("1950.00"),
                "sla_horas_max_respuesta": 4,
            },
            {
                "cliente_ruc": "20601234567",
                "fecha_inicio": hoy - timedelta(days=180),
                "fecha_fin": hoy + timedelta(days=185),
                "monto_mensual_soles": Decimal("3500.00"),
                "sla_horas_max_respuesta": 2,
            },
            {
                "cliente_ruc": "20543210987",
                "fecha_inicio": hoy - timedelta(days=30),
                "fecha_fin": hoy + timedelta(days=335),
                "monto_mensual_soles": Decimal("1400.00"),
                "sla_horas_max_respuesta": 4,
            },
        ]

        contratos_db = []
        for ct in contratos_data:
            existente = (
                await session.execute(
                    select(Contrato).where(
                        Contrato.cliente_ruc == ct["cliente_ruc"],
                        Contrato.estado == "ACTIVO"
                    )
                )
            ).scalar_one_or_none()
            if not existente:
                nuevo = Contrato(**ct)
                session.add(nuevo)
                await session.flush()
                contratos_db.append(nuevo)
                print(f"[+] Contrato creado: ID {nuevo.id} para RUC {nuevo.cliente_ruc} (SLA: {nuevo.sla_horas_max_respuesta}h)")
            else:
                contratos_db.append(existente)
        await session.commit()

        # 3. Equipos
        equipos_data = [
            {
                "serie": "OI-CLIN-001",
                "cliente_ruc": "20132371981",
                "contrato_id": contratos_db[0].id,
                "tipo_sistema": "OSMOSIS_INVERSA",
                "fecha_instalacion": hoy - timedelta(days=365),
                "parametros_nominales": {
                    "tds_entrada_ppm": 420.0,
                    "tds_post_membrana_ppm": 18.0,
                    "tds_producto_final_ppm": 5.0,
                    "ph": 7.2,
                    "conductividad_us_cm": 10.5,
                    "resistividad_mohm_cm": 0.8,
                    "litros_consumidos_red": 120000.0,
                    "litros_agua_pura": 84000.0,
                },
            },
            {
                "serie": "AB-CLIN-002",
                "cliente_ruc": "20132371981",
                "contrato_id": contratos_db[0].id,
                "tipo_sistema": "ABLANDADOR",
                "fecha_instalacion": hoy - timedelta(days=365),
                "parametros_nominales": {
                    "tds_entrada_ppm": 420.0,
                    "tds_post_membrana_ppm": 0.0,
                    "tds_producto_final_ppm": 410.0,
                    "ph": 7.4,
                    "conductividad_us_cm": 650.0,
                    "resistividad_mohm_cm": 0.0,
                    "litros_consumidos_red": 150000.0,
                    "litros_agua_pura": 150000.0,
                },
            },
            {
                "serie": "OI-HEMO-003",
                "cliente_ruc": "20601234567",
                "contrato_id": contratos_db[2].id,
                "tipo_sistema": "OSMOSIS_INVERSA",
                "fecha_instalacion": hoy - timedelta(days=500),
                "parametros_nominales": {
                    "tds_entrada_ppm": 450.0,
                    "tds_post_membrana_ppm": 12.0,
                    "tds_producto_final_ppm": 2.0,
                    "ph": 7.0,
                    "conductividad_us_cm": 4.2,
                    "resistividad_mohm_cm": 1.5,
                    "litros_consumidos_red": 280000.0,
                    "litros_agua_pura": 196000.0,
                },
            },
            {
                "serie": "FIL-LAB-004",
                "cliente_ruc": "20481977341",
                "contrato_id": contratos_db[1].id,
                "tipo_sistema": "FILTRO",
                "fecha_instalacion": hoy - timedelta(days=120),
                "parametros_nominales": {
                    "tds_entrada_ppm": 380.0,
                    "tds_post_membrana_ppm": 0.0,
                    "tds_producto_final_ppm": 375.0,
                    "ph": 7.1,
                    "conductividad_us_cm": 580.0,
                    "resistividad_mohm_cm": 0.0,
                    "litros_consumidos_red": 45000.0,
                    "litros_agua_pura": 45000.0,
                },
            },
        ]

        for eq in equipos_data:
            existente = (await session.execute(select(Equipo).where(Equipo.serie == eq["serie"]))).scalar_one_or_none()
            if not existente:
                nuevo_eq = Equipo(**eq)
                session.add(nuevo_eq)
                print(f"[+] Equipo registrado: Serie {eq['serie']} ({eq['tipo_sistema']})")
        await session.commit()

        # 4. Repuestos e Inventario Central
        for r_data in REPUESTOS:
            rep = (await session.execute(select(Repuesto).where(Repuesto.codigo == r_data["codigo"]))).scalar_one_or_none()
            if not rep:
                rep = Repuesto(
                    codigo=r_data["codigo"],
                    descripcion=r_data["descripcion"],
                    stock_almacen_central=r_data["stock"],
                    costo_unitario_soles=r_data["costo"],
                )
                session.add(rep)
                await session.flush()

                # Registrar movimiento de entrada inicial
                mov = MovimientoInventario(
                    repuesto_codigo=r_data["codigo"],
                    tipo="ENTRADA",
                    cantidad=r_data["stock"],
                    usuario_id=gerente.id,
                )
                session.add(mov)
                print(f"[+] Repuesto añadido: {r_data['codigo']} (Stock: {r_data['stock']})")
        await session.commit()

        print("\n¡Población de datos simulados completada con éxito!")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from app.core.config import get_settings
        url = get_settings().database_url

    asyncio.run(poblar_datos(url))
