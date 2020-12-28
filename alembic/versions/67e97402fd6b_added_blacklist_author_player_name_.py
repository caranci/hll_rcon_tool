"""Added blacklist author Player name update Logline server

Revision ID: 67e97402fd6b
Revises: 5bad2e454e04
Create Date: 2020-12-27 05:22:47.551311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67e97402fd6b'
down_revision = '37db3151f4ce'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('log_lines', sa.Column('server', sa.String(), nullable=True))
    op.add_column('player_blacklist', sa.Column('by', sa.String(), nullable=True))
    op.add_column('player_names', sa.Column('last_seen', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('player_names', 'last_seen')
    op.drop_column('player_blacklist', 'by')
    op.drop_column('log_lines', 'server')
    # ### end Alembic commands ###