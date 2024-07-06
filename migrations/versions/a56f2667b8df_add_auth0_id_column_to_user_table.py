"""Make auth0_id column non-nullable

Revision ID: new_revision_id
Revises: a56f2667b8df
Create Date: 2024-07-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'new_revision_id'
down_revision = 'a56f2667b8df'
branch_labels = None
depends_on = None


def upgrade():
    # Update existing rows to set a default value
    op.execute("UPDATE user SET auth0_id = '' WHERE auth0_id IS NULL")
    
    # Make the auth0_id column non-nullable and create unique constraint
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('auth0_id', nullable=False)
        batch_op.create_unique_constraint('uq_user_auth0_id', ['auth0_id'])


def downgrade():
    # Drop the unique constraint and make the column nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_auth0_id', type_='unique')
        batch_op.alter_column('auth0_id', nullable=True)

    # Reset the auth0_id column to null for consistency
    op.execute("UPDATE user SET auth0_id = NULL WHERE auth0_id = ''")
