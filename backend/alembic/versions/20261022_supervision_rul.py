"""Actividad, plazo y cobertura de nuevas ejecuciones; legado desconocido.

Revision ID: 20261022_supervision_rul
Revises: 20261022_modelo_rul
"""
from alembic import op
import sqlalchemy as sa

revision="20261022_supervision_rul"
down_revision="20261022_modelo_rul"
branch_labels=None
depends_on=None


def upgrade():
    op.add_column("ejecuciones_rul",sa.Column("limite_en",sa.DateTime(timezone=True)))
    op.add_column("ejecuciones_rul",sa.Column("latido_en",sa.DateTime(timezone=True)))
    op.add_column("ejecuciones_rul",sa.Column("esperados",sa.Integer()))
    op.add_column("ejecuciones_rul",sa.Column("procesados",sa.Integer()))
    op.create_check_constraint("ejecuciones_rul_cobertura_check","ejecuciones_rul",
        "(esperados IS NULL OR esperados >= 0) AND (procesados IS NULL OR procesados >= 0) AND (esperados IS NULL OR procesados IS NULL OR procesados <= esperados)")
    op.create_check_constraint("ejecuciones_rul_supervision_check","ejecuciones_rul",
        "(limite_en IS NULL OR limite_en > iniciado_en) AND (latido_en IS NULL OR latido_en >= iniciado_en)")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM ejecuciones_rul WHERE limite_en IS NOT NULL OR latido_en IS NOT NULL OR esperados IS NOT NULL OR procesados IS NOT NULL)")).scalar():
        raise RuntimeError("No se puede revertir: existe supervisión RUL registrada. Conservar respaldo antes del downgrade.")
    op.drop_constraint("ejecuciones_rul_supervision_check","ejecuciones_rul",type_="check")
    op.drop_constraint("ejecuciones_rul_cobertura_check","ejecuciones_rul",type_="check")
    for columna in ("procesados","esperados","latido_en","limite_en"):
        op.drop_column("ejecuciones_rul",columna)
