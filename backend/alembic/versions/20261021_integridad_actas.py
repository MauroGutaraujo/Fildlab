"""Cabeza/secuencia por equipo y fechas SLA de las nuevas actas.

Revision ID: 20261021_integridad
Revises: 7fe488f9399d
"""
from alembic import op
import sqlalchemy as sa

revision = "20261021_integridad"
down_revision = "7fe488f9399d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("equipos", sa.Column("ultimo_hash_acta", sa.String(64), nullable=True))
    op.add_column("equipos", sa.Column("secuencia_acta", sa.BigInteger(), server_default="0", nullable=False))
    op.add_column("actas_inmutables", sa.Column("equipo_serie", sa.String(50), nullable=True))
    op.add_column("actas_inmutables", sa.Column("secuencia", sa.BigInteger(), nullable=True))
    op.create_foreign_key("actas_inmutables_equipo_serie_fkey", "actas_inmutables", "equipos", ["equipo_serie"], ["serie"])
    op.create_unique_constraint("actas_equipo_secuencia_key", "actas_inmutables", ["equipo_serie", "secuencia"])
    op.add_column("ordenes_servicio", sa.Column("fecha_solicitud", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordenes_servicio", sa.Column("fecha_primera_atencion", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordenes_servicio", sa.Column("sla_horas_max_respuesta", sa.Integer(), nullable=True))
    op.alter_column("ordenes_servicio", "tiempo_respuesta_horas", existing_type=sa.Numeric(5, 2), type_=sa.Numeric(12, 2))
    op.create_check_constraint("ordenes_fechas_sla_check", "ordenes_servicio",
        "(fecha_solicitud IS NULL AND fecha_primera_atencion IS NULL) OR "
        "(fecha_solicitud IS NOT NULL AND fecha_primera_atencion IS NOT NULL "
        "AND fecha_solicitud <= fecha_primera_atencion AND fecha_primera_atencion <= fecha_creacion_cliente)")
    # No UPDATE a actas: payload/hash y enlaces antiguos se conservan byte por byte.
    # La inserción se serializaba bajo equipo; id (no now()) identifica su última inserción.
    op.execute(sa.text("""
        UPDATE equipos e SET
            ultimo_hash_acta = (SELECT a.hash_sha256 FROM actas_inmutables a
                JOIN ordenes_servicio o ON o.id = a.orden_id
                WHERE o.equipo_serie = e.serie ORDER BY a.id DESC LIMIT 1),
            secuencia_acta = (SELECT count(*) FROM actas_inmutables a
                JOIN ordenes_servicio o ON o.id = a.orden_id WHERE o.equipo_serie = e.serie)
    """))


def downgrade() -> None:
    op.drop_constraint("ordenes_fechas_sla_check", "ordenes_servicio", type_="check")
    # PostgreSQL rechaza el downgrade si alguna respuesta no cabe, sin truncar datos.
    op.alter_column("ordenes_servicio", "tiempo_respuesta_horas", existing_type=sa.Numeric(12, 2), type_=sa.Numeric(5, 2))
    op.drop_column("ordenes_servicio", "sla_horas_max_respuesta")
    op.drop_column("ordenes_servicio", "fecha_primera_atencion")
    op.drop_column("ordenes_servicio", "fecha_solicitud")
    op.drop_constraint("actas_equipo_secuencia_key", "actas_inmutables", type_="unique")
    op.drop_constraint("actas_inmutables_equipo_serie_fkey", "actas_inmutables", type_="foreignkey")
    op.drop_column("actas_inmutables", "secuencia")
    op.drop_column("actas_inmutables", "equipo_serie")
    op.drop_column("equipos", "secuencia_acta")
    op.drop_column("equipos", "ultimo_hash_acta")
