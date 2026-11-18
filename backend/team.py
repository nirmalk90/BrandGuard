"""Operator provisioning for fixed-role team workspaces."""
import argparse
from hashlib import sha256
import secrets

from sqlalchemy import select

from backend import db
from backend.demo import new_id
from backend.schemas import Profile


def token_hash(token):
    return sha256(token.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    workspace = commands.add_parser("create-workspace")
    workspace.add_argument("name")
    issue = commands.add_parser("issue-key")
    issue.add_argument("workspace_id")
    issue.add_argument("role", choices=["admin", "creator", "reviewer"])
    issue.add_argument("name")
    revoke = commands.add_parser("revoke-key")
    revoke.add_argument("member_id")
    args = parser.parse_args()
    with db.engine.begin() as conn:
        if args.command == "create-workspace":
            id_ = new_id()
            conn.execute(db.workspaces.insert().values(id=id_, profile=Profile(name=args.name).model_dump()))
            print(id_)
        elif args.command == "issue-key":
            if not conn.execute(select(db.workspaces.c.id).where(db.workspaces.c.id == args.workspace_id)).first():
                parser.error("Unknown workspace.")
            if not 1 <= len(args.name.strip()) <= 64:
                parser.error("Enter a name of 1 to 64 characters.")
            token = secrets.token_urlsafe(32)
            member_id = token_hash(token)
            conn.execute(db.members.insert().values(id=member_id, workspace_id=args.workspace_id,
                                                    role=args.role, name=args.name.strip()))
            print(f"Member ID: {member_id}\nPrivate sign-in key (shown once): {token}")
        else:
            if not conn.execute(select(db.members.c.id).where(db.members.c.id == args.member_id).with_for_update()).first():
                parser.error("Unknown member.")
            conn.execute(db.sessions.delete().where(db.sessions.c.member_id == args.member_id))
            conn.execute(db.members.delete().where(db.members.c.id == args.member_id))


if __name__ == "__main__":
    main()
