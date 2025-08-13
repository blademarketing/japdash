# Claude Instructions for JAP Dashboard

This file contains specific instructions for Claude when working on the JAP Dashboard project to ensure consistency, quality, and alignment with the established architecture and documentation.

## 📚 Documentation-First Development

**CRITICAL**: Before building any new functionality, ALWAYS:

1. **Read the relevant documentation** in the `docs/` directory
2. **Follow established patterns** from existing code and documentation  
3. **Update documentation** when adding new features
4. **Maintain consistency** with the existing system architecture

### Key Documentation References

**For API Development**:
- Read `docs/api/endpoints.md` - Follow existing API patterns
- Check `docs/api/external-apis.md` - For integration patterns
- Use `docs/architecture/data-flow.md` - For data flow understanding

**For Database Changes**:
- Review `docs/database-schema.md` - Understand schema and relationships
- Follow migration patterns shown in the documentation
- Maintain referential integrity and naming conventions

**For Frontend Work**:
- Study `docs/ui/design-guide.md` - Follow UI patterns and component structure
- Reference `docs/ui/user-workflows.md` - Understand user interaction patterns
- Maintain consistency with Tailwind CSS classes and JavaScript patterns

**For System Architecture**:
- Consult `docs/architecture/system-overview.md` - Understand component relationships
- Follow established integration patterns with external APIs
- Maintain separation of concerns between components

## 🏗️ Development Guidelines

### 1. Code Architecture Principles

**Follow Established Patterns**:
- **Flask Routes**: Use `@smart_auth_required` decorator for API endpoints
- **Database Operations**: Use transaction patterns with proper error handling
- **External API Calls**: Follow the client wrapper patterns (jap_client.py, rss_client.py, llm_client.py)
- **Frontend**: Use the `SocialMediaManager` class pattern for new functionality

**Authentication Pattern**:
```python
@app.route('/api/new-endpoint', methods=['POST'])
@smart_auth_required
def new_endpoint():
    """Follow this pattern for all API endpoints"""
    try:
        data = request.get_json()
        # Validate input
        # Process request
        # Return JSON response
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Database Transaction Pattern**:
```python
def database_operation():
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        # Database operations
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 2. Database Schema Guidelines

**When Adding New Tables**:
- Follow naming conventions (lowercase, underscore_separated)
- Include `id INTEGER PRIMARY KEY AUTOINCREMENT`
- Include `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- Add proper foreign key constraints with CASCADE options
- Create appropriate indexes for frequently queried columns

**Migration Pattern**:
```python
def add_new_feature_migration():
    """Add to apply_database_migrations() function"""
    conn.execute("""
        CREATE TABLE new_feature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
```

### 3. Frontend Development Guidelines

**JavaScript Class Pattern**:
- Add new methods to the `SocialMediaManager` class
- Follow async/await pattern for API calls
- Use consistent error handling with `showToast()`
- Maintain the modal-based interaction pattern

**CSS/Styling**:
- Use existing Tailwind CSS classes from the design guide
- Follow the color system and component patterns
- Maintain responsive design principles
- Use consistent spacing (px-4, py-2, mb-4, etc.)

**Event Handling**:
```javascript
// Follow this pattern for new features
bindNewFeatureEvents() {
    document.getElementById('newFeatureBtn').addEventListener('click', () => this.openNewFeatureModal());
    document.getElementById('newFeatureForm').addEventListener('submit', (e) => this.handleNewFeatureSubmit(e));
}
```

### 4. External API Integration Guidelines

**Follow Client Wrapper Pattern**:
- Create dedicated client classes for new external APIs
- Implement caching where appropriate
- Include comprehensive error handling
- Follow the retry logic patterns from existing clients

**Error Handling**:
```python
class NewAPIError(Exception):
    """Custom exception for new API integration"""
    pass

def handle_api_error(error):
    """Standard error handling pattern"""
    # Log error
    # Return user-friendly message
    # Maintain system stability
```

## 🔄 Feature Development Workflow

### When Adding New Features

1. **Planning Phase**:
   - Read relevant documentation sections
   - Understand existing patterns and architecture
   - Plan database changes if needed
   - Consider impact on existing functionality

2. **Implementation Phase**:
   - Follow established code patterns
   - Implement backend API endpoints first
   - Add database migrations if needed
   - Implement frontend integration
   - Follow UI/UX patterns from design guide

3. **Documentation Phase** (MANDATORY):
   - Update API endpoints documentation
   - Update database schema documentation if changed
   - Add user workflow documentation for UI changes
   - Update system architecture docs if needed

4. **Testing Phase**:
   - Test new functionality manually
   - Verify existing functionality still works
   - Test error conditions and edge cases
   - Verify documentation accuracy

### Documentation Update Requirements

**For New API Endpoints**:
- Add to `docs/api/endpoints.md` with full request/response examples
- Include error handling scenarios
- Document authentication requirements

**For Database Changes**:
- Update `docs/database-schema.md` with new tables/columns
- Document relationships and constraints
- Update any affected data flow diagrams

**For UI Changes**:
- Update `docs/ui/user-workflows.md` with new interaction patterns
- Add new components to `docs/ui/design-guide.md`
- Include screenshots or diagrams if helpful

**For System Architecture Changes**:
- Update `docs/architecture/system-overview.md`
- Update `docs/architecture/data-flow.md` if data flows change
- Document new integration patterns

## 🛡️ Quality Assurance Guidelines

### Code Quality Standards

**Python Code**:
- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Include docstrings for functions and classes
- Implement proper exception handling
- Use type hints where appropriate

**JavaScript Code**:
- Use ES6+ features consistently
- Follow existing naming conventions
- Implement proper error handling
- Use async/await for API calls
- Comment complex logic

**Database Design**:
- Normalize data appropriately
- Use proper data types
- Include necessary indexes
- Maintain referential integrity
- Follow naming conventions

### Security Considerations

**Always Consider**:
- Input validation and sanitization
- SQL injection prevention (use parameterized queries)
- XSS prevention
- Authentication and authorization
- API key security (never commit keys)
- Session management

**Pattern for Input Validation**:
```python
def validate_input(data, required_fields):
    """Standard input validation pattern"""
    if not data:
        raise ValueError("Request body required")
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    return True
```

## 🧪 Testing Guidelines

### Manual Testing Requirements

**For New Features**:
- Test happy path scenarios
- Test error conditions
- Test edge cases
- Verify integration with existing features
- Test on different screen sizes (responsive)

**Database Testing**:
- Verify migrations work on existing data
- Test foreign key constraints
- Verify indexes are working
- Check data integrity

**API Testing**:
- Test all new endpoints with curl or Postman
- Verify authentication requirements
- Test error responses
- Verify request/response formats match documentation

## 📝 Communication Guidelines

### When Working on Issues

**Always**:
- Reference relevant documentation sections
- Explain how changes align with existing architecture
- Document any deviations from established patterns
- Update documentation as part of the implementation

**Code Comments**:
- Comment complex business logic
- Reference documentation sections where relevant
- Explain non-obvious design decisions
- Document external API integration points

### Error Messages

**User-Facing Errors**:
- Provide clear, actionable error messages
- Avoid technical jargon
- Include suggestions for resolution when possible

**Developer Errors**:
- Include detailed error information
- Log full stack traces for debugging
- Reference documentation for troubleshooting

## 🚀 Performance Considerations

### Database Performance
- Use appropriate indexes for new queries
- Consider query optimization for large datasets
- Implement pagination for list endpoints
- Use transactions appropriately

### Caching Strategy
- Follow existing caching patterns
- Consider cache invalidation strategies
- Document caching decisions

### External API Efficiency
- Implement rate limiting
- Use batching where possible
- Cache responses appropriately
- Handle API failures gracefully

## 📋 Checklist for New Features

Before considering a feature complete:

- [ ] Follows established code patterns
- [ ] Includes proper error handling
- [ ] Updates relevant documentation
- [ ] Maintains database schema consistency
- [ ] Follows UI/UX design patterns
- [ ] Includes input validation
- [ ] Handles security considerations
- [ ] Tested manually with various scenarios
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

## 🔗 Quick Reference Links

**Documentation Structure**:
- `docs/README.md` - Documentation hub
- `docs/guides/getting-started.md` - Development setup
- `docs/api/endpoints.md` - API reference
- `docs/database-schema.md` - Database structure
- `docs/architecture/system-overview.md` - System architecture
- `docs/ui/design-guide.md` - UI patterns

**Key Files to Reference**:
- `app.py` - Main Flask application patterns
- `static/app.js` - Frontend JavaScript patterns
- `templates/index.html` - HTML structure patterns
- `jap_client.py`, `rss_client.py`, `llm_client.py` - API integration patterns

Remember: The goal is to maintain a consistent, well-documented, and maintainable codebase that other developers can easily understand and extend.