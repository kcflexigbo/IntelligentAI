"""add_course_and_media_fields

Revision ID: 1bdb938859e3
Revises: 8ee288c7978e
Create Date: 2025-12-10 09:57:45.935240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bdb938859e3'
down_revision: Union[str, Sequence[str], None] = '8ee288c7978e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create courses table
    op.create_table('courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_name'), 'courses', ['name'], unique=True)
    
    # Add new columns to documents table
    op.add_column('documents', sa.Column('file_type', sa.String(), nullable=False, server_default='text'))
    op.add_column('documents', sa.Column('s3_key', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('transcription', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('is_course_material', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('documents', sa.Column('course_id', sa.Integer(), nullable=True))
    
    # Make user_id nullable (for course materials that don't belong to a user)
    op.alter_column('documents', 'user_id', nullable=True)
    
    # Add foreign key constraint for course_id
    op.create_foreign_key('fk_documents_course_id', 'documents', 'courses', ['course_id'], ['id'])
    
    # Create index on is_course_material for faster queries
    op.create_index(op.f('ix_documents_is_course_material'), 'documents', ['is_course_material'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index(op.f('ix_documents_is_course_material'), table_name='documents')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_documents_course_id', 'documents', type_='foreignkey')
    
    # Revert user_id to not nullable (set a default user_id for existing nulls if needed)
    op.alter_column('documents', 'user_id', nullable=False)
    
    # Remove columns from documents table
    op.drop_column('documents', 'course_id')
    op.drop_column('documents', 'is_course_material')
    op.drop_column('documents', 'transcription')
    op.drop_column('documents', 's3_key')
    op.drop_column('documents', 'file_type')
    
    # Drop courses table
    op.drop_index(op.f('ix_courses_name'), table_name='courses')
    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_table('courses')
