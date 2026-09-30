"""Script para poblar datos de demostración en Ventas y Liquidación de Órdenes.

Crea:
1. Varias ventas con items y salidas de inventario registradas.
2. Órdenes de servicio en estados SINCRONIZADA, COMPROMETIDA y LIQUIDADA con actas inmutables,
   hashes encadenados (tamper-evident ledger), geolocalización GPS y firmas digitales.
3. Adendas de corrección administrativas para demostrar auditoría sin alterar actas originales.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import normalize_async_url, get_settings
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.schemas.liquidacion import AdendaIn, AjusteRepuesto
from app.schemas.orden import LecturasAgua, OrdenSincronizarIn, RepuestoConsumidoIn
from app.schemas.venta import VentaIn, VentaItemIn
from app.services import liquidacion as liq_svc
from app.services import ordenes as ordenes_svc
from app.services import ventas as ventas_svc

# Firma demo en formato data URI (Canvas PNG)
FIRMA_DEMO = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK8AAAA8CAYAAADgQ0W6AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAA"
    "AsTAAALEwEAmpwYAAAAB3RJTUUH5gkDDAwYx0vU8wAAIABJREFUeNrtvXd8HNd17v2ZO7M7W7tY7ALAXhDFXkTR6pUlW5ZkS7bkb"
    "rkl7k7s+97k3hvb8cW2E79xbMtx7Hscx3GLbclFvUSKlUiKTYAESeztvd2ZOfP+2AUWBEiRFH1dfL8ff3Rhds/MnDnnnN/5ls8hh"
    "BCiB11d19F1vef+39X1+51f1fV9d9V9v3/1785Z1/Ue0D3o6upBV1cPuroPXV096OrqQVdXD7q6etDV1YOu/1/V+w3w85/d/e2u"
    "rq4edHX1oKurB11dPejq6kFX/x/rfQf41b/6x/vu/jN19aCrqwd916C/O4T0r9XVg66uHnR19aCrqwd9d4D/H+0bV63w+lD/AAAA"
    "AElFTkSuQmCC"
)


async def poblar_ventas_y_liquidacion(db_url: str):
    async_url, connect_args = normalize_async_url(db_url)
    engine = create_async_engine(async_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Obtener usuarios clave
        gerente = (await session.execute(select(Usuario).where(Usuario.rol == "GERENCIA"))).scalars().first()
        tecnico = (await session.execute(select(Usuario).where(Usuario.rol == "TECNICO"))).scalars().first()

        if not gerente or not tecnico:
            print("[!] Error: Se requieren usuarios GERENCIA y TECNICO. Ejecute primero crear_usuarios_iniciales.")
            return

        print(f"[i] Gerente: {gerente.email} (ID: {gerente.id}) | Técnico: {tecnico.email} (ID: {tecnico.id})")

        # 2. Asegurar stock suficiente en repuestos para ventas y órdenes
        repuestos = (await session.execute(select(Repuesto))).scalars().all()
        for r in repuestos:
            if r.stock_almacen_central < 30:
                r.stock_almacen_central += 50
        await session.commit()

        # =========================================================================
        # SECCIÓN A: VENTAS COMERCIALES
        # =========================================================================
        print("\n--- Registrando Ventas de Demostración ---")
        hoy = datetime.now(timezone.utc)

        ventas_demo = [
            VentaIn(
                cliente_ruc="20132371981",  # Clínica Sánchez Ferrer
                items=[
                    VentaItemIn(repuesto_codigo="FIL-SED-20BB", cantidad=2, precio_unitario_soles=Decimal("65.00")),
                    VentaItemIn(repuesto_codigo="FIL-CTO-20BB", cantidad=2, precio_unitario_soles=Decimal("95.00")),
                ],
            ),
            VentaIn(
                cliente_ruc="20601234567",  # Hemodiálisis La Libertad
                items=[
                    VentaItemIn(repuesto_codigo="MEM-RO-4040", cantidad=1, precio_unitario_soles=Decimal("950.00")),
                    VentaItemIn(repuesto_codigo="SAL-PEL-25K", cantidad=6, precio_unitario_soles=Decimal("60.00")),
                ],
            ),
            VentaIn(
                cliente_ruc="20481977341",  # Escalabs
                items=[
                    VentaItemIn(repuesto_codigo="LAM-UV-30W", cantidad=1, precio_unitario_soles=Decimal("260.00")),
                    VentaItemIn(repuesto_codigo="FIL-SED-20BB", cantidad=3, precio_unitario_soles=Decimal("65.00")),
                ],
            ),
            VentaIn(
                cliente_ruc="20543210987",  # Laboratorio Roe
                items=[
                    VentaItemIn(repuesto_codigo="SAL-PEL-25K", cantidad=4, precio_unitario_soles=Decimal("60.00")),
                    VentaItemIn(repuesto_codigo="FIL-CTO-20BB", cantidad=1, precio_unitario_soles=Decimal("95.00")),
                ],
            ),
        ]

        for v_in in ventas_demo:
            try:
                v = await ventas_svc.crear_venta(session, v_in, gerente.id)
                print(f"[+] Venta registrada: ID {v.id} para RUC {v.cliente_ruc} - Total: S/ {v.total_soles}")
            except Exception as e:
                print(f"[-] Error al registrar venta para RUC {v_in.cliente_ruc}: {e}")

        await session.commit()

        # =========================================================================
        # SECCIÓN B: ÓRDENES DE SERVICIO PARA LIQUIDACIÓN
        # =========================================================================
        print("\n--- Registrando Órdenes de Servicio para Demostración de Liquidación ---")

        # Orden 1: SINCRONIZADA (Lista para demostración en vivo de liquidación)
        orden1_id = uuid.uuid4()
        orden1_in = OrdenSincronizarIn(
            id=orden1_id,
            contrato_id=1,
            equipo_serie="OI-CLIN-001",
            tecnico_id=tecnico.id,
            tipo_intervencion="PREVENTIVO",
            fecha_creacion_cliente=hoy - timedelta(hours=3),
            lecturas_agua=LecturasAgua(
                tds_entrada_ppm=425.0,
                tds_post_membrana_ppm=15.0,
                tds_producto_final_ppm=4.8,
                ph=7.15,
                conductividad_us_cm=9.8,
                resistividad_mohm_cm=0.95,
                litros_consumidos_red=145000.0,
                litros_agua_pura=102000.0,
            ),
            firma_base64=FIRMA_DEMO,
            gps_latitud=Decimal("-8.1124500"),
            gps_longitud=Decimal("-79.0315200"),
            repuestos_consumidos=[
                RepuestoConsumidoIn(repuesto_codigo="FIL-SED-20BB", cantidad=1),
                RepuestoConsumidoIn(repuesto_codigo="FIL-CTO-20BB", cantidad=1),
            ],
        )

        o1 = await ordenes_svc.sincronizar_orden(session, orden1_in, gerente)
        print(f"[+] Orden 1 (SINCRONIZADA): {o1.id} - Equipo {o1.equipo_serie} - Botón Liquidar activo en Web")

        # Orden 2: SINCRONIZADA (Segundo servicio sobre OI-CLIN-001 para mostrar encadenamiento SHA-256)
        orden2_id = uuid.uuid4()
        orden2_in = OrdenSincronizarIn(
            id=orden2_id,
            contrato_id=1,
            equipo_serie="OI-CLIN-001",
            tecnico_id=tecnico.id,
            tipo_intervencion="CORRECTIVO",
            fecha_creacion_cliente=hoy - timedelta(hours=1),
            lecturas_agua=LecturasAgua(
                tds_entrada_ppm=430.0,
                tds_post_membrana_ppm=17.5,
                tds_producto_final_ppm=5.1,
                ph=7.20,
                conductividad_us_cm=10.2,
                resistividad_mohm_cm=0.91,
                litros_consumidos_red=146200.0,
                litros_agua_pura=103100.0,
            ),
            firma_base64=FIRMA_DEMO,
            gps_latitud=Decimal("-8.1124800"),
            gps_longitud=Decimal("-79.0315500"),
            repuestos_consumidos=[
                RepuestoConsumidoIn(repuesto_codigo="LAM-UV-30W", cantidad=1),
            ],
        )
        o2 = await ordenes_svc.sincronizar_orden(session, orden2_in, gerente)
        print(f"[+] Orden 2 (SINCRONIZADA): {o2.id} - Encadenada a Orden 1 por hash SHA-256")

        # Orden 3: LIQUIDADA (Para mostrar orden auditada y cerrada por Gerencia)
        orden3_id = uuid.uuid4()
        orden3_in = OrdenSincronizarIn(
            id=orden3_id,
            contrato_id=3,
            equipo_serie="OI-HEMO-003",
            tecnico_id=tecnico.id,
            tipo_intervencion="PREVENTIVO",
            fecha_creacion_cliente=hoy - timedelta(days=2),
            lecturas_agua=LecturasAgua(
                tds_entrada_ppm=450.0,
                tds_post_membrana_ppm=11.8,
                tds_producto_final_ppm=2.1,
                ph=7.05,
                conductividad_us_cm=4.3,
                resistividad_mohm_cm=1.45,
                litros_consumidos_red=285000.0,
                litros_agua_pura=199500.0,
            ),
            firma_base64=FIRMA_DEMO,
            gps_latitud=Decimal("-8.1089200"),
            gps_longitud=Decimal("-79.0352100"),
            repuestos_consumidos=[
                RepuestoConsumidoIn(repuesto_codigo="MEM-RO-4040", cantidad=1),
                RepuestoConsumidoIn(repuesto_codigo="FIL-SED-20BB", cantidad=2),
            ],
        )
        o3 = await ordenes_svc.sincronizar_orden(session, orden3_in, gerente)
        await session.commit()
        # Liquidar orden 3
        o3_liq = await liq_svc.liquidar(session, o3.id)
        print(f"[+] Orden 3 (LIQUIDADA): {o3_liq.id} - Equipo {o3_liq.equipo_serie} - Estado consolidado")

        # Orden 4: LIQUIDADA con ADENDA ADMINISTRATIVA (Muestra corrección sin alterar acta)
        orden4_id = uuid.uuid4()
        orden4_in = OrdenSincronizarIn(
            id=orden4_id,
            contrato_id=1,
            equipo_serie="AB-CLIN-002",
            tecnico_id=tecnico.id,
            tipo_intervencion="CORRECTIVO",
            fecha_creacion_cliente=hoy - timedelta(days=3),
            lecturas_agua=LecturasAgua(
                tds_entrada_ppm=420.0,
                tds_post_membrana_ppm=0.0,
                tds_producto_final_ppm=415.0,
                ph=7.35,
                conductividad_us_cm=640.0,
                resistividad_mohm_cm=0.0,
                litros_consumidos_red=158000.0,
                litros_agua_pura=158000.0,
            ),
            firma_base64=FIRMA_DEMO,
            gps_latitud=Decimal("-8.1124300"),
            gps_longitud=Decimal("-79.0315100"),
            repuestos_consumidos=[
                RepuestoConsumidoIn(repuesto_codigo="SAL-PEL-25K", cantidad=2),
            ],
        )
        o4 = await ordenes_svc.sincronizar_orden(session, orden4_in, gerente)
        await session.commit()
        await liq_svc.liquidar(session, o4.id)

        # Crear Adenda de corrección
        adenda_data = AdendaIn(
            observacion=(
                "Auditoría técnica: Se verificó con jefatura médica que el técnico utilizó 1 saco adicional "
                "de Sal en Pellets SAL-PEL-25K por regeneración exhaustiva de resina. Se regulariza el consumo en inventario."
            ),
            ajuste_repuestos=[
                AjusteRepuesto(repuesto_codigo="SAL-PEL-25K", delta=-1)
            ]
        )
        ad = await liq_svc.crear_adenda(session, o4.id, gerente.id, adenda_data)
        print(f"[+] Orden 4 (LIQUIDADA CON ADENDA): {o4.id} - Adenda ID {ad.id} vinculada exitosamente")

        # Orden 5: COMPROMETIDA (Para mostrar el estado intermedio)
        orden5_id = uuid.uuid4()
        orden5_in = OrdenSincronizarIn(
            id=orden5_id,
            contrato_id=2,
            equipo_serie="FIL-LAB-004",
            tecnico_id=tecnico.id,
            tipo_intervencion="PREVENTIVO",
            fecha_creacion_cliente=hoy - timedelta(hours=5),
            lecturas_agua=LecturasAgua(
                tds_entrada_ppm=385.0,
                tds_post_membrana_ppm=0.0,
                tds_producto_final_ppm=380.0,
                ph=7.10,
                conductividad_us_cm=590.0,
                resistividad_mohm_cm=0.0,
                litros_consumidos_red=48000.0,
                litros_agua_pura=48000.0,
            ),
            firma_base64=FIRMA_DEMO,
            gps_latitud=Decimal("-8.1156200"),
            gps_longitud=Decimal("-79.0298100"),
            repuestos_consumidos=[
                RepuestoConsumidoIn(repuesto_codigo="FIL-SED-20BB", cantidad=1),
            ],
        )
        o5 = await ordenes_svc.sincronizar_orden(session, orden5_in, gerente)
        o5_db = await session.get(OrdenServicio, o5.id)
        o5_db.estado = "COMPROMETIDA"
        await session.commit()
        print(f"[+] Orden 5 (COMPROMETIDA): {o5.id} - Equipo {o5.equipo_serie} - Consumibles en tránsito")

        await session.commit()
        print("\n[OK] ¡Datos de demostración para Ventas y Liquidación insertados con éxito!")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = get_settings().database_url

    asyncio.run(poblar_ventas_y_liquidacion(url))
