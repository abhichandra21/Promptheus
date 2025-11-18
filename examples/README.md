# Promptheus Multi-User Platform - Implementation Examples

This directory contains complete implementation examples for transforming Promptheus into a multi-user platform with team collaboration features.

## Contents

### 📋 Documentation
- **`multiuser-auth-plan.md`** - Comprehensive authentication strategy and implementation plan
- **`UI-MOCKUPS.md`** - Detailed UI/UX mockups with ASCII art and descriptions

### 💻 Code Examples
- **`fastapi-backend-auth.py`** - Complete FastAPI backend with JWT authentication
- **`react-frontend-auth.tsx`** - React frontend with authentication and prompt interface

### 🐳 Infrastructure
- **`docker-compose.yml`** - Complete local development environment setup
- **`init-db.sql`** - Database initialization script (create this from schema in plan)
- **`backend/Dockerfile`** - Backend container configuration
- **`frontend/Dockerfile.dev`** - Frontend development container
- **`nginx/nginx.conf`** - Reverse proxy configuration

---

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)

### 1. Clone and Setup

```bash
# Navigate to examples directory
cd examples/

# Create environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Start with dev tools (pgAdmin, Redis Commander)
docker-compose --profile dev-tools up -d

# View logs
docker-compose logs -f backend

# Check service health
docker-compose ps
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (with dev-tools profile)
- **Redis Commander**: http://localhost:8081 (with dev-tools profile)

### 4. Demo Login

```
Email: demo@promptheus.dev
Password: DemoPassword123!
```

---

## Development Workflow

### Backend Development

```bash
# Run backend locally (without Docker)
cd backend/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://promptheus:dev_password_change_in_prod@localhost:5432/promptheus"
export REDIS_URL="redis://:dev_redis_password@localhost:6379/0"
export SECRET_KEY="dev_secret_key_CHANGE_IN_PRODUCTION"

# Run migrations (Alembic)
alembic upgrade head

# Start server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
# Run frontend locally (without Docker)
cd frontend/
npm install

# Set environment variables
export REACT_APP_API_URL="http://localhost:8000"

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Database Management

```bash
# Access PostgreSQL CLI
docker-compose exec postgres psql -U promptheus -d promptheus

# Run SQL commands
\dt  # List tables
\d users  # Describe users table

# Create database migration
cd backend/
alembic revision --autogenerate -m "Add new field to users"
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing

```bash
# Backend tests
cd backend/
pytest

# Frontend tests
cd frontend/
npm test

# E2E tests
npm run test:e2e
```

---

## Project Structure

```
examples/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── team.py
│   │   │   ├── prompt.py
│   │   │   └── api_key.py
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   └── prompt.py
│   │   ├── api/                    # API routes
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── prompts.py
│   │   │   └── teams.py
│   │   ├── core/                   # Core functionality
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── services/               # Business logic
│   │   │   ├── prompt_service.py   # Port from promptheus/
│   │   │   ├── provider_service.py
│   │   │   └── auth_service.py
│   │   └── db/
│   │       ├── database.py
│   │       └── session.py
│   ├── alembic/                    # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── prompt/
│   │   │   │   ├── PromptInput.tsx
│   │   │   │   ├── QuestionForm.tsx
│   │   │   │   └── RefinedOutput.tsx
│   │   │   └── layout/
│   │   │       ├── Header.tsx
│   │   │       └── Sidebar.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   └── History.tsx
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── usePrompts.ts
│   │   ├── types/
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   └── Dockerfile.dev
│
├── nginx/
│   ├── nginx.conf
│   └── ssl/
│
├── docker-compose.yml
├── .env.example
├── init-db.sql
└── README.md (this file)
```

---

## Environment Variables

Create a `.env` file in the `examples/` directory:

```bash
# Database
DATABASE_URL=postgresql://promptheus:dev_password_change_in_prod@postgres:5432/promptheus

# Redis
REDIS_URL=redis://:dev_redis_password@redis:6379/0

# JWT
SECRET_KEY=your-super-secret-key-minimum-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# LLM Providers (from existing Promptheus)
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
DASHSCOPE_API_KEY=your_qwen_key
ZAI_API_KEY=your_glm_key

# Email (optional for development)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=noreply@promptheus.dev

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# Environment
ENVIRONMENT=development
DEBUG=true
```

---

## API Endpoints

### Authentication
```
POST   /api/v1/auth/register        Register new user
POST   /api/v1/auth/login           Login
POST   /api/v1/auth/refresh         Refresh token
POST   /api/v1/auth/logout          Logout
GET    /api/v1/auth/me              Get current user
```

### Prompts
```
POST   /api/v1/prompts/analyze      Analyze prompt
POST   /api/v1/prompts/refine       Refine prompt
POST   /api/v1/prompts/tweak        Tweak prompt
GET    /api/v1/prompts/history      Get history
DELETE /api/v1/prompts/{id}         Delete prompt
```

### API Keys
```
GET    /api/v1/api-keys             List API keys
POST   /api/v1/api-keys             Create API key
DELETE /api/v1/api-keys/{id}        Revoke API key
```

Full API documentation: http://localhost:8000/docs

---

## CLI Integration

### Update Existing CLI

To integrate authentication with the existing Promptheus CLI:

```bash
# Add new dependency to pyproject.toml
[tool.poetry.dependencies]
httpx = ">=0.24.0"  # For API calls

# Add auth commands to src/promptheus/commands/auth.py
promptheus login              # Browser-based OAuth2
promptheus login --api-key    # API key input
promptheus logout             # Clear credentials
promptheus whoami             # Show current user
```

### CLI Usage Examples

```bash
# Login
$ promptheus login
Opening browser for authentication...
✓ Authenticated as john@example.com

# Use authenticated API
$ promptheus "Generate a blog post"
# Now uses backend API instead of local LLM

# Check status
$ promptheus whoami
Authenticated as: john@example.com
Team: Acme Inc
Usage: 1,247 / 10,000 prompts this month

# API key for CI/CD
$ export PROMPTHEUS_API_KEY=sk-live-xxxxx
$ promptheus "Generate prompt" --skip-questions
```

---

## Migration from Single-User CLI

### Phase 1: Maintain Backward Compatibility

```python
# src/promptheus/main.py

def process_prompt(prompt: str, config: Config):
    # Check if user is authenticated
    if is_authenticated():
        # Use backend API
        return api_client.refine_prompt(prompt)
    else:
        # Fall back to local LLM (existing behavior)
        provider = get_provider(config.provider)
        return local_refinement(prompt, provider)
```

### Phase 2: Gradual Migration

1. **Week 1-2**: Deploy backend API
2. **Week 3**: Add `--use-api` flag to CLI
3. **Week 4**: Make API default, add `--local` flag
4. **Week 5**: Deprecate local mode (warning)
5. **Week 6**: Remove local mode (breaking change)

---

## Deployment

### EC2 Deployment

```bash
# 1. Launch EC2 instance (Ubuntu 22.04, t3.medium)
# 2. Install Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# 3. Clone repository
git clone https://github.com/yourusername/Promptheus.git
cd Promptheus/examples/

# 4. Configure environment
cp .env.example .env
nano .env  # Add production secrets

# 5. Start services
docker-compose --profile production up -d

# 6. Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d promptheus.yourdomain.com
```

### AWS RDS + ElastiCache

```bash
# 1. Create RDS PostgreSQL instance
# 2. Create ElastiCache Redis cluster
# 3. Update .env with production endpoints

DATABASE_URL=postgresql://user:pass@promptheus.xxx.rds.amazonaws.com:5432/promptheus
REDIS_URL=redis://:pass@promptheus.xxx.cache.amazonaws.com:6379/0
```

---

## Monitoring and Logging

### Structured Logging

```python
# Backend uses Python logging
import logging

logger = logging.getLogger(__name__)
logger.info("User logged in", extra={"user_id": user.id, "email": user.email})
```

### Metrics

- Request count by endpoint
- Response times (p50, p95, p99)
- Error rates
- Active users
- API key usage

### Tools (Phase 2)

- Prometheus + Grafana
- Sentry for error tracking
- DataDog for APM
- CloudWatch for AWS metrics

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS (SSL certificate)
- [ ] Configure CORS properly
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Enable SQL injection protection (ORM)
- [ ] Secure API keys (never log)
- [ ] Implement CSRF protection
- [ ] Add security headers
- [ ] Regular dependency updates
- [ ] Backup database regularly

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U promptheus -d promptheus

# Reset database
docker-compose down -v
docker-compose up -d
```

### Backend Not Starting

```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - Missing environment variables
# - Database not ready
# - Port already in use
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend

# Clear node_modules
docker-compose exec frontend rm -rf node_modules
docker-compose exec frontend npm install
```

---

## Next Steps

1. **Review the plan**: Read `multiuser-auth-plan.md`
2. **Explore UI mockups**: See `UI-MOCKUPS.md`
3. **Run the examples**: `docker-compose up -d`
4. **Integrate with CLI**: Update `src/promptheus/` to call API
5. **Deploy to staging**: Test on EC2
6. **Collect feedback**: Beta test with team
7. **Production deploy**: Full rollout
8. **OKTA integration**: Enterprise features

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/abhichandra21/Promptheus/issues
- Documentation: See `/docs` directory
- Email: support@promptheus.dev (if configured)

---

## License

MIT License - Same as main Promptheus project
