#!/usr/bin/env python
"""Database migration helper script for Tenga Inventory POS.

Usage:
    python scripts/migrate.py upgrade [target]     # Upgrade to target revision (default: head)
    python scripts/migrate.py downgrade [target]   # Downgrade to target revision (default: -1)
    python scripts/migrate.py current              # Show current migration version
    python scripts/migrate.py history              # Show migration history
    python scripts/migrate.py revision -m "msg"    # Create new migration
    python scripts/migrate.py init                 # Initialize fresh schema
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from src.database.config import DB_URL, engine

def get_alembic_config():
    """Get Alembic configuration."""
    config = Config()
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", DB_URL))
    config.set_main_option(
        "script_location",
        str(project_root / "src" / "migrations")
    )
    return config

def cmd_upgrade(args):
    """Upgrade database schema."""
    config = get_alembic_config()
    target = args.target or "head"
    print(f"Upgrading to {target}...")
    command.upgrade(config, target)
    print(f"✓ Upgraded to {target}")

def cmd_downgrade(args):
    """Downgrade database schema."""
    config = get_alembic_config()
    target = args.target or "-1"
    print(f"Downgrading to {target}...")
    command.downgrade(config, target)
    print(f"✓ Downgraded to {target}")

def cmd_current(args):
    """Show current migration version."""
    config = get_alembic_config()
    print("Current migration version:")
    command.current(config)

def cmd_history(args):
    """Show migration history."""
    config = get_alembic_config()
    print("Migration history:")
    command.history(config)

def cmd_revision(args):
    """Create new migration."""
    if not args.message:
        print("Error: --message is required for creating migrations")
        sys.exit(1)
    
    config = get_alembic_config()
    print(f"Creating migration: {args.message}")
    command.revision(config, autogenerate=True, message=args.message)
    print("✓ Migration created in src/migrations/versions/")

def cmd_init(args):
    """Initialize fresh schema."""
    print("Initializing schema...")
    print("  - Dropping all tables")
    from src.database import drop_db
    drop_db()
    
    print("  - Upgrading to latest schema")
    config = get_alembic_config()
    command.upgrade(config, "head")
    
    print("✓ Schema initialized")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration helper for Tenga Inventory POS"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Migration command")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database schema")
    upgrade_parser.add_argument("target", nargs="?", default="head", 
                               help="Target revision (default: head)")
    upgrade_parser.set_defaults(func=cmd_upgrade)
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database schema")
    downgrade_parser.add_argument("target", nargs="?", default="-1",
                                help="Target revision (default: -1)")
    downgrade_parser.set_defaults(func=cmd_downgrade)
    
    # Current command
    current_parser = subparsers.add_parser("current", help="Show current version")
    current_parser.set_defaults(func=cmd_current)
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.set_defaults(func=cmd_history)
    
    # Revision command
    revision_parser = subparsers.add_parser("revision", help="Create new migration")
    revision_parser.add_argument("-m", "--message", required=False,
                                help="Migration description")
    revision_parser.set_defaults(func=cmd_revision)
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize fresh schema")
    init_parser.set_defaults(func=cmd_init)
    
    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
