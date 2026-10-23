"""Correcciones auditadas y anulación/restauración de altas de componentes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261023_cambios_componentes"
down_revision = "20261022_supervision_rul"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("componentes_equipo", sa.Column("revision", sa.Integer(), server_default="1", nullable=False))
    op.add_column("componentes_equipo", sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("componentes_revision_check", "componentes_equipo", "revision >= 1")
    op.drop_index("componentes_equipo_nombre_key", table_name="componentes_equipo")
    op.create_index("componentes_equipo_nombre_key", "componentes_equipo", ["equipo_serie", sa.text("lower(nombre)")],
                    unique=True, postgresql_where=sa.text("anulado_en IS NULL"))
    op.create_table(
        "cambios_componentes",
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("componente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("componentes_equipo.id"), nullable=False),
        sa.Column("accion", sa.String(length=24), nullable=False),
        sa.Column("revision_anterior", sa.Integer(), nullable=False),
        sa.Column("revision_nueva", sa.Integer(), nullable=False),
        sa.Column("antes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("despues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("solicitud", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("registrado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("registrado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("accion IN ('CORREGIR','ANULAR_ALTA','RESTABLECER_ALTA')", name="cambios_componentes_accion_check"),
        sa.CheckConstraint("revision_nueva = revision_anterior + 1", name="cambios_componentes_revision_check"),
        sa.CheckConstraint("length(btrim(motivo)) > 0", name="cambios_componentes_motivo_check"),
        sa.UniqueConstraint("componente_id", "revision_nueva", name="cambios_componentes_revision_key"),
    )
    op.create_index("ix_cambios_componentes_componente_id", "cambios_componentes", ["componente_id"])


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS(SELECT 1 FROM cambios_componentes) OR EXISTS(SELECT 1 FROM componentes_equipo WHERE revision <> 1 OR anulado_en IS NOT NULL)")).scalar():
        raise RuntimeError("No se puede revertir: se perderían auditorías, revisiones o estados de anulación de componentes.")
    op.drop_index("ix_cambios_componentes_componente_id", table_name="cambios_componentes")
    op.drop_table("cambios_componentes")
    op.drop_index("componentes_equipo_nombre_key", table_name="componentes_equipo")
    op.create_index("componentes_equipo_nombre_key", "componentes_equipo", ["equipo_serie", sa.text("lower(nombre)")], unique=True)
    op.drop_constraint("componentes_revision_check", "componentes_equipo", type_="check")
    op.drop_column("componentes_equipo", "anulado_en")
    op.drop_column("componentes_equipo", "revision")
