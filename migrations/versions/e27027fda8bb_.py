"""empty message

Revision ID: e27027fda8bb
Revises: d11354a43502
Create Date: 2024-08-05 14:50:51.643701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e27027fda8bb'
down_revision = 'd11354a43502'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(length=200), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], name='fk_project_image'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('image')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('image',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('file_path', sa.VARCHAR(length=200), nullable=False),
    sa.Column('project_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], name='fk_project_image'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('images')
    # ### end Alembic commands ###
