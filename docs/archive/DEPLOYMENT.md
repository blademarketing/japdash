# Deployment Guide for Tag System Update

## Important: Database Migration Required

This update adds new database tables for the tagging system. You MUST apply the migration before running the new code.

## Deployment Steps

### 1. Backup Your Database (CRITICAL)
```bash
cd /path/to/production/japdash
cp social_trigger.db social_trigger_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. Update the Code
```bash
git pull origin master
```

### 3. The Migration Will Apply Automatically
The app now includes automatic migration on startup. When you restart the service, it will:
- Check if the tags tables exist
- Create them if they don't
- Track the migration in a new `schema_migrations` table
- Log the migration to the console

### 4. Restart Your Service
```bash
# However you normally restart your service
sudo systemctl restart japdash
# or
pm2 restart japdash
# or
./restart.sh
```

### 5. Verify Migration
Check the logs to ensure migration was applied:
```bash
# Check console logs for "Database migration v2_add_tags applied"
tail -f console.log | grep "migration"
```

Or check the database directly:
```bash
sqlite3 social_trigger.db "SELECT * FROM schema_migrations;"
# Should show: v2_add_tags|2025-07-27 ...
```

## Manual Migration (Alternative)

If you prefer to apply the migration manually before starting:

```bash
# Apply migration manually
sqlite3 social_trigger.db < migrations/v2_add_tags.sql

# Then pull and restart
git pull
# restart service
```

## Rollback Plan

If something goes wrong:
```bash
# Stop the service
sudo systemctl stop japdash

# Restore backup
cp social_trigger_backup_[timestamp].db social_trigger.db

# Use previous version
git checkout [previous-commit-hash]

# Restart
sudo systemctl start japdash
```

## What's New

1. **Tags System**: Tag accounts for better organization
2. **Copy Actions**: Copy actions between accounts on the same platform
3. **Multi-Tag Filtering**: Filter accounts by multiple tags
4. **Automatic Migrations**: Database updates apply automatically

The migration system will handle all future database changes automatically!