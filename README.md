# Databricks Metadata Manager

A comprehensive web application for collaborative metadata management in Databricks, featuring comment suggestions, approval workflows, and audit logging.

## 🚀 Features

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

## 🛠️ Installation

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd metadata-manager
```

2. Create environment file:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your Databricks credentials
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

# Databricks
DATABRICKS_HOST=https://your-workspace.databricks.com
DATABRICKS_TOKEN=your-databricks-token

# Application
DEBUG=True
CORS_ORIGINS=http://localhost:5173
```

### Databricks Schema Setup

Initialize the metadata tracking schema in Databricks:

```bash
cd databricks
python initialize_databricks_schema.py
```

Or run the SQL script directly:
```sql
-- Run databricks/setup_metadata_schema.sql in your Databricks SQL workspace
```

## 👥 User Roles

### Test Users (Development)

The application includes a development user switcher and pre-configured test users:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| john_suggest | password123 | Suggest Only | Browse catalog, suggest comments |
| jane_approver | password123 | Approver | Suggest + approve/reject comments |
| admin_user | admin123 | Admin | Full system access |
| alice_suggest | password123 | Suggest Only | Browse catalog, suggest comments |
| bob_approver | password123 | Approver | Suggest + approve/reject comments |

### Creating Test Users

Via API endpoint (development mode):
```bash
curl -X POST http://localhost:8080/api/v1/auth/dev/create-test-users
```

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
│   │   └── store/          # Redux store
│   └── package.json
├── databricks/             # Databricks setup scripts
├── product/                # Product documentation
│   ├── PRD.md             # Product Requirements
│   └── TDD.md             # Technical Design
└── docker-compose.yml      # Docker orchestration
```

## 📊 Databricks Integration

The application integrates with Databricks to:
- Discover catalog entities (schemas, tables, columns)
- Read existing comments
- Apply approved comment changes
- Track all changes in `metadata_manager` schema

### Required Permissions

Your Databricks service principal needs:
- SELECT on target catalogs/schemas
- MODIFY permissions to update comments
- CREATE SCHEMA permission for metadata tracking

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

## 🧪 Development

### Running Tests

Backend tests:
```bash
cd backend
pytest
```

Frontend tests:
```bash
cd front-end
npm test
```

### Database Migrations

Create new migration:
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Building for Production

Backend:
```bash
docker build -t metadata-manager-backend ./backend
```

Frontend:
```bash
cd front-end
npm run build
```

## 📈 Monitoring

The application tracks:
- User activity and comment statistics
- Approval turnaround times
- Metadata coverage percentages
- System performance metrics

View metrics in Databricks:
```sql
SELECT * FROM anand_rao.metadata_manager.v_user_activity;
SELECT * FROM anand_rao.metadata_manager.v_coverage_report;
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
- Check the [documentation](./product/)
- Review existing issues
- Create a new issue with details

## 🚦 Status

- ✅ Core functionality complete
- ✅ User authentication and roles
- ✅ Catalog browsing
- ✅ Comment management
- ✅ Approval workflow
- ✅ Databricks integration
- ✅ Development tools
- 🔄 Production deployment guides (in progress)

---

Built with ❤️ for better Databricks metadata management