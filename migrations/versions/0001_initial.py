"""Initial governance schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workspaces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('profile', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sessions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=12), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_workspace_id'), 'sessions', ['workspace_id'], unique=False)
    op.create_table('sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sources_workspace_id'), 'sources', ['workspace_id'], unique=False)
    op.create_table('submissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=False),
        sa.Column('platform', sa.String(length=64), nullable=False),
        sa.Column('creator', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submissions_workspace_id'), 'submissions', ['workspace_id'], unique=False)
    op.create_table('rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('spec', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rules_source_id'), 'rules', ['source_id'], unique=False)
    op.create_index(op.f('ix_rules_workspace_id'), 'rules', ['workspace_id'], unique=False)
    op.create_table('versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submission_id', sa.String(length=36), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', 'number')
    )
    op.create_index(op.f('ix_versions_submission_id'), 'versions', ['submission_id'], unique=False)
    op.create_table('actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submission_id', sa.String(length=36), nullable=False),
        sa.Column('version_id', sa.String(length=36), nullable=False),
        sa.Column('actor', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=24), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ),
        sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_actions_submission_id'), 'actions', ['submission_id'], unique=False)
    op.create_index(op.f('ix_actions_version_id'), 'actions', ['version_id'], unique=False)
    op.create_table('reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version_id', sa.String(length=36), nullable=False),
        sa.Column('mode', sa.String(length=24), nullable=False),
        sa.Column('rules_checked', sa.Integer(), nullable=False),
        sa.Column('notice', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_version_id'), 'reviews', ['version_id'], unique=False)
    op.create_table('findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('rule_id', sa.String(length=36), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_findings_review_id'), 'findings', ['review_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_findings_review_id'), table_name='findings')
    op.drop_table('findings')
    op.drop_index(op.f('ix_reviews_version_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_actions_version_id'), table_name='actions')
    op.drop_index(op.f('ix_actions_submission_id'), table_name='actions')
    op.drop_table('actions')
    op.drop_index(op.f('ix_versions_submission_id'), table_name='versions')
    op.drop_table('versions')
    op.drop_index(op.f('ix_rules_workspace_id'), table_name='rules')
    op.drop_index(op.f('ix_rules_source_id'), table_name='rules')
    op.drop_table('rules')
    op.drop_index(op.f('ix_submissions_workspace_id'), table_name='submissions')
    op.drop_table('submissions')
    op.drop_index(op.f('ix_sources_workspace_id'), table_name='sources')
    op.drop_table('sources')
    op.drop_index(op.f('ix_sessions_workspace_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_table('workspaces')
