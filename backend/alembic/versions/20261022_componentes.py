"""Historial de componentes y referencia explícita del cálculo RUL.

Revision ID: 20261022_componentes
Revises: 20261022_rul
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261022_componentes"
down_revision = "20261022_rul"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("componentes_equipo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("equipo_serie", sa.String(50), sa.ForeignKey("equipos.serie"), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("tipo_componente", sa.String(20), nullable=False),
        sa.Column("fecha_instalacion", sa.Date(), nullable=True),
        sa.Column("fabricante_modelo", sa.String(120), nullable=True),
        sa.Column("creado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo_componente IN ('MEMBRANA','FILTRO','RESINA','OTRO')", name="componentes_tipo_check"),
        sa.CheckConstraint("length(btrim(nombre)) > 0", name="componentes_nombre_check"))
    op.create_index("ix_componentes_equipo_equipo_serie", "componentes_equipo", ["equipo_serie"])
    op.create_index("componentes_equipo_nombre_key", "componentes_equipo", ["equipo_serie", sa.text("lower(nombre)")], unique=True)
    op.create_table("intervenciones_componente",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("componente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("componentes_equipo.id"), nullable=False),
        sa.Column("orden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ordenes_servicio.id"), nullable=False),
        sa.Column("acta_hash", sa.String(64), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("fecha_efectiva", sa.Date(), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=False),
        sa.Column("registrado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo IN ('INSPECCION','LIMPIEZA','REPARACION_PARCIAL','SUSTITUCION')", name="intervenciones_tipo_check"),
        sa.CheckConstraint("length(btrim(observacion)) > 0", name="intervenciones_observacion_check"))
    op.create_index("ix_intervenciones_componente_componente_id", "intervenciones_componente", ["componente_id"])
    op.create_index("ix_intervenciones_componente_orden_id", "intervenciones_componente", ["orden_id"])
    op.create_table("anulaciones_intervencion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("intervencion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("intervenciones_componente.id"), nullable=False, unique=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("registrado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(btrim(motivo)) > 0", name="anulaciones_motivo_check"))
    op.add_column("predicciones_rul", sa.Column("fecha_referencia", sa.Date(), nullable=True))
    # Fecha legada de mantenimiento y actas intactas: no se infiere ninguna sustitución.


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM componentes_equipo")).scalar():
        raise RuntimeError("No se puede revertir: existe historial de componentes. Conservar respaldo y resolverlo antes del downgrade.")
    op.drop_column("predicciones_rul", "fecha_referencia")
    op.drop_table("anulaciones_intervencion")
    op.drop_table("intervenciones_componente")
    op.drop_table("componentes_equipo")
