import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    JSON, Boolean, Column, DateTime, ForeignKey, Integer, MetaData,
    String, Table, Text, UniqueConstraint, create_engine, event,
)

load_dotenv()
url = os.getenv("DATABASE_URL", "sqlite:///./brandguard.sqlite")
if url.startswith(("postgres://", "postgresql://")):
    url = "postgresql+psycopg://" + url.split("://", 1)[1]
engine = create_engine(url, pool_pre_ping=True)
metadata = MetaData()


if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")


def now():
    return datetime.now(timezone.utc)


def identifier():
    return Column("id", String(36), primary_key=True)


def reference(name, target, **options):
    return Column(name, ForeignKey(target), nullable=False, index=True, **options)


def timestamp(name="created_at"):
    return Column(name, DateTime(timezone=True), nullable=False, default=now)


workspaces = Table("workspaces", metadata, identifier(), timestamp(),
    Column("profile", JSON, nullable=False))
sessions = Table("sessions", metadata, Column("id", String(64), primary_key=True),
    reference("workspace_id", "workspaces.id"), Column("role", String(12), nullable=False),
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
    Column("generation", Integer, nullable=False))
versions = Table("versions", metadata, identifier(), timestamp(),
    reference("submission_id", "submissions.id"), Column("number", Integer, nullable=False),
    Column("content", Text, nullable=False), Column("content_hash", String(64), nullable=False),
    UniqueConstraint("submission_id", "number"))
reviews = Table("reviews", metadata, identifier(), timestamp(),
    reference("version_id", "versions.id"), Column("mode", String(24), nullable=False),
    Column("rules_checked", Integer, nullable=False), Column("notice", String(200)))
findings = Table("findings", metadata, identifier(), reference("review_id", "reviews.id"),
    Column("rule_id", ForeignKey("rules.id")), Column("evidence", JSON, nullable=False),
    Column("status", String(24), nullable=False), Column("reason", Text))
actions = Table("actions", metadata, identifier(), timestamp(),
    reference("submission_id", "submissions.id"), reference("version_id", "versions.id"),
    Column("actor", String(64), nullable=False), Column("action", String(24), nullable=False),
    Column("comment", Text, nullable=False))
