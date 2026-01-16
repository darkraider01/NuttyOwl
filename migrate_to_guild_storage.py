"""
Migration script to clear existing data for guild-specific storage.

This script backs up existing data files and clears them to prepare for
the new guild-specific storage system.
"""
import json
import os
import shutil
from datetime import datetime

# File paths
EVENTS_FILE = "events.json"
CLIPPERS_FILE = "clippers.json"
CONFIG_ROLES_FILE = "config_roles.json"

def backup_file(filepath):
    """Create a backup of a file with timestamp."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up {filepath} to {backup_path}")
        return True
    return False

def clear_file(filepath):
    """Clear a JSON file by writing an empty object."""
    with open(filepath, 'w') as f:
        json.dump({}, f, indent=2)
    print(f"✅ Cleared {filepath}")

def main():
    print("=" * 60)
    print("NuttyOwl Bot - Guild-Specific Storage Migration")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Backup your existing data files")
    print("2. Clear all events, clippers, and role configurations")
    print("3. Prepare the bot for guild-specific data storage")
    print()
    print("⚠️  WARNING: After this migration, you will need to recreate")
    print("   all events and clippers for each server separately.")
    print()
    
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    print()
    print("Starting migration...")
    print()
    
    # Backup and clear each file
    for filepath in [EVENTS_FILE, CLIPPERS_FILE, CONFIG_ROLES_FILE]:
        if backup_file(filepath):
            clear_file(filepath)
        else:
            print(f"ℹ️  {filepath} does not exist, creating empty file...")
            clear_file(filepath)
    
    print()
    print("=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start your bot")
    print("2. In each Discord server, run:")
    print("   - !addrole @YourRole (to set the role to ping)")
    print("   - !addevent HH:MM Description (to create events)")
    print("   - !clipper command_name description (to create clippers)")
    print()
    print("Each server will now have its own independent data!")
    print()

if __name__ == "__main__":
    main()
