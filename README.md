# Autonomous AI Software Factory

An AI-powered software factory platform that autonomously generates PRD, architecture, code, tests, and deployments from user requirements.

## Features

- **Requirements Analysis**: AI analyzes requirements and generates detailed PRD with architecture
- **Autonomous Development**: Claude Code autonomously writes production-ready code
- **Automated Testing**: Comprehensive test suites generated and executed with intelligent retries
- **Auto Deployment**: Projects deployed to preview environments with one-click production release
- **Real-time Monitoring**: WebSocket-based live updates for project progress
- **Permission Gatekeeper**: Safety controls for dangerous operations

## Tech Stack

### Frontend
- Next.js 14 with App Router
- TypeScript (strict mode)
- Tailwind CSS 4
- React Query for state management
- Socket.IO for real-time updates

### Backend
- FastAPI (Python 3.11)
- PostgreSQL 16
- Redis 7
- SQLAlchemy (async)
- ARQ task queue for background jobs

### Infrastructure
- Docker Compose for local development
- Alembic for database migrations
- Claude Code for autonomous development

## Project Structure

```
autonomous-ai-factory/
├── frontend/              # Next.js frontend application
│   ├── app/               # App router pages
│   │   ├── page.tsx       # Landing page
│   │   ├── projects/      # Project pages
│   │   │   ├── page.tsx   # Project list
│   │   │   ├── new/       # Create project form
│   │   │   └── [id]/      # Project detail pages
│   ├── components/        # Reusable React components
│   ├── lib/               # Utilities (API client, WebSocket)
│   └── Dockerfile
├── backend/               # FastAPI backend application
│   ├── api/               # API route handlers
│   ├── core/              # Orchestrator, planner, executor, tester, gatekeeper
│   ├── models/            # SQLAlchemy ORM models
│   ├── workers/           # ARQ async workers
│   ├── db/                # Database migrations (Alembic)
│   ├── tests/             # Pytest test suite
│   └── Dockerfile
├── workspace/             # Generated project workspaces
├── docker-compose.yml     # Docker Compose configuration
└── .env.example           # Environment variables template
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 20+ (for local frontend development)
- Anthropic API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd autonomous-ai-factory
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. **Start with Docker Compose**
   ```bash
   docker compose up -d
   ```

   Services will be available at:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Running Tests

#### Backend Tests

```bash
cd backend
pytest
```

Test coverage includes:
- Model creation and relationships
- API endpoint functionality
- Gatekeeper permission logic

#### Frontend Tests

```bash
cd frontend
npm test
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/projects` - Create a new project
- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{id}` - Get project details
- `POST /api/v1/projects/{id}/start` - Start project pipeline
- `GET /api/v1/projects/{id}/agent-runs` - Get agent execution logs
- `GET /api/v1/projects/{id}/test-runs` - Get test results
- `GET /api/v1/projects/{id}/delivery-report` - Get delivery report
- `WS /ws/{project_id}` - WebSocket for real-time updates

## Usage

1. **Create a Project**
   - Navigate to http://localhost:3000
   - Click "Create Project"
   - Fill in requirements, goals, and preferences
   - Submit to start autonomous development

2. **Monitor Progress**
   - View real-time pipeline progress
   - Check task status and agent logs
   - Review test results as they complete

3. **Deploy**
   - Once delivered, view the delivery report
   - Access preview deployment
   - Review code in generated repository

## Configuration

### Permission Policies

Control what the AI can do through permission policies:

- `allow_auto_deploy`: Allow automatic deployment to preview environments
- `allow_production_release`: Allow production releases (requires manual approval)
- `allow_delete_operation`: Allow destructive delete operations
- `max_cost`: Maximum budget for API costs (USD)
- `max_retry_count`: Maximum retries for failed tasks

### Gatekeeper

The gatekeeper enforces safety policies:

- Always blocks dangerous operations (e.g., `delete_production_data`)
- Always allows safe operations (e.g., `create_branch`, `run_tests`)
- Enforces cost limits and retry limits
- Requires explicit permission for deployments and external API calls

## Architecture

### Pipeline Stages

1. **Created** - Project initialized
2. **Requirement Analyzing** - AI analyzes and structures requirements
3. **Planning** - Generate task breakdown and architecture
4. **Developing** - Autonomous code generation
5. **Testing** - Automated test execution
6. **Reviewing** - Code quality review
7. **Deploying** - Deployment to preview environment
8. **Delivered** - Project complete with delivery report

### Components

- **Orchestrator**: Coordinates the entire pipeline
- **Planner**: Breaks down requirements into tasks
- **Executor**: Executes development tasks via Claude Code
- **Tester**: Runs automated tests
- **Gatekeeper**: Enforces permission policies
- **WebSocket Manager**: Real-time progress updates

## Troubleshooting

### Database connection issues

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres
```

### Backend not starting

```bash
# Check backend logs
docker compose logs backend

# Ensure database is ready
docker compose up postgres -d
```

### Frontend build errors

```bash
# Clear Next.js cache
cd frontend
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest` and `npm test`
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: See inline code documentation and API docs
