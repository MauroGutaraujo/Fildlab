"""Condiciones contractuales y costo histórico de movimientos.

Revision ID: 20261021_historia
Revises: 20261021_integridad
"""
from alembic import op
import sqlalchemy as sa

revision = "20261021_historia"
down_revision = "20261021_integridad"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contratos", sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_table("condiciones_contrato",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contrato_id", sa.Integer(), sa.ForeignKey("contratos.id"), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("monto_mensual_soles", sa.Numeric(10, 2), nullable=False),
        sa.Column("sla_horas_max_respuesta", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column("registrado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_condiciones_contrato_contrato_id", "condiciones_contrato", ["contrato_id"])
    op.create_index("ix_condiciones_contrato_vigente_desde", "condiciones_contrato", ["vigente_desde"])
    # Congelar lo conocido, sin atribuirle precisión histórica no disponible.
    op.execute("""INSERT INTO condiciones_contrato
        (contrato_id, vigente_desde, fecha_inicio, fecha_fin, monto_mensual_soles, sla_horas_max_respuesta, estado, origen)
        SELECT id, DATE '0001-01-01', fecha_inicio, fecha_fin, monto_mensual_soles,
               sla_horas_max_respuesta, estado, 'BASE_LEGADA' FROM contratos""")
    op.add_column("movimientos_inventario", sa.Column("costo_unitario_soles", sa.Numeric(10, 2), nullable=True))
    op.add_column("movimientos_inventario", sa.Column("costo_historico_confirmado", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("""UPDATE movimientos_inventario AS m SET costo_unitario_soles = r.costo_unitario_soles
        FROM repuestos AS r WHERE r.codigo = m.repuesto_codigo""")
    op.execute("""UPDATE ordenes_servicio AS o SET sla_horas_max_respuesta = c.sla_horas_max_respuesta
        FROM contratos AS c WHERE c.id = o.contrato_id AND o.sla_horas_max_respuesta IS NULL""")


def downgrade():
    op.drop_column("movimientos_inventario", "costo_historico_confirmado")
    op.drop_column("movimientos_inventario", "costo_unitario_soles")
    op.drop_table("condiciones_contrato")
    op.drop_column("contratos", "anulado_en")
