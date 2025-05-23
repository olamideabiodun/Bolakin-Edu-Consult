"""Add ProofOfFundsRequest model

Revision ID: ab3257d1a9a8
Revises: 4472c45c8f55
Create Date: 2025-05-16 21:43:57.500128

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab3257d1a9a8'
down_revision = '4472c45c8f55'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('proof_of_funds_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('service_type', sa.String(length=100), nullable=False),
    sa.Column('purpose', sa.String(length=150), nullable=False),
    sa.Column('destination_country', sa.String(length=100), nullable=True),
    sa.Column('amount_required', sa.String(length=100), nullable=True),
    sa.Column('timeline', sa.String(length=100), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('submission_date', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('admin_notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('proof_of_funds_requests')
    # ### end Alembic commands ###
