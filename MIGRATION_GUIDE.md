# Database Migration Guide

## Overview

This guide covers migrating your JAP Dashboard database to support the new screenshot functionality (v3_add_screenshots). The migration script provides safe backup and restore capabilities.

## ⚠️ Important - Before You Start

**ALWAYS backup your database before running any migration!** The migration script will automatically create backups, but it's good practice to have manual backups too.

## Quick Migration (Recommended)

For most users, simply run:

```bash
# Automatic backup + migration
python migrate_database.py --migrate
```

This will:
1. ✅ Create automatic backup with timestamp
2. ✅ Apply v3_add_screenshots migration  
3. ✅ Add screenshot functionality
4. ✅ Preserve all existing data

## Interactive Mode (Full Control)

For full control over the process:

```bash
# Interactive menu
python migrate_database.py
```

Available options:
- **📦 Create Backup** - Manual backup creation
- **🚀 Migrate to v3** - Apply screenshot migration
- **📋 List Backups** - View all available backups
- **🔄 Restore from Backup** - Rollback to previous version
- **✅ Verify Database** - Check database integrity

## Command Line Options

```bash
python migrate_database.py --backup    # Create backup only
python migrate_database.py --migrate   # Auto backup and migrate  
python migrate_database.py --help      # Show help
python migrate_database.py             # Interactive mode
```

## What the Migration Adds

### New Database Table: `screenshots`
- Before/after screenshot storage
- Links to execution_history records
- GoLogin profile tracking
- Retry logic and error handling

### New Admin Settings:
- `gologin_api_key` - GoLogin API token
- `gologin_api_token` - Alternative key name  
- `gologin_*_profile_id` - Browser profiles for each platform
- `screenshot_api_key` - Screenshot service API key
- `screenshot_api_url` - Screenshot service endpoint
- `screenshot_enabled` - Enable/disable screenshots
- `screenshot_max_retries` - Retry configuration

## Safety Features

### Automatic Backups
- **Timestamped backups**: `social_media_accounts_YYYYMMDD_HHMMSS.db`
- **Integrity verification**: Size and structure checks
- **Backup before restore**: Creates safety backup before rollback

### Rollback Protection
- **Version detection**: Identifies current database version
- **Migration tracking**: Prevents duplicate migrations
- **Integrity checks**: Verifies database after operations

## Backup Storage

Backups are stored in the `database_backups/` directory:

```
database_backups/
├── social_media_accounts_20250813_180000.db  # Before v3 migration
├── social_media_accounts_20250813_181500.db  # Before restore
└── social_media_accounts_20250813_182000.db  # Latest backup
```

## Troubleshooting

### Migration Already Applied
```
ℹ️ Migration v3_add_screenshots already applied
```
**Solution**: Database is already up to date, no action needed.

### Backup Creation Failed
```
❌ Backup failed: [permission denied]
```
**Solutions**:
- Check file permissions
- Ensure disk space available
- Run with appropriate user permissions

### Migration Failed
```
❌ Migration failed: [error details]
```
**Solutions**:
1. Check database isn't in use by another process
2. Verify database file permissions
3. Use interactive mode for detailed error info
4. Restore from backup if needed

### Database Integrity Issues
```
❌ Database integrity check failed
```
**Solutions**:
1. Stop the application
2. Restore from most recent backup
3. Contact support if issues persist

## Production Deployment Steps

1. **Stop the application**:
   ```bash
   # Stop your web server/application
   systemctl stop japdash  # or similar
   ```

2. **Pull the latest code**:
   ```bash
   git pull origin master
   ```

3. **Run the migration**:
   ```bash
   python migrate_database.py --migrate
   ```

4. **Verify the migration**:
   ```bash
   python migrate_database.py
   # Select option 5: Verify Database Integrity
   ```

5. **Start the application**:
   ```bash
   systemctl start japdash  # or similar
   ```

6. **Configure screenshot settings** in the admin panel:
   - Add your GoLogin API key and browser profile IDs
   - Add your screenshot service API key
   - Test screenshot functionality

## Rollback Process

If you need to rollback:

1. **Stop the application**
2. **Use the migration script**:
   ```bash
   python migrate_database.py
   # Select option 4: Restore from Backup
   # Choose your pre-migration backup
   ```
3. **Checkout previous git version** (if needed)
4. **Start the application**

## Database Version History

- **v0/unknown** - Original database without migration tracking
- **v1_initial** - Basic tables (accounts, actions, execution_history)
- **v2_add_tags** - Added tags functionality  
- **v3_add_screenshots** - Added screenshot functionality ← **Current Target**

## File Safety

The migration script:
- ✅ **Never modifies** the original database until backup is confirmed
- ✅ **Creates timestamped backups** before any changes
- ✅ **Verifies integrity** before and after operations  
- ✅ **Provides rollback** functionality
- ✅ **Preserves all existing data**

---

**Need help?** The migration script provides detailed status information and error messages to guide you through any issues.