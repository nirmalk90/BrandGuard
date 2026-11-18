import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    JSON, Boolean, Column, DateTime, ForeignKey, Integer, MetaData,
    String, Table, Text, UniqueConstraint, LargeBinary, create_engine, event,
)

load_dotenv()
url = os.getenv("DATABASE_URL", "sqlite:///./brandguard.sqlite")
if url.startswith(("postgres://", "postgresql://")):
    url = "postgresql+psycopg://" + url.split("://", 1)[1]
engine = create_engine(url, pool_pre_ping=True)
metadata = MetaData()


def configure_sqlite(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")


if engine.dialect.name == "sqlite":
    event.listen(engine, "connect", configure_sqlite)


def now():
    return datetime.now(timezone.utc)


def identifier():
    return Column("id", String(36), primary_key=True)


def reference(name, target, **options):
    return Column(name, ForeignKey(target), nullable=False, index=True, **options)


def timestamp(name="created_at"):
    return Column(name, DateTime(timezone=True), nullable=False, default=now)


workspaces = Table("workspaces", metadata, identifier(), timestamp(),
    Column("profile", JSON, nullable=False),
    Column("palette_version", Integer, nullable=False, server_default="1"),
    Column("logo_version", Integer, nullable=False, server_default="1"))
members = Table("members", metadata, Column("id", String(64), primary_key=True),
    reference("workspace_id", "workspaces.id"), Column("name", String(64), nullable=False),
    Column("role", String(12), nullable=False))
sessions = Table("sessions", metadata, Column("id", String(64), primary_key=True),
    reference("workspace_id", "workspaces.id"), Column("role", String(12), nullable=False),
    Column("member_id", ForeignKey("members.id"), index=True),
    timestamp())
sources = Table("sources", metadata, identifier(), reference("workspace_id", "workspaces.id"),
    timestamp(), Column("title", String(160), nullable=False),
    Column("content", Text, nullable=False), Column("version", Integer, nullable=False))
rules = Table("rules", metadata, identifier(), reference("workspace_id", "workspaces.id"),
    reference("source_id", "sources.id"), timestamp(), timestamp("updated_at"),
    Column("version", Integer, nullable=False), Column("spec", JSON, nullable=False),
    Column("active", Boolean, nullable=False))
submissions = Table("submissions", metadata, identifier(),
    reference("workspace_id", "workspaces.id"), timestamp(), timestamp("updated_at"),
    Column("title", String(160), nullable=False), Column("content_type", String(64), nullable=False),
    Column("platform", String(64), nullable=False), Column("creator", String(64), nullable=False),
    Column("status", String(24), nullable=False), Column("revision", Integer, nullable=False),
    Column("generation", Integer, nullable=False),
    Column("campaign", String(100), nullable=False, server_default="Unassigned", index=True))
assets = Table("assets", metadata, identifier(), reference("workspace_id", "workspaces.id"),
    timestamp(), Column("kind", String(12), nullable=False), Column("name", String(160), nullable=False),
    Column("digest", String(64), nullable=False), Column("image", LargeBinary, nullable=False),
    Column("mime", String(20), nullable=False), Column("width", Integer, nullable=False),
    Column("height", Integer, nullable=False), Column("lines", JSON, nullable=False),
    Column("active", Boolean, nullable=False), UniqueConstraint("workspace_id", "kind", "digest"))
versions = Table("versions", metadata, identifier(), timestamp(),
    reference("submission_id", "submissions.id"), Column("number", Integer, nullable=False),
    Column("content", Text, nullable=False), Column("content_hash", String(64), nullable=False),
    Column("artwork_id", ForeignKey("assets.id")),
    UniqueConstraint("submission_id", "number"))
reviews = Table("reviews", metadata, identifier(), timestamp(),
    reference("version_id", "versions.id"), Column("mode", String(24), nullable=False),
    Column("rules_checked", Integer, nullable=False), Column("notice", String(200)),
    Column("rules_snapshot", JSON))
findings = Table("findings", metadata, identifier(), reference("review_id", "reviews.id"),
    Column("rule_id", ForeignKey("rules.id")), Column("evidence", JSON, nullable=False),
    Column("status", String(24), nullable=False), Column("reason", Text))
actions = Table("actions", metadata, identifier(), timestamp(),
    reference("submission_id", "submissions.id"), reference("version_id", "versions.id"),
    Column("actor", String(64), nullable=False), Column("action", String(24), nullable=False),
    Column("comment", Text, nullable=False))

connections = Table("wordpress_connections", metadata, identifier(),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False, unique=True),
    Column("token_hash", String(64), unique=True))
posts = Table("wordpress_posts", metadata, identifier(),
    reference("connection_id", "wordpress_connections.id"), Column("post_id", Integer, nullable=False),
    Column("digest", String(64), nullable=False), Column("snapshot", JSON, nullable=False),
    Column("submission_id", ForeignKey("submissions.id"), unique=True, nullable=False),
    UniqueConstraint("connection_id", "post_id", "digest"))
