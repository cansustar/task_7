"""123

Revision ID: 86dc9a70301a
Revises: a816c8748a04
Create Date: 2022-03-31 22:30:34.122871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86dc9a70301a'
down_revision = 'a816c8748a04'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('article', sa.Column('updatedAt', sa.DateTime(), nullable=True))
    op.drop_column('article', 'updateAt')
    op.add_column('comment', sa.Column('updatedAt', sa.DateTime(), nullable=True))
    op.drop_column('comment', 'updateAt')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('comment', sa.Column('updateAt', sa.DATETIME(), nullable=True))
    op.drop_column('comment', 'updatedAt')
    op.add_column('article', sa.Column('updateAt', sa.DATETIME(), nullable=True))
    op.drop_column('article', 'updatedAt')
    # ### end Alembic commands ###
