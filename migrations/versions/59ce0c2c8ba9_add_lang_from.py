"""Add lang from

Revision ID: 59ce0c2c8ba9
Revises: 3cc87976691f
Create Date: 2024-07-25 10:43:34.142141

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59ce0c2c8ba9'
down_revision = '3cc87976691f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('content', schema=None) as batch_op:
        batch_op.alter_column('text_translate',
               existing_type=sa.TEXT(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('content', schema=None) as batch_op:
        batch_op.alter_column('text_translate',
               existing_type=sa.TEXT(),
               nullable=False)

    # ### end Alembic commands ###
