# Technical Design Document (TDD)
## Databricks Metadata Manager

### 1. System Architecture

#### 1.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    User Browser                          │
│                  (React + MUI + Vite)                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                         │
│              (REST API + WebSockets)                     │
├──────────────────────────────────────────────────────────┤
│              Authentication & Authorization              │
│                    (JWT + RBAC)                         │
├──────────────────────────────────────────────────────────┤
│                 Business Logic Layer                     │
│          (Comment Management, Approval Workflow)         │
├──────────────────────────────────────────────────────────┤
│                    Data Access Layer                     │
│              (SQLAlchemy ORM + Alembic)                 │
└────────┬───────────────────────────┬────────────────────┘
         │                           │
┌────────▼────────┐         ┌────────▼────────┐
│   PostgreSQL    │         │   Databricks     │
│    Database     │         │   Workspace      │
│  (Metadata DB)  │         │  (via SDK/SQL)   │
└─────────────────┘         └─────────────────┘
```

### 2. Technology Stack

#### 2.1 Frontend
- **Framework**: React 18.x with TypeScript
- **Build Tool**: Vite 5.x
- **UI Library**: Material-UI (MUI) v5
- **State Management**: Redux Toolkit + RTK Query
- **Routing**: React Router v6
- **Form Handling**: React Hook Form
- **Data Grid**: MUI DataGrid Pro
- **Authentication**: JWT with axios interceptors
- **Testing**: Vitest + React Testing Library

#### 2.2 Backend
- **Framework**: FastAPI 0.100+
- **Language**: Python 3.11+
- **Database ORM**: SQLAlchemy 2.0
- **Migration Tool**: Alembic
- **Authentication**: python-jose[cryptography] for JWT
- **Databricks SDK**: databricks-sdk
- **Task Queue**: Celery + Redis (for async operations)
- **Testing**: pytest + pytest-asyncio
- **API Documentation**: OpenAPI/Swagger (built-in)

#### 2.3 Infrastructure
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

### 3. Backend Design

#### 3.1 Project Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── catalogs.py
│   │   │   ├── comments.py
│   │   │   ├── approvals.py
│   │   │   └── users.py
│   │   └── dependencies/
│   │       ├── auth.py
│   │       ├── database.py
│   │       └── databricks.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── settings.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   ├── models/
│   │   ├── user.py
│   │   ├── comment.py
│   │   ├── approval.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── comment.py
│   │   ├── approval.py
│   │   └── databricks.py
│   ├── services/
│   │   ├── databricks_service.py
│   │   ├── comment_service.py
│   │   ├── approval_service.py
│   │   └── notification_service.py
│   └── main.py
├── alembic/
├── tests/
├── requirements.txt
├── Dockerfile
└── .env.example
```

#### 3.2 Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255),
    role VARCHAR(50) NOT NULL, -- 'regular_user', 'approver', 'admin'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL, -- 'catalog', 'schema', 'table', 'column'
    entity_catalog VARCHAR(255) NOT NULL,
    entity_schema VARCHAR(255),
    entity_table VARCHAR(255),
    entity_column VARCHAR(255),
    current_comment TEXT,
    suggested_comment TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'draft', 'pending', 'approved', 'rejected', 'applied'
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Approvals table
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID REFERENCES comments(id),
    approver_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL, -- 'approved', 'rejected', 'request_changes'
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_comments_status ON comments(status);
CREATE INDEX idx_comments_entity ON comments(entity_catalog, entity_schema, entity_table);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

#### 3.3 API Design

##### Authentication Endpoints
```yaml
POST /api/v1/auth/register
  Body: {email, username, password, full_name}
  Response: {user_id, message}

POST /api/v1/auth/login
  Body: {username, password}
  Response: {access_token, refresh_token, user}

POST /api/v1/auth/refresh
  Body: {refresh_token}
  Response: {access_token}

POST /api/v1/auth/logout
  Headers: Authorization: Bearer {token}
  Response: {message}
```

##### Catalog Management Endpoints
```yaml
GET /api/v1/catalogs
  Query: ?search=string
  Response: [{name, comment, table_count, schema_count}]

GET /api/v1/catalogs/{catalog}/schemas
  Response: [{name, comment, table_count}]

GET /api/v1/schemas/{catalog}/{schema}/tables
  Response: [{name, comment, column_count, row_count}]

GET /api/v1/tables/{catalog}/{schema}/{table}/columns
  Response: [{name, data_type, comment, nullable}]
```

##### Comment Management Endpoints
```yaml
GET /api/v1/comments
  Query: ?entity_type=table&status=pending&user_id=uuid
  Response: [{id, entity_info, suggested_comment, status, created_by, created_at}]

POST /api/v1/comments
  Body: {entity_type, entity_path, suggested_comment}
  Response: {id, status, message}

PUT /api/v1/comments/{id}
  Body: {suggested_comment}
  Response: {id, status, message}

DELETE /api/v1/comments/{id}
  Response: {message}

GET /api/v1/comments/{id}/history
  Response: [{action, user, timestamp, details}]
```

##### Approval Endpoints
```yaml
GET /api/v1/approvals/pending
  Query: ?page=1&size=20&sort=created_at
  Response: {items: [...], total, page, pages}

POST /api/v1/approvals/{comment_id}/approve
  Body: {feedback?}
  Response: {message, status}

POST /api/v1/approvals/{comment_id}/reject
  Body: {feedback}
  Response: {message, status}

POST /api/v1/approvals/batch
  Body: {comment_ids, action, feedback?}
  Response: {processed, failed, messages}
```

### 4. Frontend Design

#### 4.1 Project Structure
```
front-end/
├── src/
│   ├── components/
│   │   ├── catalog/
│   │   │   ├── CatalogBrowser.tsx
│   │   │   ├── SchemaList.tsx
│   │   │   ├── TableList.tsx
│   │   │   └── ColumnList.tsx
│   │   ├── common/
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── approval/
│   │   │   ├── ApprovalDashboard.tsx
│   │   │   ├── ApprovalCard.tsx
│   │   │   └── ApprovalActions.tsx
│   │   └── comments/
│   │       ├── CommentEditor.tsx
│   │       ├── CommentHistory.tsx
│   │       └── CommentStatus.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Login.tsx
│   │   ├── CatalogExplorer.tsx
│   │   ├── ApprovalQueue.tsx
│   │   └── UserProfile.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.service.ts
│   │   ├── catalog.service.ts
│   │   └── comment.service.ts
│   ├── store/
│   │   ├── store.ts
│   │   ├── authSlice.ts
│   │   ├── catalogSlice.ts
│   │   └── commentSlice.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useCatalog.ts
│   │   └── useComments.ts
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── helpers.ts
│   │   └── validators.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── .env.example
```

#### 4.2 Component Architecture

##### Key Components

1. **CatalogBrowser**
   - Hierarchical tree view of catalogs/schemas/tables
   - Search and filter functionality
   - Lazy loading for performance
   - Context menu for quick actions

2. **CommentEditor**
   - Rich text editor with markdown support
   - Side-by-side preview
   - Template suggestions
   - Auto-save drafts

3. **ApprovalDashboard**
   - Filterable list of pending approvals
   - Batch selection and actions
   - Quick preview modal
   - Statistics and charts

4. **EntityDetailView**
   - Display all metadata for selected entity
   - Current vs suggested comment comparison
   - Related entities navigation
   - Action buttons based on user role

#### 4.3 State Management

```typescript
// Store structure
interface AppState {
  auth: {
    user: User | null;
    isAuthenticated: boolean;
    loading: boolean;
  };
  catalog: {
    catalogs: Catalog[];
    selectedCatalog: string | null;
    schemas: Schema[];
    tables: Table[];
    columns: Column[];
    loading: boolean;
    error: string | null;
  };
  comments: {
    userComments: Comment[];
    pendingApprovals: Comment[];
    filters: CommentFilters;
    loading: boolean;
  };
  ui: {
    sidebarOpen: boolean;
    theme: 'light' | 'dark';
    notifications: Notification[];
  };
}
```

### 5. Databricks Integration

#### 5.1 Service Principal Setup
```python
class DatabricksService:
    def __init__(self):
        self.client = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=settings.DATABRICKS_TOKEN,
            # Or use service principal
            client_id=settings.DATABRICKS_CLIENT_ID,
            client_secret=settings.DATABRICKS_CLIENT_SECRET
        )
    
    async def list_catalogs(self):
        return await self.client.catalogs.list()
    
    async def update_comment(self, entity_type, entity_path, comment):
        sql = self._build_comment_sql(entity_type, entity_path, comment)
        return await self.client.sql.execute(sql)
```

#### 5.2 Comment Update SQL Generation
```python
def build_comment_sql(entity_type: str, entity_path: dict, comment: str) -> str:
    comment_escaped = comment.replace("'", "''")
    
    if entity_type == "table":
        return f"""
        ALTER TABLE {entity_path['catalog']}.{entity_path['schema']}.{entity_path['table']}
        SET COMMENT '{comment_escaped}'
        """
    elif entity_type == "column":
        return f"""
        ALTER TABLE {entity_path['catalog']}.{entity_path['schema']}.{entity_path['table']}
        ALTER COLUMN {entity_path['column']}
        COMMENT '{comment_escaped}'
        """
    elif entity_type == "schema":
        return f"""
        ALTER SCHEMA {entity_path['catalog']}.{entity_path['schema']}
        SET COMMENT '{comment_escaped}'
        """
```

### 6. Security Considerations

#### 6.1 Authentication & Authorization
- JWT tokens with short expiration (15 minutes)
- Refresh tokens with longer expiration (7 days)
- Role-based access control (RBAC)
- API rate limiting per user
- Session management with Redis

#### 6.2 Data Security
- Encryption at rest for sensitive data
- TLS 1.3 for all communications
- Input validation and sanitization
- SQL injection prevention via parameterized queries
- XSS protection with Content Security Policy

#### 6.3 Audit & Compliance
- Comprehensive audit logging
- Data retention policies
- GDPR compliance for user data
- Regular security scans
- Penetration testing

### 7. Performance Optimization

#### 7.1 Backend Optimizations
- Database query optimization with indexes
- Caching strategy with Redis
- Pagination for large datasets
- Async processing for heavy operations
- Connection pooling for database

#### 7.2 Frontend Optimizations
- Code splitting with Vite
- Lazy loading of components
- Virtual scrolling for large lists
- Image optimization
- Service worker for offline support
- Memoization of expensive computations

### 8. Monitoring & Logging

#### 8.1 Application Metrics
- API response times
- Error rates
- User activity metrics
- Database query performance
- Cache hit rates

#### 8.2 Infrastructure Metrics
- CPU and memory usage
- Network latency
- Database connections
- Queue lengths
- Disk usage

#### 8.3 Business Metrics
- Comments suggested per day
- Approval turnaround time
- User engagement
- Feature adoption rates

### 9. Deployment Strategy

#### 9.1 Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENV=development
    volumes:
      - ./backend:/app
  
  frontend:
    build: ./front-end
    ports:
      - "5173:5173"
    volumes:
      - ./front-end:/app
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=metadata_manager
  
  redis:
    image: redis:7-alpine
```

#### 9.2 Production Deployment
- Container orchestration with Kubernetes
- Blue-green deployment strategy
- Health checks and readiness probes
- Auto-scaling based on load
- CDN for static assets

### 10. Testing Strategy

#### 10.1 Backend Testing
- Unit tests: 80% coverage minimum
- Integration tests for API endpoints
- Database migration tests
- Performance tests with locust
- Security tests with OWASP ZAP

#### 10.2 Frontend Testing
- Component unit tests with Vitest
- Integration tests with React Testing Library
- E2E tests with Playwright
- Visual regression tests
- Accessibility tests with axe-core

### 11. CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run backend tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest --cov=app

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run frontend tests
        run: |
          cd front-end
          npm install
          npm run test

  deploy:
    needs: [backend-tests, frontend-tests]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Deployment steps
```

### 12. Documentation

#### 12.1 API Documentation
- Auto-generated OpenAPI/Swagger docs
- Postman collection
- API versioning strategy
- Change logs

#### 12.2 User Documentation
- User guide with screenshots
- Video tutorials
- FAQ section
- Troubleshooting guide

#### 12.3 Developer Documentation
- Setup instructions
- Architecture diagrams
- Code style guide
- Contributing guidelines

### 13. Maintenance & Support

#### 13.1 Regular Maintenance
- Weekly dependency updates
- Monthly security patches
- Quarterly performance reviews
- Annual architecture reviews

#### 13.2 Support Structure
- Tier 1: User documentation and FAQ
- Tier 2: Support ticket system
- Tier 3: Engineering team escalation
- SLA: 24-hour response for critical issues

### 14. Scalability Considerations

#### 14.1 Horizontal Scaling
- Stateless API design
- Load balancer configuration
- Database read replicas
- Caching layer expansion

#### 14.2 Vertical Scaling
- Resource monitoring
- Auto-scaling policies
- Database optimization
- Query performance tuning

### 15. Disaster Recovery

#### 15.1 Backup Strategy
- Daily database backups
- Point-in-time recovery
- Geo-replicated storage
- Regular backup testing

#### 15.2 Recovery Procedures
- RTO: 4 hours
- RPO: 1 hour
- Automated failover
- Disaster recovery drills