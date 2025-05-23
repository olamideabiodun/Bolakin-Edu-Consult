"""Add HotelAccommodationRequest model

Revision ID: 79b55c5d6bcd
Revises: d35e7e6fdd4b
Create Date: 2025-05-16 21:52:18.018778

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79b55c5d6bcd'
down_revision = 'd35e7e6fdd4b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('hotel_accommodation_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('destination_city_hotel', sa.String(length=150), nullable=False),
    sa.Column('check_in_date', sa.Date(), nullable=False),
    sa.Column('check_out_date', sa.Date(), nullable=False),
    sa.Column('num_adults', sa.Integer(), nullable=False),
    sa.Column('num_children', sa.Integer(), nullable=False),
    sa.Column('num_rooms', sa.Integer(), nullable=False),
    sa.Column('hotel_preferences', sa.Text(), nullable=True),
    sa.Column('room_type_preference', sa.String(length=100), nullable=True),
    sa.Column('budget_per_night', sa.String(length=100), nullable=True),
    sa.Column('special_requests', sa.Text(), nullable=True),
    sa.Column('submission_date', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('admin_notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('hotel_accommodation_requests')
    # ### end Alembic commands ###
