# MicroCore SaaS

Production-ready micro-SaaS with authentication, billing, dashboard, and admin panel.

## Features

- **Authentication**: JWT + OAuth (Google, GitHub skeleton)
- **Billing**: Stripe subscriptions with multiple plans
- **Dashboard**: Real-time analytics and charts
- **Admin Panel**: User management and system analytics
- **Infrastructure**: Terraform + AWS + CI/CD
- **Monitoring**: Prometheus + Grafana + Sentry

## Tech Stack

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL + Alembic
- Redis (caching, sessions)
- Stripe (billing)
- Celery (background jobs)

### Frontend
- React 18+ + TypeScript
- Vite (build tool)
- TailwindCSS (styling)
- Chart.js/Recharts (charts)
- React Query (state management)

### Infrastructure
- AWS (ECS, RDS, S3, CloudFront)
- Terraform (IaC)
- GitHub Actions (CI/CD)
- Docker (containers)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- AWS CLI (for deployment)

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository>
   cd microcore-saas
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Setup backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

4. **Setup frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access applications**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
microcore-saas/
├── backend/          # FastAPI application
├── frontend/         # React Vite application
├── infra/           # Terraform infrastructure
├── docs/            # Documentation
├── scripts/         # Development scripts
├── tests/           # E2E tests
└── .github/         # GitHub Actions
```

## Development

### Backend Development
```bash
cd backend
# Run tests
pytest
# Code formatting
black app/
ruff check app/
# Type checking
mypy app/
```

### Frontend Development
```bash
cd frontend
# Run tests
npm test
# Type checking
npm run type-check
# Linting
npm run lint
```

## Deployment

See [DEPLOYMENT.md](docs/deployment/README.md) for detailed deployment instructions.

## Architecture

See [ARCHITECTURE.md](docs/architecture/README.md) for system architecture and design decisions.

## Contributing

1. Create feature branch: `git checkout -b feat/your-feature`
2. Make changes and add tests
3. Ensure all checks pass
4. Submit pull request

## License

MIT License - see LICENSE file for details.