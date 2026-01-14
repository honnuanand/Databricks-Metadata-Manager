# Databricks Metadata Manager

A comprehensive web application for collaborative metadata management in Databricks, featuring comment suggestions, approval workflows, and audit logging.

**Repository**: https://github.com/honnuanand/Databricks-Metadata-Manager

**Status**: ✅ All 21/21 tests passing

---

## 🚀 Deploying to Databricks Apps

> **Deploy** = Production deployment to Databricks Apps with Lakebase OAuth

### Quick Deploy (Existing Workspace)

```bash
python deploy_to_databricks.py --skip-secrets
```

### New Workspace Setup

```bash
# 1. Configure CLI profile
databricks auth login --host https://WORKSPACE.cloud.databricks.com --profile PROFILE_NAME

# 2. Edit app.yaml with your workspace settings

# 3. Create secrets
databricks secrets create-scope --scope metadata-manager-secrets --profile PROFILE_NAME
databricks secrets put-secret --scope metadata-manager-secrets --key secret-key --profile PROFILE_NAME
databricks secrets put-secret --scope metadata-manager-secrets --key databricks-token --profile PROFILE_NAME

# 4. Setup Lakebase schema (creates schema, tables, default users)
python scripts/setup_lakebase_schema.py --profile PROFILE_NAME --schema metadata_manager

# 5. Deploy app
python deploy_to_databricks.py --skip-secrets

# 6. Grant SP access to Lakebase
python scripts/grant_lakebase_sp_access.py --profile PROFILE_NAME --schema metadata_manager

# 7. Redeploy to apply permissions
python deploy_to_databricks.py --skip-secrets
```

### Configuration (`app.yaml`)

| Variable | Example | Description |
|----------|---------|-------------|
| `deployment.app_name` | `metadata-mgr` | App name in Databricks |
| `deployment.profile` | `fe-vm-leaps-fe` | Databricks CLI profile |
| `LAKEBASE_INSTANCE` | `arao-lb` | Lakebase instance name |
| `LAKEBASE_HOST` | `instance-xxx.database...` | Lakebase hostname |
| `LAKEBASE_SCHEMA` | `metadata_manager` | PostgreSQL schema |
| `DATABRICKS_HOST` | `https://workspace...` | Workspace URL |
| `DATABRICKS_CATALOG` | `arao` | Unity Catalog for browsing |

📖 **Full deployment guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✨ Features

### Core Functionality
- **Catalog Discovery**: Browse Databricks catalogs, schemas, tables, and columns
- **Comment Management**: Suggest, edit, and manage metadata comments
- **Approval Workflow**: Review and approve/reject comment suggestions
- **User Roles**: Three distinct roles with different permissions
  - **Suggest Only**: Can browse and suggest comments
  - **Approver**: Can suggest and approve/reject comments
  - **Admin**: Full system access including user management
- **Audit Trail**: Complete logging of all actions
- **Development User Switcher**: Easy role switching for testing

### Technical Features
- **Modern Stack**: FastAPI backend + React/Vite/MUI frontend
- **Real-time Updates**: Responsive UI with Redux state management
- **Databricks Integration**: Native SDK integration for catalog operations
- **Docker Support**: Full containerization for easy deployment
- **Type Safety**: TypeScript frontend with Pydantic validation

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional)
- Databricks workspace with appropriate permissions
- PostgreSQL database (or use Docker)

## 🛠️ Local Development Setup

> **Install** = Setting up for local development and testing

### Unified Installer (For New Databricks Workspace)

The unified installer handles complete platform installation on a new Databricks workspace with a single command:

```bash
# Full interactive installation
python install.py

# Or with a configuration file
python install.py --config install_config.yaml
```

The installer will:
1. Run pre-flight checks (Databricks CLI, Node.js, Python dependencies)
2. Prompt for missing credentials (Databricks token, warehouse ID, database URL)
3. Create Databricks secret scope and store all secrets
4. Create Unity Catalog schemas and tables
5. Grant permissions to the service principal
6. Run PostgreSQL migrations and seed users
7. Build frontend and deploy to Databricks Apps
8. Generate verification report

#### Installer Options

```bash
# Generate a configuration template
python install.py --init-config

# Dry run - validate without making changes
python install.py --dry-run

# Run only specific steps
python install.py --only secrets,schemas,postgres

# Skip specific steps
python install.py --skip deploy

# Verbose output
python install.py --verbose

# Override specific settings via CLI
python install.py --catalog my-catalog --scope my-secrets
```

#### Configuration File

Create `install_config.yaml` from the template:

```yaml
databricks:
  host: "https://your-workspace.cloud.databricks.com"
  warehouse_id: "abc123def456"  # SQL Warehouse ID

catalog:
  name: "my_catalog"
  schemas:
    primary: "metadata_manager"
    test: "metadata_test"

secrets:
  scope_name: "my-app-secrets"

service_principal:
  name: "metadata-manager"

database:
  run_migrations: true
  seed_data: true

deployment:
  app_name: "metadata-manager"
```

See `install_config.yaml.example` for all available options.

---

### Quick Start with Docker (Local Development)

1. Clone the repository:
```bash
git clone https://github.com/honnuanand/Databricks-Metadata-Manager.git
cd metadata-manager
```

2. Set up environment variables:
```bash
# IMPORTANT: Never hardcode tokens in code files
export DATABRICKS_TOKEN="your-databricks-token"
export DATABRICKS_HOST="https://your-workspace.databricks.com"
export DATABASE_URL="postgresql://user:pass@host/db"
```

3. Start the application:
```bash
docker-compose up -d
```

The application will be available at:
- Frontend: http://localhost:4001
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs

### Manual Installation

#### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
alembic upgrade head
```

6. Run the backend:
```bash
uvicorn app.main:app --reload --port 8080
```

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd front-end
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

## 🔧 Configuration

### Backend Configuration (.env)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/metadata_manager
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Databricks (NEVER hardcode tokens in code!)
DATABRICKS_HOST=https://your-workspace.databricks.com
DATABRICKS_TOKEN=your-databricks-token  # Use environment variable

# Application
DEBUG=True
CORS_ORIGINS=http://localhost:4001
```

### Databricks Schema Setup

Initialize the metadata tracking schema in Databricks:

```bash
# Set environment variables first
export DATABRICKS_TOKEN="your-token"
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"

# Run the schema creation script
python databricks/create_schema_sql.py
```

This will create the `arao.metadata_manager` schema with:
- `users` table with test users
- `comment_suggestions` table for tracking comment changes
- `approvals` table for approval workflow
- `audit_logs` table for audit trail

## 👥 User Roles

### Test Users

The application includes pre-configured test users:

| Email | Password | Role | Permissions |
|-------|----------|------|-------------|
| admin@example.com | admin123 | admin | Full system access including user management |
| approver@example.com | approver123 | approver | Can suggest and approve/reject comments |
| user@example.com | user123 | suggest_only | Can browse catalog and suggest comments |

Test users are automatically created when the backend starts up if they don't exist.

## 📱 Using the Application

### 1. Login
Navigate to http://localhost:4001 and login with test credentials.

### 2. Browse Catalog
- Navigate to Catalog Explorer
- Click through catalogs → schemas → tables
- View column details and existing comments

### 3. Suggest Comments
- Click the edit/add icon next to any entity
- Enter your suggested comment
- Submit for approval (or save as draft)

### 4. Approval Workflow (Approvers only)
- Navigate to Approval Queue
- Review pending suggestions
- Approve or reject with feedback

### 5. Track Your Comments
- Go to My Comments page
- View drafts, pending, approved, and rejected comments
- Edit drafts or submit for approval

## 🏗️ Project Structure

```
metadata-manager/
├── install.py               # Unified installer (main entry point)
├── install_config.yaml.example  # Configuration template
├── installer/               # Installer package
│   ├── config.py           # Configuration management
│   ├── validators.py       # Input validation
│   ├── preflight.py        # Pre-flight checks
│   ├── secrets_manager.py  # Databricks secrets operations
│   ├── databricks_schema.py # Unity Catalog schema setup
│   ├── postgres_setup.py   # PostgreSQL/Alembic setup
│   ├── deployment.py       # App build and deployment
│   ├── verification.py     # Installation verification
│   └── templates/          # SQL templates (Jinja2)
│       ├── schema.sql.j2   # Parameterized schema DDL
│       └── grants.sql.j2   # Parameterized permissions
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   ├── db/             # Database setup
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── front-end/              # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # Redux store
│   │   └── testing/        # In-app test runner
│   ├── tests/              # Playwright E2E tests
│   └── package.json
├── databricks/             # Databricks schema setup scripts (legacy)
├── scripts/                # Setup and utility scripts
│   ├── setup_secrets.py    # Secret scope setup
│   ├── setup_database.py   # Database initialization
│   └── grant_permissions.py # Service principal permissions
├── docs/                   # Documentation
│   ├── AUTHENTICATION_GUIDE.md
│   ├── DEPLOYMENT.md
│   ├── LOGIN_GUIDE.md
│   └── NEON_SETUP.md
├── product/                # Product documentation
│   ├── PRD.md             # Product Requirements
│   └── TDD.md             # Technical Design
├── deploy_to_databricks.py # Deployment script (for updates)
└── docker-compose.yml      # Docker orchestration
```

## 📊 Databricks Integration

The application integrates with Databricks to:
- Discover catalog entities (schemas, tables, columns)
- Read existing comments
- Apply approved comment changes
- Track all changes in `metadata_manager` schema

### Required Permissions

The Databricks Apps service principal needs these Unity Catalog permissions:

| Permission | Target | Purpose |
|------------|--------|---------|
| `USE CATALOG` | Catalog (e.g., `arao`) | Access the catalog |
| `USE SCHEMA` | `metadata_manager` schema | Access app tables |
| `ALL PRIVILEGES` | `metadata_manager` schema | Read/write app data |
| `USE SCHEMA` | `metadata_test` schema | Access test data |
| `SELECT` | `metadata_test` schema | Read test tables |

**Note**: After deployment, run `python scripts/grant_permissions.py` to grant these permissions to the service principal. See [Post-Deployment: Service Principal Permissions](#post-deployment-service-principal-permissions) for details.

## 🔍 API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

Key endpoints:
- `/api/v1/auth/` - Authentication
- `/api/v1/catalogs/` - Catalog browsing
- `/api/v1/comments/` - Comment management
- `/api/v1/approvals/` - Approval workflow
- `/api/v1/users/` - User management

## 🧪 Testing

### In-App Test Runner

The application includes a comprehensive test runner accessible at `/test-runner`:
- 21/21 tests passing (12 authentication tests + 9 catalog tests)
- Real-time test execution with progress indicators
- Browser-based integration tests

```bash
# Access at: http://localhost:4001/test-runner
```

### Playwright E2E Tests

```bash
cd front-end
npm run test:playwright:catalog  # Run catalog exploration tests
```

**Note**: All tests are passing ✅

### Database Migrations

Create new migration:
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Post-Deployment: Service Principal Permissions

After deploying the app, you need to grant Unity Catalog permissions to the service principal that runs the app. The service principal name is automatically assigned by Databricks and can be discovered by:

1. **Check App Logs**: Go to Databricks Apps > metadata-manager > Logs
2. **Query Current User**: Access `https://your-app-url/api/v1/debug/current-user` in the browser

Once you have the service principal name, grant permissions using the helper script:

```bash
# Interactive mode - prompts for service principal name
python scripts/grant_permissions.py

# Specify service principal directly
python scripts/grant_permissions.py --principal "metadata-manager"

# Use custom catalog
python scripts/grant_permissions.py --principal "app-xyz metadata-manager" --catalog my_catalog

# Dry run - show grants without executing
python scripts/grant_permissions.py --principal "metadata-manager" --dry-run
```

The script grants these permissions:
- `USE CATALOG` on the catalog
- `USE SCHEMA` on `metadata_manager` and `metadata_test` schemas
- `ALL PRIVILEGES` on `metadata_manager` schema (for read/write)
- `SELECT` on `metadata_test` schema (read-only for sample data)

#### Required Secrets

The application requires these secrets in the Databricks secret scope:

| Secret Key | Description |
|------------|-------------|
| `databricks-token` | Databricks PAT token for API access |
| `databricks-host` | Workspace URL (e.g., https://workspace.cloud.databricks.com) |
| `secret-key` | JWT signing key for authentication |
| `lakebase-password` | Password for Lakebase PostgreSQL user |
| `lakebase-host` | Lakebase instance hostname |
| `lakebase-user` | Lakebase database user |
| `lakebase-database` | Lakebase database name |

### Lakebase Setup (Databricks PostgreSQL)

The application uses **Databricks Lakebase** (PostgreSQL-compatible database) for user authentication storage. Here's how to set it up:

#### 1. Create a Lakebase Instance

In Databricks workspace:
1. Go to **Data** > **Create** > **PostgreSQL Database**
2. Note the instance hostname (e.g., `instance-xxxx.database.cloud.databricks.com`)

#### 2. Create the Application User

Connect to Lakebase using the admin credentials and run:

```sql
-- Create the application user with a secure password
CREATE USER metadata_manager_app WITH PASSWORD 'YourSecurePassword123!';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE databricks_postgres TO metadata_manager_app;
GRANT ALL PRIVILEGES ON SCHEMA public TO metadata_manager_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO metadata_manager_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO metadata_manager_app;
```

#### 3. Store Credentials in Databricks Secrets

```bash
# Create secret scope (if not exists)
databricks secrets create-scope metadata-manager-secrets

# Store Lakebase credentials
databricks secrets put-secret metadata-manager-secrets lakebase-password
# Enter your password when prompted (e.g., YourSecurePassword123!)

databricks secrets put-secret metadata-manager-secrets lakebase-host --string-value "instance-xxxx.database.cloud.databricks.com"
databricks secrets put-secret metadata-manager-secrets lakebase-user --string-value "metadata_manager_app"
databricks secrets put-secret metadata-manager-secrets lakebase-database --string-value "databricks_postgres"

# Store other required secrets
databricks secrets put-secret metadata-manager-secrets databricks-token --string-value "dapi..."
databricks secrets put-secret metadata-manager-secrets databricks-host --string-value "https://your-workspace.cloud.databricks.com"
databricks secrets put-secret metadata-manager-secrets secret-key --string-value "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

#### 4. Verify Secrets

```bash
databricks secrets list-secrets metadata-manager-secrets
```

Expected output:
```
Key                Last Updated Timestamp
databricks-host    ...
databricks-token   ...
lakebase-database  ...
lakebase-host      ...
lakebase-password  ...
lakebase-user      ...
secret-key         ...
```

#### 5. Deploy the Application

The deploy script automatically retrieves Lakebase credentials from secrets and constructs the DATABASE_URL:

```bash
python deploy_to_databricks.py --skip-secrets
```

#### Connection String Format

The application constructs the DATABASE_URL as:
```
postgresql://<lakebase-user>:<lakebase-password>@<lakebase-host>:5432/<lakebase-database>?sslmode=require
```

Example:
```
postgresql://metadata_manager_app:YourSecurePassword123!@instance-xxxx.database.cloud.databricks.com:5432/databricks_postgres?sslmode=require
```

### OAuth Token Authentication (Passwordless - Recommended)

For production deployments, use **OAuth token authentication** instead of static passwords. This provides better security through short-lived tokens that auto-refresh.

#### Benefits of OAuth

- No long-lived passwords to manage or rotate
- Tokens auto-expire after 1 hour
- Better audit trail (service principal identity in logs)
- Follows Databricks security best practices

#### How OAuth Works

1. **Service Principal Credentials**: When running in Databricks Apps, the app automatically has access to OAuth credentials via `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` environment variables.

2. **Token Generation**: The app calls `WorkspaceClient().database.generate_database_credential()` to get a short-lived OAuth token (valid for 1 hour).

3. **Auto-Refresh**: The `LakebaseOAuthManager` class automatically refreshes tokens 5 minutes before expiry.

4. **Connection**: The app connects to Lakebase using:
   - **Username**: Service principal's `client_id`
   - **Password**: OAuth token

#### Setup OAuth for Service Principal

**Step 1: Get Service Principal Info**

After deploying the app, find the service principal details:

```bash
# Check app info
databricks apps get metadata-manager

# Or query from the running app
curl https://your-app-url/health
```

The health endpoint will show `oauth_username` (the SP's client_id).

**Step 2: Create Postgres Role in Lakebase**

Connect to Lakebase as admin and run the setup script:

```bash
# Using psql
psql "postgresql://admin:password@instance-xxx.database.cloud.databricks.com:5432/databricks_postgres?sslmode=require" \
  -f scripts/setup_lakebase_sp_oauth.sql
```

Or run these SQL commands manually:

```sql
-- Replace with your actual service principal client_id
-- Example: 10922e0f-2688-4911-9fe0-4f35af5a563f

-- 1. Create the databricks_auth extension
CREATE EXTENSION IF NOT EXISTS databricks_auth;

-- 2. Create Postgres role for the Service Principal
SELECT databricks_create_role('YOUR_SP_CLIENT_ID', 'SERVICE_PRINCIPAL');

-- 3. Grant permissions
GRANT CONNECT ON DATABASE databricks_postgres TO "YOUR_SP_CLIENT_ID";
GRANT USAGE ON SCHEMA public TO "YOUR_SP_CLIENT_ID";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "YOUR_SP_CLIENT_ID";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "YOUR_SP_CLIENT_ID";

-- 4. Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO "YOUR_SP_CLIENT_ID";
```

**Step 3: Deploy with OAuth**

The app automatically detects OAuth credentials when running in Databricks Apps. Deploy normally:

```bash
python deploy_to_databricks.py --hard-redeploy --skip-secrets
```

**Step 4: Verify OAuth is Working**

Check the health endpoint:

```bash
curl https://your-app-url/health
```

You should see:
```json
{
  "using_oauth": true,
  "oauth_token_expires_in": 3500,
  "oauth_username": "10922e0f-2688-4911-9fe0-4f35af5a563f"
}
```

#### OAuth vs Password Authentication

| Feature | OAuth | Password |
|---------|-------|----------|
| Token Lifetime | 1 hour (auto-refresh) | Never expires |
| Secret Management | No secrets to store | Password in Databricks Secrets |
| Audit Trail | SP identity logged | User account logged |
| Setup Complexity | Requires Lakebase role | Simpler initial setup |
| Recommended For | Production | Development/Testing |

#### Fallback to Password

If OAuth credentials are not available (e.g., running locally), the app automatically falls back to static password authentication using `DATABASE_URL` or the Lakebase secrets.

### Alternative: Legacy Neon PostgreSQL

For backward compatibility, the app also supports Neon PostgreSQL via the `database-url` secret:

```bash
databricks secrets put-secret metadata-manager-secrets database-url --string-value "postgresql://user:pass@host.neon.tech/db"
```

## 📈 Monitoring

The application tracks:
- User activity and comment statistics
- Approval turnaround times
- Metadata coverage percentages
- System performance metrics

View metrics in Databricks:
```sql
SELECT * FROM arao.metadata_manager.v_user_activity;
SELECT * FROM arao.metadata_manager.comment_suggestions;
SELECT * FROM arao.metadata_manager.audit_logs;
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
- Check the [documentation](./docs/)
- Review [product documentation](./product/)
- Create an issue on [GitHub](https://github.com/honnuanand/Databricks-Metadata-Manager/issues)

## 🚦 Status

- ✅ Core functionality complete
- ✅ User authentication and roles (Databricks Lakebase PostgreSQL)
- ✅ Catalog browsing with Databricks Unity Catalog
- ✅ Comment management
- ✅ Approval workflow
- ✅ Databricks Apps deployment with OAuth
- ✅ **Lakebase OAuth Token Authentication** (passwordless, auto-refresh)
- ✅ Comprehensive test suite (21/21 passing)
- ✅ In-app test runner
- ✅ Security hardening (secrets in Databricks Secrets)

---

Built with ❤️ for better Databricks metadata management