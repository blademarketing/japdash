# Screenshot Database Migration Plan

## Overview
Add comprehensive screenshot functionality to track before/after states for all order executions (RSS triggers and instant executions).

## New Table: screenshots

```sql
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL,           -- Foreign key to execution_history table
    screenshot_type TEXT NOT NULL,           -- 'before' or 'after'
    url TEXT NOT NULL,                       -- URL that was screenshotted
    platform TEXT NOT NULL,                 -- 'facebook', 'instagram', 'x', 'tiktok'
    
    -- GoLogin Configuration
    gologin_profile_id TEXT NOT NULL,       -- GoLogin profile ID used
    
    -- Screenshot Data
    screenshot_data TEXT,                    -- Base64 encoded PNG data
    file_path TEXT,                         -- Optional: file system path if stored as file
    
    -- Capture Metadata
    dimensions_width INTEGER,               -- Screenshot width in pixels
    dimensions_height INTEGER,              -- Screenshot height in pixels
    capture_timestamp TIMESTAMP NOT NULL,   -- When screenshot was taken
    
    -- Status Tracking
    status TEXT DEFAULT 'pending',          -- 'pending', 'capturing', 'completed', 'failed'
    error_message TEXT,                     -- Error details if status='failed'
    retry_count INTEGER DEFAULT 0,          -- Number of retry attempts
    
    -- Performance Metrics
    capture_duration_ms INTEGER,            -- Time taken to capture screenshot
    container_id TEXT,                      -- Docker container ID used for capture
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (execution_id) REFERENCES execution_history (id) ON DELETE CASCADE,
    
    -- Ensure only one before/after per execution
    UNIQUE(execution_id, screenshot_type)
);
```

## Indexes for Performance

```sql
CREATE INDEX idx_screenshots_execution_id ON screenshots(execution_id);
CREATE INDEX idx_screenshots_type ON screenshots(screenshot_type);
CREATE INDEX idx_screenshots_status ON screenshots(status);
CREATE INDEX idx_screenshots_platform ON screenshots(platform);
CREATE INDEX idx_screenshots_timestamp ON screenshots(capture_timestamp);
```

## Settings Table Additions

Add GoLogin configuration to the settings table:

```sql
INSERT OR REPLACE INTO settings (key, value) VALUES 
('gologin_api_key', ''),
('gologin_facebook_profile_id', ''),
('gologin_instagram_profile_id', ''),
('gologin_twitter_profile_id', ''),
('gologin_tiktok_profile_id', ''),
('screenshot_enabled', 'true'),
('screenshot_store_as_files', 'false'),
('screenshot_max_retries', '3');
```

## Migration Strategy for Production

### Phase 1: Schema Addition (Safe)
1. Add new `screenshots` table - no impact on existing functionality
2. Add settings for GoLogin configuration
3. Deploy migration without enabling screenshot capture

### Phase 2: Feature Enablement (Gradual)
1. Deploy screenshot client and capture logic
2. Enable screenshots for new executions only
3. Monitor performance and storage usage
4. Gradually enable for all executions

### Phase 3: Backfill (Optional)
1. Create background job to capture screenshots for recent executions
2. Only for executions where target URLs are still valid
3. Run during low-traffic periods

## Data Flow Integration

### For RSS Triggers:
1. RSS poller detects new post
2. Create execution_history record
3. **NEW**: Capture "before" screenshot of target URL
4. Execute JAP order
5. **NEW**: Capture "after" screenshot (with delay for processing)
6. Update execution status

### For Instant Executions:
1. User submits quick execute form
2. Create execution_history record  
3. **NEW**: Capture "before" screenshot
4. Execute JAP order
5. **NEW**: Capture "after" screenshot (with delay)
6. Display results with screenshots

## Storage Considerations

### Option A: Database Storage (Current Plan)
- Store base64 PNG data in `screenshot_data` column
- Pros: Simple, atomic with execution data, no file system dependencies
- Cons: Database size growth, memory usage for large screenshots
- Estimated size: ~100-500KB per screenshot = ~200KB-1MB per execution

### Option B: File System Storage (Future Option)
- Store screenshots as files, reference path in `file_path` column
- Pros: Better performance, smaller database, easier to serve images
- Cons: File system management, backup complexity, orphaned files risk

### Current Recommendation: 
Start with database storage for simplicity, migrate to file system if size becomes an issue.

## Error Handling

### Screenshot Capture Failures:
1. Record failure in `screenshots` table with error message
2. Continue with order execution (screenshots are supplementary)
3. Implement retry logic with exponential backoff
4. Alert if failure rate exceeds threshold

### GoLogin API Issues:
1. Graceful degradation - continue without screenshots
2. Log errors for debugging
3. Display warning in UI if screenshots unavailable

## Performance Impact

### Database Size Growth:
- Current execution_history: ~49 records
- With screenshots: Each execution = 1 execution + 2 screenshots
- Estimated monthly growth: ~100 executions = ~20-100MB database growth

### API Performance:
- Screenshot capture adds ~15-30 seconds per execution
- Run asynchronously to avoid blocking order execution
- Consider queuing system for high-volume scenarios

## Monitoring & Observability

### Key Metrics:
1. Screenshot capture success rate
2. Average capture time per platform
3. Storage growth rate
4. GoLogin API response times
5. Error rates by platform/profile

### Alerts:
1. Screenshot failure rate > 20%
2. GoLogin API errors
3. Database size growth exceeding projections
4. Capture time exceeding 60 seconds

## Security Considerations

### API Key Security:
- Store GoLogin API key encrypted in settings
- Never log API keys in error messages
- Restrict API key access to screenshot service only

### Screenshot Data:
- Screenshots may contain sensitive user content
- Consider data retention policies
- Ensure proper access controls

## Testing Strategy

### Unit Tests:
1. Screenshot client API integration
2. Database operations (CRUD for screenshots)
3. Error handling and retry logic
4. GoLogin profile selection logic

### Integration Tests:
1. End-to-end screenshot capture flow
2. Migration testing on sample data
3. Performance testing with concurrent captures
4. Failure scenarios and recovery

### Manual Testing:
1. Test each platform (Facebook, Instagram, X, TikTok)
2. Verify before/after screenshots accuracy
3. Test with various URL types and formats
4. Verify UI display of screenshots

## Rollout Plan

### Week 1: Infrastructure
- Deploy database migration
- Add GoLogin configuration to settings UI
- Implement screenshot client (without enabling)

### Week 2: Core Integration  
- Integrate screenshot capture into execution flow
- Enable for instant executions first (lower volume)
- Monitor performance and fix issues

### Week 3: Full Deployment
- Enable screenshots for RSS triggers
- Add UI components to display screenshots
- Monitor system performance and user feedback

### Week 4: Optimization
- Performance tuning based on real usage
- Consider file system storage if needed
- Documentation and user training

## Recovery Planning

### If Screenshots Impact Performance:
1. Disable screenshot capture via feature flag
2. Make screenshot capture optional per execution
3. Implement queueing/batch processing
4. Consider reducing screenshot dimensions

### If Storage Grows Too Fast:
1. Implement automatic cleanup of old screenshots
2. Migrate to file system storage
3. Add compression for stored images
4. Implement selective screenshot capture

## Success Criteria

### Functional:
- 90%+ screenshot capture success rate
- Before/after screenshots display correctly in UI
- No impact on core order execution performance
- Smooth migration with zero data loss

### Technical:
- Database migration completes without errors
- Screenshot capture times < 30 seconds average
- System remains responsive under load
- Proper error handling and user feedback

### Business:
- Users can visually verify order effectiveness
- Improved debugging capability for failed orders  
- Enhanced audit trail for compliance
- Foundation for future analytics features