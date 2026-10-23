"""Ejecuciones y resultados RUL anexos; vigencia operativa explícita.

Revision ID: 20261022_historial_rul
Revises: 20261022_componentes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20261022_historial_rul"
down_revision = "20261022_componentes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ejecuciones_rul",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("iniciado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizado_en", sa.DateTime(timezone=True)),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("version_calculo", sa.String(40), nullable=False),
        sa.Column("version_dataset", sa.String(40), nullable=False),
        sa.Column("politica_alerta", sa.String(40), nullable=False),
        sa.Column("dataset_sha256", sa.String(64)),
        sa.Column("entorno", pg.JSONB(), nullable=False),
        sa.Column("vigencia_horas", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("estimadas", sa.Integer(), nullable=False),
        sa.Column("abstenciones", sa.Integer(), nullable=False),
        sa.Column("error_codigo", sa.String(40)),
        sa.CheckConstraint("estado IN ('EN_CURSO','COMPLETADA','FALLIDA','OMITIDA_CONCURRENCIA')", name="ejecuciones_rul_estado_check"),
        sa.CheckConstraint("vigencia_horas BETWEEN 1 AND 168", name="ejecuciones_rul_vigencia_check"),
        sa.CheckConstraint("total >= 0 AND estimadas >= 0 AND abstenciones >= 0 AND total = estimadas + abstenciones", name="ejecuciones_rul_totales_check"),
        sa.CheckConstraint("(estado = 'EN_CURSO' AND finalizado_en IS NULL) OR (estado <> 'EN_CURSO' AND finalizado_en >= iniciado_en)", name="ejecuciones_rul_fechas_check"))
    op.create_index("ix_ejecuciones_rul_iniciado_en", "ejecuciones_rul", ["iniciado_en"])
    op.create_table("resultados_rul",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("ejecucion_id", pg.UUID(as_uuid=True), sa.ForeignKey("ejecuciones_rul.id")),
        sa.Column("equipo_serie", sa.String(50), sa.ForeignKey("equipos.serie"), nullable=False),
        sa.Column("origen", sa.String(10), nullable=False),
        sa.Column("calculado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_evaluacion", sa.Date()),
        sa.Column("fecha_referencia", sa.Date()),
        sa.Column("tipo_referencia", sa.String(50)),
        sa.Column("vence_en", sa.DateTime(timezone=True)),
        sa.Column("version_calculo", sa.String(40), nullable=False),
        sa.Column("dias_vida_util_remanente", sa.Integer()),
        sa.Column("nivel_alerta", sa.String(20)),
        sa.Column("motivo_no_estimable", sa.String(80)),
        sa.UniqueConstraint("ejecucion_id", "equipo_serie", name="resultados_rul_ejecucion_equipo_key"),
        sa.CheckConstraint("origen IN ('LEGADO','BATCH')", name="resultados_rul_origen_check"),
        sa.CheckConstraint("origen = 'LEGADO' OR (ejecucion_id IS NOT NULL AND fecha_evaluacion IS NOT NULL AND fecha_referencia IS NOT NULL AND tipo_referencia IS NOT NULL AND vence_en IS NOT NULL AND vence_en > calculado_en)", name="resultados_rul_entrada_check"),
        sa.CheckConstraint("(dias_vida_util_remanente IS NOT NULL AND dias_vida_util_remanente >= 0 AND nivel_alerta IS NOT NULL AND nivel_alerta IN ('VERDE','AMARILLO','ROJO') AND motivo_no_estimable IS NULL) OR (dias_vida_util_remanente IS NULL AND nivel_alerta IS NULL AND motivo_no_estimable IS NOT NULL)", name="resultados_rul_valor_check"))
    op.create_index("ix_resultados_rul_equipo_serie", "resultados_rul", ["equipo_serie"])
    op.create_index("ix_resultados_rul_calculado_en", "resultados_rul", ["calculado_en"])
    op.add_column("predicciones_rul", sa.Column("tipo_referencia", sa.String(50)))
    op.add_column("predicciones_rul", sa.Column("ejecucion_id", pg.UUID(as_uuid=True)))
    op.add_column("predicciones_rul", sa.Column("vence_en", sa.DateTime(timezone=True)))
    op.create_foreign_key("predicciones_rul_ejecucion_id_fkey", "predicciones_rul", "ejecuciones_rul", ["ejecucion_id"], ["id"])
    # Copia literal; no inventar ejecución, tipo, día evaluado ni fecha de caducidad.
    op.execute("""INSERT INTO resultados_rul(id,equipo_serie,origen,calculado_en,fecha_referencia,
        version_calculo,dias_vida_util_remanente,nivel_alerta,motivo_no_estimable)
        SELECT gen_random_uuid(),equipo_serie,'LEGADO',actualizado_en,fecha_referencia,
        version_calculo,dias_vida_util_remanente,nivel_alerta,motivo_no_estimable FROM predicciones_rul""")


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS(SELECT 1 FROM ejecuciones_rul) OR EXISTS(SELECT 1 FROM resultados_rul WHERE origen <> 'LEGADO')")).scalar():
        raise RuntimeError("No se puede revertir: existe historial RUL nuevo. Conservar respaldo y resolver su recuperación antes del downgrade.")
    op.drop_constraint("predicciones_rul_ejecucion_id_fkey", "predicciones_rul", type_="foreignkey")
    for campo in ("vence_en", "ejecucion_id", "tipo_referencia"):
        op.drop_column("predicciones_rul", campo)
    op.drop_table("resultados_rul")
    op.drop_table("ejecuciones_rul")
