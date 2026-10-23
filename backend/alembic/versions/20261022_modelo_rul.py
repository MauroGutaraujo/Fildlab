"""Identidad del artefacto y entorno de entrenamiento, sin inferir legado.

Revision ID: 20261022_modelo_rul
Revises: 20261022_historial_rul
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision="20261022_modelo_rul"
down_revision="20261022_historial_rul"
branch_labels=None
depends_on=None


def upgrade():
    op.add_column("ejecuciones_rul",sa.Column("modelo_sha256",sa.String(64)))
    op.add_column("ejecuciones_rul",sa.Column("entorno_modelo",JSONB()))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM ejecuciones_rul WHERE modelo_sha256 IS NOT NULL OR entorno_modelo IS NOT NULL)")).scalar():
        raise RuntimeError("No se puede revertir: existe identidad de modelos RUL. Conservar respaldo y resolver antes del downgrade.")
    op.drop_column("ejecuciones_rul","entorno_modelo")
    op.drop_column("ejecuciones_rul","modelo_sha256")
