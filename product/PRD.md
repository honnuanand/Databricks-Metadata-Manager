# Product Requirements Document (PRD)
## Databricks Metadata Manager

### 1. Executive Summary
The Databricks Metadata Manager is a web-based application that enables collaborative metadata management for Databricks catalog entities (schemas, tables, columns) with an approval workflow. It addresses the limitation that only table owners can update comments by implementing a service principal-based system with user suggestions and approvals.

### 2. Problem Statement
- Only table owners can update comments on Databricks entities (schemas, tables, columns)
- No collaborative way for business users to suggest metadata updates
- Lack of approval workflow for metadata changes
- No centralized interface for viewing and managing Databricks catalog metadata

### 3. Solution Overview
A ReactJS/MUI frontend with FastAPI backend that:
- Discovers Databricks catalog entities via service principal
- Allows users to suggest comment updates
- Implements approval workflow for metadata changes
- Applies approved changes using service principal credentials

### 4. User Personas

#### 4.1 Regular Users (Business/Technical Users)
- **Role**: Suggest metadata updates
- **Capabilities**:
  - Browse catalog, schemas, tables, and columns
  - View existing comments
  - Suggest new/updated comments
  - Track status of their suggestions
  - View feedback from approvers

#### 4.2 Approvers
- **Role**: Review and approve metadata suggestions
- **Capabilities**:
  - All Regular User capabilities
  - View pending approval requests
  - Approve/reject suggestions
  - Provide feedback on suggestions
  - Batch approve multiple suggestions

#### 4.3 Service Principal (System User)
- **Role**: Apply approved changes to Databricks
- **Capabilities**:
  - Ownership access to catalog entities
  - Execute SQL statements to update comments
  - Automated application of approved changes

### 5. Functional Requirements

#### 5.1 Authentication & Authorization
- User authentication system
- Role-based access control (Regular User, Approver)
- Service principal configuration for Databricks access

#### 5.2 Catalog Discovery
- List accessible catalogs
- Browse schemas within catalogs
- View tables within schemas
- Display columns for each table
- Show existing comments at all levels

#### 5.3 Comment Management
- Display current comments for entities
- Allow users to suggest new comments
- Allow users to edit existing comments
- Track comment history
- Support markdown formatting in comments

#### 5.4 Approval Workflow
- Submit suggestions for approval
- Pending approval status indication
- Approval queue for approvers
- Approve/reject with feedback
- Email notifications for status changes
- Audit trail of all changes

#### 5.5 Databricks Integration
- Connect using Databricks SDK
- Execute SQL statements for comment updates
- Handle permissions and error cases
- Retry mechanism for failed updates

### 6. Non-Functional Requirements

#### 6.1 Performance
- Page load time < 2 seconds
- Search/filter response < 1 second
- Support 100+ concurrent users
- Efficient caching of catalog metadata

#### 6.2 Security
- Secure storage of service principal credentials
- Encrypted communication (HTTPS)
- Session management and timeout
- Audit logging of all actions

#### 6.3 Usability
- Intuitive navigation
- Responsive design for various screen sizes
- Clear status indicators
- Helpful error messages
- Keyboard navigation support

#### 6.4 Reliability
- 99.9% uptime
- Graceful error handling
- Data consistency guarantees
- Backup and recovery procedures

### 7. User Interface Requirements

#### 7.1 Main Dashboard
- Catalog/Schema/Table hierarchy view
- Search and filter capabilities
- Quick access to pending items
- Activity feed of recent changes

#### 7.2 Entity Detail View
- Display entity metadata
- Show existing comments
- Edit/suggest interface
- Comment history
- Related entities navigation

#### 7.3 Approval Dashboard
- List of pending approvals
- Filtering and sorting options
- Bulk selection and actions
- Preview of suggested changes
- Approval/rejection interface

#### 7.4 User Profile
- View own suggestions
- Track approval status
- Notification preferences
- Activity history

### 8. API Requirements

#### 8.1 Authentication Endpoints
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- GET /api/auth/user

#### 8.2 Catalog Endpoints
- GET /api/catalogs
- GET /api/catalogs/{catalog}/schemas
- GET /api/schemas/{schema}/tables
- GET /api/tables/{table}/columns

#### 8.3 Comment Endpoints
- GET /api/comments/{entity_type}/{entity_id}
- POST /api/comments/suggest
- PUT /api/comments/{comment_id}
- GET /api/comments/history/{entity_id}

#### 8.4 Approval Endpoints
- GET /api/approvals/pending
- POST /api/approvals/{id}/approve
- POST /api/approvals/{id}/reject
- GET /api/approvals/history

### 9. Data Model

#### 9.1 Core Entities
- Users (id, email, name, role, created_at)
- Comments (id, entity_type, entity_id, content, status, created_by, created_at)
- Approvals (id, comment_id, approver_id, status, feedback, created_at)
- AuditLog (id, user_id, action, entity_type, entity_id, timestamp)

### 10. Integration Requirements
- Databricks workspace connection
- Databricks SQL warehouse or cluster
- Service principal with appropriate permissions
- Email service for notifications
- Optional: SSO integration

### 11. Success Metrics
- Number of metadata updates suggested
- Approval turnaround time
- User adoption rate
- Metadata coverage percentage
- System uptime and performance

### 12. Timeline & Phases

#### Phase 1: MVP (Weeks 1-4)
- Basic authentication
- Catalog browsing
- Comment suggestions
- Simple approval workflow

#### Phase 2: Enhanced Features (Weeks 5-8)
- Advanced search and filters
- Bulk operations
- Email notifications
- Audit logging

#### Phase 3: Advanced Features (Weeks 9-12)
- SSO integration
- Advanced permissions
- Analytics dashboard
- API for external integrations

### 13. Risks & Mitigations
- **Risk**: Databricks API limitations
  - **Mitigation**: Implement caching and batch operations
- **Risk**: Service principal permission issues
  - **Mitigation**: Clear documentation and validation checks
- **Risk**: User adoption
  - **Mitigation**: Training materials and intuitive UI

### 14. Future Enhancements
- AI-powered comment suggestions
- Integration with data lineage tools
- Support for additional metadata types
- Mobile application
- Automated quality checks for comments