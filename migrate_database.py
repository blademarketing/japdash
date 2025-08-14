#!/usr/bin/env python3
"""
JAP Dashboard Database Migration Script

This script safely migrates your production database to support the new screenshot functionality
while creating automatic backups and providing rollback capabilities.

Features:
- Automatic backup before migration
- Version detection and validation
- Safe rollback functionality
- Data integrity verification
- Interactive user interface
"""

import sqlite3
import os
import shutil
from datetime import datetime
import sys
import json

class DatabaseMigrator:
    def __init__(self, db_path="social_media_accounts.db"):
        self.db_path = db_path
        self.backup_dir = "database_backups"
        
    def ensure_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            print(f"📁 Created backup directory: {self.backup_dir}")
    
    def get_database_version(self, db_path):
        """Get current database version"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # Check if schema_migrations table exists
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchall()
            if not tables:
                conn.close()
                return "v0_no_migrations"
            
            # Get latest migration
            migrations = conn.execute("SELECT version FROM schema_migrations ORDER BY version DESC").fetchall()
            conn.close()
            
            if not migrations:
                return "v1_initial"
            
            return migrations[0][0]
            
        except Exception as e:
            print(f"❌ Error checking database version: {e}")
            return "unknown"
    
    def get_available_backups(self):
        """Get list of available backup files"""
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("social_media_accounts_") and file.endswith(".db"):
                backup_path = os.path.join(self.backup_dir, file)
                stat = os.stat(backup_path)
                created = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get version from backup
                version = self.get_database_version(backup_path)
                
                backups.append({
                    'filename': file,
                    'path': backup_path,
                    'created': created,
                    'version': version,
                    'size': f"{stat.st_size / 1024:.1f} KB"
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups
    
    def create_backup(self):
        """Create a backup of the current database"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database file not found: {self.db_path}")
            return None
        
        self.ensure_backup_directory()
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"social_media_accounts_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            print(f"💾 Creating backup: {backup_filename}")
            shutil.copy2(self.db_path, backup_path)
            
            # Verify backup
            original_size = os.path.getsize(self.db_path)
            backup_size = os.path.getsize(backup_path)
            
            if original_size != backup_size:
                print(f"⚠️ Warning: Backup size mismatch (original: {original_size}, backup: {backup_size})")
                return None
            
            print(f"✅ Backup created successfully: {backup_path}")
            print(f"📊 Backup size: {backup_size / 1024:.1f} KB")
            
            return backup_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def restore_backup(self, backup_path):
        """Restore database from backup"""
        if not os.path.exists(backup_path):
            print(f"❌ Backup file not found: {backup_path}")
            return False
        
        try:
            # Create current backup before restore
            current_backup = self.create_backup()
            if current_backup:
                print(f"💾 Current database backed up to: {current_backup}")
            
            print(f"🔄 Restoring database from: {backup_path}")
            shutil.copy2(backup_path, self.db_path)
            
            # Verify restore
            restored_size = os.path.getsize(self.db_path)
            backup_size = os.path.getsize(backup_path)
            
            if restored_size != backup_size:
                print(f"❌ Restore size mismatch")
                return False
            
            print(f"✅ Database restored successfully")
            print(f"📊 Restored size: {restored_size / 1024:.1f} KB")
            
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def verify_database_integrity(self, db_path=None):
        """Verify database integrity and structure"""
        if db_path is None:
            db_path = self.db_path
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # Run SQLite integrity check
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if integrity[0] != "ok":
                print(f"❌ Database integrity check failed: {integrity[0]}")
                conn.close()
                return False
            
            # Check essential tables exist
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            required_tables = ['accounts', 'actions', 'execution_history', 'settings']
            
            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                print(f"⚠️ Warning: Missing tables: {', '.join(missing_tables)}")
            
            # Count records in main tables
            counts = {}
            for table in ['accounts', 'execution_history', 'settings']:
                if table in tables:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    counts[table] = count
            
            conn.close()
            
            print(f"✅ Database integrity verified")
            print(f"📊 Record counts: {counts}")
            
            return True
            
        except Exception as e:
            print(f"❌ Database verification failed: {e}")
            return False
    
    def apply_v3_screenshots_migration(self):
        """Apply the v3 screenshots migration"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # Create schema_migrations table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create settings table if it doesn't exist (for older databases)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Check if already applied
            existing = conn.execute("SELECT version FROM schema_migrations WHERE version = 'v3_add_screenshots'").fetchone()
            if existing:
                print("ℹ️ Migration v3_add_screenshots already applied")
                conn.close()
                return True
            
            print("🔄 Applying v3_add_screenshots migration...")
            
            # Check what tables currently exist for diagnostics
            existing_tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"📋 Current tables: {', '.join(existing_tables)}")
            
            if 'settings' not in existing_tables:
                print("ℹ️ Creating settings table (missing from original database)")
            
            # Create screenshots table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER NOT NULL,
                    screenshot_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    gologin_profile_id TEXT NOT NULL,
                    screenshot_data TEXT,
                    dimensions_width INTEGER,
                    dimensions_height INTEGER,
                    capture_duration_ms INTEGER,
                    capture_timestamp TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES execution_history (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_execution_id ON screenshots(execution_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_type ON screenshots(screenshot_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_status ON screenshots(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_platform ON screenshots(platform)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp ON screenshots(capture_timestamp)')
            
            # Add GoLogin and screenshot settings (using INSERT OR IGNORE to preserve existing values)
            settings = [
                ('gologin_api_key', ''),
                ('gologin_api_token', ''),
                ('gologin_facebook_profile_id', ''),
                ('gologin_instagram_profile_id', ''),
                ('gologin_twitter_profile_id', ''),
                ('gologin_tiktok_profile_id', ''),
                ('screenshot_enabled', 'true'),
                ('screenshot_store_as_files', 'false'),
                ('screenshot_max_retries', '3'),
                ('screenshot_api_url', 'https://gologin.electric-marinade.com:8443'),
                ('screenshot_api_key', '')
            ]
            
            for key, default_value in settings:
                conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, default_value))
            
            # Mark migration as applied
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', ('v3_add_screenshots',))
            
            conn.commit()
            conn.close()
            
            print("✅ Migration v3_add_screenshots applied successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def apply_v4_packages_migration(self):
        """Apply v4 migration: Add packages system with network-specific order collections"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Database not found: {self.db_path}")
                return False
            
            conn = sqlite3.connect(self.db_path)
            conn.execute("BEGIN")
            
            # Create schema_migrations table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check if already applied
            existing = conn.execute("SELECT version FROM schema_migrations WHERE version = 'v4_add_packages'").fetchone()
            if existing:
                print("ℹ️ Migration v4_add_packages already applied")
                conn.close()
                return True
            
            print("🔄 Applying v4_add_packages migration...")
            
            # Check what tables currently exist for diagnostics
            existing_tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"📋 Current tables: {', '.join(existing_tables)}")
            
            # Create packages table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create package_orders table for network-specific order collections
            conn.execute('''
                CREATE TABLE IF NOT EXISTS package_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    network TEXT NOT NULL,                -- 'instagram', 'facebook', 'x', 'tiktok'
                    service_id INTEGER NOT NULL,          -- JAP service ID
                    service_name TEXT NOT NULL,           -- Service display name
                    quantity INTEGER NOT NULL,            -- Order quantity
                    order_priority INTEGER DEFAULT 1,     -- Execution order within network
                    
                    -- Quick Execute parameters - preserved exactly as current system
                    use_llm_generation BOOLEAN DEFAULT 0,
                    comment_directives TEXT,
                    comment_count INTEGER,
                    use_hashtags BOOLEAN DEFAULT 0,
                    use_emojis BOOLEAN DEFAULT 0,
                    custom_comments TEXT,
                    
                    -- Additional service parameters (JSON for flexibility)
                    service_parameters TEXT,              -- JSON of additional parameters
                    
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (package_id) REFERENCES packages (id) ON DELETE CASCADE,
                    UNIQUE(package_id, network, order_priority)  -- Ensure unique priorities per network
                )
            ''')
            
            # Create package_executions table to track package submissions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS package_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    target_url TEXT NOT NULL,             -- Submitted URL
                    detected_network TEXT NOT NULL,       -- Auto-detected network
                    status TEXT DEFAULT 'pending',        -- 'pending', 'processing', 'completed', 'failed'
                    total_orders INTEGER DEFAULT 0,       -- Number of orders created
                    completed_orders INTEGER DEFAULT 0,   -- Number of completed orders
                    failed_orders INTEGER DEFAULT 0,      -- Number of failed orders
                    error_message TEXT,                   -- Error details if failed
                    execution_start TIMESTAMP,
                    execution_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (package_id) REFERENCES packages (id) ON DELETE CASCADE
                )
            ''')
            
            # Create package_execution_orders to link individual orders to package executions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS package_execution_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_execution_id INTEGER NOT NULL,
                    execution_history_id INTEGER NOT NULL,  -- Links to existing execution_history table
                    package_order_id INTEGER NOT NULL,      -- The template order from package_orders
                    jap_order_id TEXT NOT NULL,             -- JAP API order ID
                    status TEXT DEFAULT 'pending',          -- JAP order status
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (package_execution_id) REFERENCES package_executions (id) ON DELETE CASCADE,
                    FOREIGN KEY (execution_history_id) REFERENCES execution_history (id) ON DELETE CASCADE,
                    FOREIGN KEY (package_order_id) REFERENCES package_orders (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_orders_package_network ON package_orders(package_id, network)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_orders_priority ON package_orders(package_id, network, order_priority)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_executions_package ON package_executions(package_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_executions_network ON package_executions(detected_network)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_executions_status ON package_executions(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_execution_orders_package ON package_execution_orders(package_execution_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_execution_orders_execution ON package_execution_orders(execution_history_id)')
            
            # Mark migration as applied
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', ('v4_add_packages',))
            
            conn.commit()
            conn.close()
            
            print("✅ Migration v4_add_packages applied successfully!")
            print("📦 Added packages system with network-specific order collections")
            print("🔗 Integrated with existing execution_history for tracking")
            print("🎯 Supports auto-detection and routing by social network")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def apply_v5_simplify_packages_migration(self):
        """Apply v5 migration: Remove priority and enabled fields from package_orders"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Database not found: {self.db_path}")
                return False
            
            conn = sqlite3.connect(self.db_path)
            conn.execute("BEGIN")
            
            # Create schema_migrations table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check if already applied
            existing = conn.execute("SELECT version FROM schema_migrations WHERE version = 'v5_simplify_packages'").fetchone()
            if existing:
                print("ℹ️ Migration v5_simplify_packages already applied")
                conn.close()
                return True
            
            print("🔄 Applying v5_simplify_packages migration...")
            
            # Check what tables currently exist for diagnostics
            existing_tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"📋 Current tables: {', '.join(existing_tables)}")
            
            # Create new package_orders table without priority and enabled fields
            conn.execute('''
                CREATE TABLE package_orders_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    network TEXT NOT NULL,                -- 'instagram', 'facebook', 'x', 'tiktok'
                    service_id INTEGER NOT NULL,          -- JAP service ID
                    service_name TEXT NOT NULL,           -- Service display name
                    quantity INTEGER NOT NULL,            -- Order quantity
                    
                    -- Quick Execute parameters - preserved exactly as current system
                    use_llm_generation BOOLEAN DEFAULT 0,
                    comment_directives TEXT,
                    comment_count INTEGER,
                    use_hashtags BOOLEAN DEFAULT 0,
                    use_emojis BOOLEAN DEFAULT 0,
                    custom_comments TEXT,
                    
                    -- Additional service parameters (JSON for flexibility)
                    service_parameters TEXT,              -- JSON of additional parameters
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (package_id) REFERENCES packages (id) ON DELETE CASCADE
                )
            ''')
            
            # Copy data from old table to new table (excluding priority and enabled fields)
            conn.execute('''
                INSERT INTO package_orders_new (
                    id, package_id, network, service_id, service_name, quantity,
                    use_llm_generation, comment_directives, comment_count,
                    use_hashtags, use_emojis, custom_comments, service_parameters,
                    created_at, updated_at
                )
                SELECT 
                    id, package_id, network, service_id, service_name, quantity,
                    use_llm_generation, comment_directives, comment_count,
                    use_hashtags, use_emojis, custom_comments, service_parameters,
                    created_at, updated_at
                FROM package_orders
            ''')
            
            # Drop old table and rename new one
            conn.execute('DROP TABLE package_orders')
            conn.execute('ALTER TABLE package_orders_new RENAME TO package_orders')
            
            # Recreate indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_package_orders_package_network ON package_orders(package_id, network)')
            
            # Mark migration as applied
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', ('v5_simplify_packages',))
            
            conn.commit()
            conn.close()
            
            print("✅ Migration v5_simplify_packages applied successfully!")
            print("🗑️ Removed priority and enabled fields from package_orders")
            print("🔄 Simplified package order structure")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def show_database_status(self):
        """Show current database status"""
        print("\n" + "="*60)
        print("📊 Current Database Status")
        print("="*60)
        
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            return
        
        version = self.get_database_version(self.db_path)
        size = os.path.getsize(self.db_path)
        modified = datetime.fromtimestamp(os.path.getmtime(self.db_path)).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"📍 Database: {self.db_path}")
        print(f"📏 Size: {size / 1024:.1f} KB")
        print(f"🕒 Modified: {modified}")
        print(f"🏷️ Version: {version}")
        
        # Show table counts
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            print(f"📋 Tables: {len(tables)}")
            
            for table in ['accounts', 'execution_history', 'screenshots', 'packages', 'package_orders', 'package_executions', 'settings']:
                if table in tables:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    print(f"   {table}: {count} records")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Could not read table info: {e}")
    
    def interactive_menu(self):
        """Interactive menu for migration operations"""
        while True:
            self.show_database_status()
            
            print("\n" + "="*60)
            print("🛠️ JAP Dashboard Database Migration Tool")
            print("="*60)
            
            print("\nAvailable Actions:")
            print("1. 📦 Create Backup")
            print("2. 🚀 Migrate to v3 (Screenshots)")
            print("3. 📦 Migrate to v4 (Packages)")
            print("4. 🔄 Migrate to v5 (Simplify Packages)")
            print("5. 📋 List Available Backups")
            print("6. 🔄 Restore from Backup")
            print("7. ✅ Verify Database Integrity")
            print("8. ❌ Exit")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == "1":
                backup_path = self.create_backup()
                if backup_path:
                    print(f"\n✅ Backup created: {backup_path}")
                input("\nPress Enter to continue...")
                
            elif choice == "2":
                print("\n🚀 Starting Migration to v3 (Screenshots)")
                print("-" * 40)
                
                current_version = self.get_database_version(self.db_path)
                print(f"Current version: {current_version}")
                
                if current_version == "v3_add_screenshots":
                    print("ℹ️ Database is already at v3. No migration needed.")
                else:
                    confirm = input("\n⚠️ This will modify your database. Continue? (y/N): ").strip().lower()
                    if confirm == 'y':
                        backup_path = self.create_backup()
                        if backup_path:
                            if self.apply_v3_screenshots_migration():
                                print("\n🎉 Migration completed successfully!")
                                self.verify_database_integrity()
                            else:
                                print("\n❌ Migration failed. Database not modified.")
                        else:
                            print("\n❌ Could not create backup. Migration aborted.")
                    else:
                        print("Migration cancelled.")
                
                input("\nPress Enter to continue...")
                
            elif choice == "3":
                print("\n📦 Starting Migration to v4 (Packages)")
                print("-" * 40)
                
                current_version = self.get_database_version(self.db_path)
                print(f"Current version: {current_version}")
                
                if current_version == "v4_add_packages":
                    print("ℹ️ Database is already at v4. No migration needed.")
                else:
                    confirm = input("\n⚠️ This will modify your database. Continue? (y/N): ").strip().lower()
                    if confirm == 'y':
                        backup_path = self.create_backup()
                        if backup_path:
                            if self.apply_v4_packages_migration():
                                print("\n🎉 Migration completed successfully!")
                                self.verify_database_integrity()
                            else:
                                print("\n❌ Migration failed. Database not modified.")
                        else:
                            print("\n❌ Could not create backup. Migration aborted.")
                    else:
                        print("Migration cancelled.")
                
                input("\nPress Enter to continue...")
                
            elif choice == "4":
                print("\n🔄 Starting Migration to v5 (Simplify Packages)")
                print("-" * 40)
                
                current_version = self.get_database_version(self.db_path)
                print(f"Current version: {current_version}")
                
                if current_version == "v5_simplify_packages":
                    print("ℹ️ Database is already at v5. No migration needed.")
                else:
                    confirm = input("\n⚠️ This will modify your database. Continue? (y/N): ").strip().lower()
                    if confirm == 'y':
                        backup_path = self.create_backup()
                        if backup_path:
                            if self.apply_v5_simplify_packages_migration():
                                print("\n🎉 Migration completed successfully!")
                                self.verify_database_integrity()
                            else:
                                print("\n❌ Migration failed. Database not modified.")
                        else:
                            print("\n❌ Could not create backup. Migration aborted.")
                    else:
                        print("Migration cancelled.")
                
                input("\nPress Enter to continue...")
                
            elif choice == "5":
                backups = self.get_available_backups()
                print(f"\n📋 Available Backups ({len(backups)})")
                print("-" * 80)
                
                if not backups:
                    print("No backups found.")
                else:
                    print(f"{'#':<3} {'Filename':<30} {'Created':<20} {'Version':<15} {'Size'}")
                    print("-" * 80)
                    for i, backup in enumerate(backups, 1):
                        print(f"{i:<3} {backup['filename']:<30} {backup['created']:<20} {backup['version']:<15} {backup['size']}")
                
                input("\nPress Enter to continue...")
                
            elif choice == "6":
                backups = self.get_available_backups()
                if not backups:
                    print("\n❌ No backups available for restore.")
                    input("Press Enter to continue...")
                    continue
                
                print(f"\n🔄 Restore from Backup")
                print("-" * 40)
                print(f"{'#':<3} {'Filename':<30} {'Created':<20} {'Version':<15}")
                print("-" * 80)
                
                for i, backup in enumerate(backups, 1):
                    print(f"{i:<3} {backup['filename']:<30} {backup['created']:<20} {backup['version']:<15}")
                
                try:
                    choice_num = input(f"\nSelect backup to restore (1-{len(backups)}) or 'c' to cancel: ").strip()
                    if choice_num.lower() == 'c':
                        continue
                    
                    backup_idx = int(choice_num) - 1
                    if 0 <= backup_idx < len(backups):
                        selected_backup = backups[backup_idx]
                        print(f"\nSelected: {selected_backup['filename']}")
                        print(f"Version: {selected_backup['version']}")
                        print(f"Created: {selected_backup['created']}")
                        
                        confirm = input(f"\n⚠️ This will replace your current database. Continue? (y/N): ").strip().lower()
                        if confirm == 'y':
                            if self.restore_backup(selected_backup['path']):
                                print("\n🎉 Database restored successfully!")
                                self.verify_database_integrity()
                            else:
                                print("\n❌ Restore failed.")
                        else:
                            print("Restore cancelled.")
                    else:
                        print("❌ Invalid selection.")
                        
                except ValueError:
                    print("❌ Invalid input.")
                
                input("\nPress Enter to continue...")
                
            elif choice == "7":
                print("\n✅ Verifying Database Integrity")
                print("-" * 40)
                self.verify_database_integrity()
                input("\nPress Enter to continue...")
                
            elif choice == "8":
                print("\n👋 Goodbye!")
                break
                
            else:
                print("\n❌ Invalid choice. Please try again.")
                input("Press Enter to continue...")

def main():
    """Main entry point"""
    print("🚀 JAP Dashboard Database Migration Tool")
    print("=" * 60)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--backup":
            migrator = DatabaseMigrator()
            migrator.create_backup()
            return
        elif sys.argv[1] == "--migrate":
            migrator = DatabaseMigrator()
            backup_path = migrator.create_backup()
            if backup_path and migrator.apply_v3_screenshots_migration():
                print("Migration completed successfully!")
            return
        elif sys.argv[1] == "--help":
            print("\nUsage:")
            print("  python migrate_database.py              # Interactive mode")
            print("  python migrate_database.py --backup     # Create backup only")
            print("  python migrate_database.py --migrate    # Auto backup and migrate")
            print("  python migrate_database.py --help       # Show this help")
            return
    
    # Interactive mode
    migrator = DatabaseMigrator()
    migrator.interactive_menu()

if __name__ == "__main__":
    main()
