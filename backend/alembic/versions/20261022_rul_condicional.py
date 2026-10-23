"""Versionar cálculo RUL y representar abstenciones sin fabricar cifras.

Revision ID: 20261022_rul
Revises: 20261021_historia
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_rul"
down_revision = "20261021_historia"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("predicciones_rul", sa.Column("version_calculo", sa.String(40), nullable=False, server_default="LEGADO"))
    op.add_column("predicciones_rul", sa.Column("motivo_no_estimable", sa.String(80), nullable=True))
    op.alter_column("predicciones_rul", "dias_vida_util_remanente", existing_type=sa.Integer(), nullable=True)
    op.alter_column("predicciones_rul", "nivel_alerta", existing_type=sa.String(20), nullable=True)
    op.create_check_constraint("predicciones_rul_resultado_check", "predicciones_rul",
        "(dias_vida_util_remanente IS NOT NULL AND dias_vida_util_remanente >= 0 AND nivel_alerta IS NOT NULL AND motivo_no_estimable IS NULL) "
        "OR (dias_vida_util_remanente IS NULL AND nivel_alerta IS NULL AND motivo_no_estimable IS NOT NULL)")


def downgrade():
    abstenciones = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM predicciones_rul WHERE dias_vida_util_remanente IS NULL OR nivel_alerta IS NULL"
    )).scalar()
    if abstenciones:
        raise RuntimeError("No se puede revertir RUL: hay abstenciones que la versión anterior no puede representar. Conservar respaldo y resolverlas antes del downgrade.")
    op.drop_constraint("predicciones_rul_resultado_check", "predicciones_rul", type_="check")
    op.alter_column("predicciones_rul", "dias_vida_util_remanente", existing_type=sa.Integer(), nullable=False)
    op.alter_column("predicciones_rul", "nivel_alerta", existing_type=sa.String(20), nullable=False)
    op.drop_column("predicciones_rul", "motivo_no_estimable")
    op.drop_column("predicciones_rul", "version_calculo")
