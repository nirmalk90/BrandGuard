"""Artwork, workspace identities, campaign evidence and WordPress snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def key():
    return sa.Column("id", sa.String(36), primary_key=True)


def workspace():
    return sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False)


def upgrade():
    op.create_table("members", sa.Column("id", sa.String(64), primary_key=True), workspace(),
                    sa.Column("name", sa.String(64), nullable=False),
                    sa.Column("role", sa.String(12), nullable=False))
    op.create_index("ix_members_workspace_id", "members", ["workspace_id"])
    op.create_table("assets", key(), workspace(),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("kind", sa.String(12), nullable=False),
                    sa.Column("name", sa.String(160), nullable=False),
                    sa.Column("digest", sa.String(64), nullable=False),
                    sa.Column("image", sa.LargeBinary, nullable=False),
                    sa.Column("mime", sa.String(20), nullable=False),
                    sa.Column("width", sa.Integer, nullable=False),
                    sa.Column("height", sa.Integer, nullable=False),
                    sa.Column("lines", sa.JSON, nullable=False),
                    sa.Column("active", sa.Boolean, nullable=False),
                    sa.UniqueConstraint("workspace_id", "kind", "digest"))
    op.create_index("ix_assets_workspace_id", "assets", ["workspace_id"])
    # SQLite supports adding nullable references inline without rebuilding tables with dependents.
    op.execute("ALTER TABLE sessions ADD COLUMN member_id VARCHAR(64) REFERENCES members(id)")
    op.create_index("ix_sessions_member_id", "sessions", ["member_id"])
    op.execute("ALTER TABLE versions ADD COLUMN artwork_id VARCHAR(36) REFERENCES assets(id)")
    op.add_column("reviews", sa.Column("rules_snapshot", sa.JSON))
    op.add_column("submissions", sa.Column("campaign", sa.String(100), nullable=False, server_default="Unassigned"))
    op.create_index("ix_submissions_campaign", "submissions", ["campaign"])
    for field in ("logo_version", "palette_version"):
        op.add_column("workspaces", sa.Column(field, sa.Integer, nullable=False, server_default="1"))
    op.create_table("wordpress_connections", key(), workspace(),
                    sa.Column("token_hash", sa.String(64), unique=True), sa.UniqueConstraint("workspace_id"))
    op.create_table("wordpress_posts", key(),
                    sa.Column("connection_id", sa.String(36), sa.ForeignKey("wordpress_connections.id"), nullable=False),
                    sa.Column("post_id", sa.Integer, nullable=False),
                    sa.Column("digest", sa.String(64), nullable=False),
                    sa.Column("snapshot", sa.JSON, nullable=False),
                    sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id"), nullable=False, unique=True),
                    sa.UniqueConstraint("connection_id", "post_id", "digest"))
    op.create_index("ix_wordpress_posts_connection_id", "wordpress_posts", ["connection_id"])


def downgrade():
    op.drop_table("wordpress_posts")
    op.drop_table("wordpress_connections")
    op.drop_column("workspaces", "palette_version")
    op.drop_column("workspaces", "logo_version")
    op.drop_index("ix_submissions_campaign", table_name="submissions")
    op.drop_column("submissions", "campaign")
    op.drop_column("reviews", "rules_snapshot")
    op.drop_column("versions", "artwork_id")
    op.drop_index("ix_sessions_member_id", table_name="sessions")
    op.drop_column("sessions", "member_id")
    op.drop_table("assets")
    op.drop_table("members")
