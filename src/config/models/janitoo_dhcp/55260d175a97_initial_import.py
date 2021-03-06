"""Initial import

Revision ID: 55260d175a97
Revises: c82e77da67b
Create Date: 2015-11-17 00:13:21.257568

"""

# revision identifiers, used by Alembic.
revision = '55260d175a97'
down_revision = 'c82e77da67b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('dhcp_leases',
    sa.Column('add_ctrl', sa.Integer(), nullable=False),
    sa.Column('add_node', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('location', sa.String(length=250), nullable=False),
    sa.Column('cmd_classes', sa.String(length=250), nullable=False),
    sa.Column('state', sa.String(length=10), nullable=False),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('add_ctrl', 'add_node', name='dhcp_leases_primary'),
    )
    op.create_table('dhcp_leases_param',
    sa.Column('add_ctrl', sa.Integer(), nullable=False),
    sa.Column('add_node', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=250), nullable=False),
    sa.ForeignKeyConstraint(['add_ctrl', 'add_node'], ['dhcp_leases.add_ctrl', 'dhcp_leases.add_node'], name='dhcp_leases_param_foreign_lease'),
    sa.PrimaryKeyConstraint('add_ctrl', 'add_node', 'key', name='dhcp_leases_param_primary')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('dhcp_leases_param')
    op.drop_table('dhcp_leases')
    ### end Alembic commands ###
