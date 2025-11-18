# Promptheus Multi-User Authentication Plan

## Executive Summary

This document outlines authentication strategies for transforming Promptheus from a single-user CLI tool into a multi-user team platform with eventual public deployment.

## Current State Analysis

### Existing Features
1. **Prompt Refinement Engine** - AI-powered prompt optimization
2. **Multi-Provider LLM Support** - 6 providers (Gemini, Claude, OpenAI, Groq, Qwen, GLM)
3. **Interactive REPL** - Session-based command interface
4. **History Management** - Local file-based prompt storage
5. **CLI & Pipeline Integration** - Flexible input/output modes

### User Interaction Flows
1. **Single Prompt Flow**: Input → Analysis → Questions → Refinement → Output
2. **Interactive Session**: Launch REPL → Multiple prompts → Session state persistence
3. **History Access**: View history → Load previous prompts → Reuse/modify
4. **Tweaking**: Initial refinement → Iterative modifications → Final acceptance

## Top 3 Authentication Strategies

### Option 1: JWT-Based Authentication with Refresh Tokens ⭐ RECOMMENDED

**Why This is Best:**
- **Industry Standard**: Widely adopted, battle-tested approach
- **Stateless**: Scales horizontally without session storage
- **Flexible**: Works for web, mobile, CLI, and API integrations
- **OKTA Compatible**: Easy migration path to OKTA later
- **Performance**: Fast validation without database lookups

**Architecture:**
```
┌─────────┐         ┌──────────┐         ┌─────────┐
│ Client  │────────▶│ FastAPI  │────────▶│Database │
│ (React/ │  JWT    │ Backend  │  Query  │(Postgres│
│  CLI)   │◀────────│          │◀────────│  /Mongo)│
└─────────┘  Token  └──────────┘  User   └─────────┘
```

**Implementation Details:**
- **Access Tokens**: Short-lived (15-60 min), contains user claims
- **Refresh Tokens**: Long-lived (7-30 days), stored securely
- **Token Rotation**: Automatic refresh on expiry
- **CLI Support**: Store tokens in `~/.promptheus/auth.json`
- **Web Support**: HttpOnly cookies + localStorage for React

**Security Features:**
- HTTPS-only transmission
- Token rotation on refresh
- Revocation list for compromised tokens
- Rate limiting on auth endpoints
- CORS configuration for web clients

**Migration Path to OKTA:**
```
Phase 1: Custom JWT → Phase 2: OKTA + JWT → Phase 3: Full OKTA SSO
```

---

### Option 2: API Key + Session-Based Hybrid

**Why Consider This:**
- **Simple CLI Integration**: API keys perfect for CLI tools
- **Fine-Grained Access**: Key-based rate limiting and permissions
- **Service Accounts**: Easy team/bot account management
- **Hybrid Flexibility**: Sessions for web, keys for CLI/API

**Architecture:**
```
┌──────────┐  API Key  ┌──────────┐  Session  ┌─────────┐
│CLI Client│──────────▶│          │◀──────────│Web React│
└──────────┘           │ FastAPI  │           └─────────┘
                       │ Backend  │
┌──────────┐  Session  │          │  DB Query ┌─────────┐
│Mobile App│──────────▶│          │──────────▶│Database │
└──────────┘           └──────────┘           └─────────┘
```

**Implementation Details:**
- **API Keys**: For CLI/service accounts (`sk-live-xxx`, `sk-test-xxx`)
- **Sessions**: For web UI (Redis-backed, 24hr expiry)
- **Role-Based Keys**: User keys vs Admin keys vs Read-only keys
- **Key Rotation**: Automatic expiry warnings and rotation workflow

**Security Features:**
- Encrypted key storage
- IP whitelisting for sensitive keys
- Usage analytics per key
- Automatic key rotation
- Audit logs for all key operations

**Drawbacks:**
- More complex to maintain two auth systems
- Key management overhead for users
- Not as modern as pure token-based systems

---

### Option 3: OAuth2 with Social Providers + Email

**Why Consider This:**
- **Zero Onboarding Friction**: "Sign in with Google/GitHub"
- **Enterprise Ready**: OKTA integrates via OAuth2/SAML
- **No Password Management**: Delegate to trusted providers
- **Modern UX**: Expected by users in 2025

**Architecture:**
```
┌─────────┐           ┌──────────┐           ┌──────────┐
│  React  │──────────▶│ FastAPI  │◀──────────│Google/GH │
│   Web   │  Callback │ OAuth2   │  Verify   │  OAuth   │
└─────────┘           └──────────┘           └──────────┘
                           │
                           ▼
                      ┌─────────┐
                      │Database │
                      │ Users   │
                      └─────────┘
```

**Supported Providers:**
- Google OAuth2
- GitHub OAuth2
- Microsoft Azure AD (enterprise)
- Email/Password (fallback)
- OKTA (future)

**Implementation Details:**
- **Authorization Code Flow**: Secure web authentication
- **PKCE**: For mobile/SPA security
- **Scopes**: Minimal permissions (email, profile)
- **Account Linking**: Link multiple OAuth providers to one account

**CLI Authentication:**
```bash
# Device flow for CLI
promptheus login
> Opening browser for authentication...
> Waiting for approval...
> ✓ Authenticated as user@example.com
```

**Drawbacks:**
- Requires browser for CLI auth
- Dependency on external providers
- More complex initial setup

---

## Recommended Approach: Option 1 (JWT) + OAuth2 Integration

### Why This Combination?

**Phase 1 (MVP - Local/Team):**
- Start with JWT + email/password
- Simple registration flow
- Team-based access control
- Local deployment on EC2

**Phase 2 (Growth - Public Beta):**
- Add OAuth2 social providers
- Improve onboarding UX
- Enhanced rate limiting
- Multi-region deployment

**Phase 3 (Enterprise - OKTA):**
- Integrate OKTA SSO
- Enterprise team management
- Audit logging
- Compliance features

### Technical Stack

**Backend:**
- FastAPI (Python) - Async, high-performance
- PostgreSQL - User data, history, sessions
- Redis - Token blacklist, rate limiting
- Alembic - Database migrations

**Frontend:**
- React 18+ with TypeScript
- TanStack Query (React Query) - API state management
- Zustand - Local state management
- Tailwind CSS - Styling
- shadcn/ui - Component library

**Infrastructure:**
- Docker + Docker Compose - Local development
- AWS EC2 - Initial deployment
- AWS RDS - Managed PostgreSQL
- AWS ElastiCache - Managed Redis
- Nginx - Reverse proxy
- Let's Encrypt - SSL certificates

**Authentication Libraries:**
- **Backend**: python-jose[cryptography], passlib, python-multipart
- **Frontend**: axios, js-cookie, react-router-dom

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    oauth_provider VARCHAR(50), -- 'google', 'github', 'okta', NULL for email
    oauth_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    UNIQUE(oauth_provider, oauth_id)
);

-- Teams/Organizations table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free', -- 'free', 'team', 'enterprise'
    max_members INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team members
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member', -- 'owner', 'admin', 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, user_id)
);

-- Refresh tokens
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT false,
    device_info JSONB
);

-- Prompt history (migrated from local files)
CREATE TABLE prompt_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    original_prompt TEXT NOT NULL,
    refined_prompt TEXT NOT NULL,
    task_type VARCHAR(50),
    provider VARCHAR(50),
    model VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_shared BOOLEAN DEFAULT false
);

-- API keys (for CLI/service accounts)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_prefix VARCHAR(20) NOT NULL, -- 'sk-live-', 'sk-test-'
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    scopes JSONB DEFAULT '[]'::jsonb,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT false
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_prompt_history_user ON prompt_history(user_id);
CREATE INDEX idx_prompt_history_team ON prompt_history(team_id);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

---

## API Endpoints Structure

```
Authentication:
POST   /api/v1/auth/register          - Register new user
POST   /api/v1/auth/login             - Login with email/password
POST   /api/v1/auth/refresh           - Refresh access token
POST   /api/v1/auth/logout            - Logout (revoke refresh token)
GET    /api/v1/auth/me                - Get current user
POST   /api/v1/auth/verify-email      - Verify email address
POST   /api/v1/auth/reset-password    - Reset password

OAuth:
GET    /api/v1/auth/oauth/{provider}  - Initiate OAuth flow
GET    /api/v1/auth/oauth/callback    - OAuth callback

Users:
GET    /api/v1/users/me               - Get current user profile
PATCH  /api/v1/users/me               - Update profile
DELETE /api/v1/users/me               - Delete account

Teams:
GET    /api/v1/teams                  - List user's teams
POST   /api/v1/teams                  - Create team
GET    /api/v1/teams/{id}             - Get team details
PATCH  /api/v1/teams/{id}             - Update team
DELETE /api/v1/teams/{id}             - Delete team
POST   /api/v1/teams/{id}/members     - Add team member
DELETE /api/v1/teams/{id}/members/{user_id} - Remove member

Prompts:
POST   /api/v1/prompts/analyze        - Analyze prompt (generate questions)
POST   /api/v1/prompts/refine         - Refine prompt with answers
POST   /api/v1/prompts/tweak          - Tweak refined prompt
GET    /api/v1/prompts/history        - Get user's prompt history
GET    /api/v1/prompts/{id}           - Get specific prompt
DELETE /api/v1/prompts/{id}           - Delete prompt

Providers:
GET    /api/v1/providers              - List available LLM providers
GET    /api/v1/providers/{id}/models  - List models for provider

API Keys:
GET    /api/v1/api-keys               - List user's API keys
POST   /api/v1/api-keys               - Create new API key
DELETE /api/v1/api-keys/{id}          - Revoke API key
```

---

## CLI Authentication Flow

```bash
# Option 1: Browser-based (OAuth2 device flow)
$ promptheus login
Opening browser for authentication...
Waiting for approval...
✓ Authenticated as john@example.com (Team: Acme Inc)

# Option 2: API key (for CI/CD, scripts)
$ promptheus login --api-key
Enter your API key: sk-live-xxxxxxxxxxxxx
✓ Authenticated successfully

# Option 3: Environment variable
$ export PROMPTHEUS_API_KEY=sk-live-xxxxxxxxxxxxx
$ promptheus "Generate a prompt"

# Check auth status
$ promptheus whoami
Authenticated as: john@example.com
Team: Acme Inc (5 members)
Plan: Team
API Usage: 1,247 / 10,000 prompts this month
```

---

## Security Considerations

### Access Token Structure (JWT)
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "team_id": "team-uuid",
  "role": "admin",
  "scopes": ["prompts:read", "prompts:write", "teams:admin"],
  "exp": 1699999999,
  "iat": 1699996399,
  "iss": "promptheus-api"
}
```

### Rate Limiting
```
Public endpoints: 10 req/min per IP
Authenticated users: 100 req/min
Team plan: 1000 req/min
Enterprise: Unlimited
```

### Password Requirements
- Minimum 12 characters
- Must include: uppercase, lowercase, number, special char
- bcrypt hashing with cost factor 12
- Password history (prevent reuse of last 5)

### Token Security
- Access tokens: 15 min expiry
- Refresh tokens: 30 days expiry
- HttpOnly cookies for web
- Secure flag for production
- SameSite=Strict for CSRF protection

---

## Deployment Architecture

### Local Development
```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: promptheus
      POSTGRES_USER: promptheus
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://promptheus:dev_password@postgres:5432/promptheus
      REDIS_URL: redis://redis:6379
      SECRET_KEY: dev_secret_key_change_in_production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
```

### EC2 Production Deployment
```
┌─────────────────────────────────────────────┐
│              AWS EC2 Instance               │
│  ┌───────────────────────────────────────┐  │
│  │           Nginx (Reverse Proxy)       │  │
│  │   :443 (HTTPS) → React + FastAPI      │  │
│  └───────────────────────────────────────┘  │
│  ┌──────────────┐    ┌──────────────────┐  │
│  │   FastAPI    │    │   React (Build)  │  │
│  │   :8000      │    │   Served by Nginx│  │
│  └──────────────┘    └──────────────────┘  │
└─────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
    ┌──────────────┐    ┌──────────────┐
    │  AWS RDS     │    │  ElastiCache │
    │  PostgreSQL  │    │  Redis       │
    └──────────────┘    └──────────────┘
```

### Infrastructure as Code (Terraform)
```hcl
# main.tf
resource "aws_instance" "promptheus_server" {
  ami           = "ami-0c55b159cbfafe1f0" # Ubuntu 22.04
  instance_type = "t3.medium"
  key_name      = var.ssh_key_name

  vpc_security_group_ids = [aws_security_group.promptheus_sg.id]

  user_data = file("scripts/setup.sh")

  tags = {
    Name        = "Promptheus-Server"
    Environment = var.environment
  }
}

resource "aws_db_instance" "promptheus_db" {
  identifier        = "promptheus-db"
  engine            = "postgres"
  engine_version    = "16.1"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_encrypted = true

  db_name  = "promptheus"
  username = var.db_username
  password = var.db_password

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  skip_final_snapshot = var.environment == "dev"
}

resource "aws_elasticache_cluster" "promptheus_redis" {
  cluster_id           = "promptheus-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}
```

---

## Migration Plan from CLI to Multi-User

### Phase 1: Backend API (Week 1-2)
- [ ] Set up FastAPI project structure
- [ ] Implement JWT authentication
- [ ] Create user registration/login endpoints
- [ ] Database schema and migrations
- [ ] Port prompt refinement logic to API
- [ ] Add rate limiting and security middleware

### Phase 2: Web Frontend (Week 3-4)
- [ ] Set up React + TypeScript project
- [ ] Implement authentication UI (login/register)
- [ ] Build prompt refinement interface
- [ ] Create history view
- [ ] Team management UI
- [ ] Responsive design

### Phase 3: CLI Integration (Week 5)
- [ ] Add `promptheus login` command
- [ ] Store auth tokens locally
- [ ] Modify CLI to call backend API
- [ ] Maintain backward compatibility for local-only mode
- [ ] Update documentation

### Phase 4: Testing & Deployment (Week 6-7)
- [ ] Unit tests (pytest for backend, Jest for frontend)
- [ ] Integration tests
- [ ] E2E tests (Playwright)
- [ ] Docker images
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Deploy to EC2

### Phase 5: OKTA Integration (Week 8+)
- [ ] OKTA developer account setup
- [ ] SAML/OAuth2 integration
- [ ] Enterprise team management
- [ ] SSO testing
- [ ] Documentation for enterprise customers

---

## Cost Estimation (AWS EC2 Deployment)

### MVP (10-50 users)
- EC2 t3.medium: $30/month
- RDS db.t3.micro: $15/month
- ElastiCache cache.t3.micro: $12/month
- Data transfer: ~$5/month
- **Total: ~$62/month**

### Growth (100-500 users)
- EC2 t3.large: $60/month
- RDS db.t3.small: $30/month
- ElastiCache cache.t3.small: $24/month
- Load Balancer: $20/month
- Data transfer: ~$20/month
- **Total: ~$154/month**

### Scale (1000+ users)
- EC2 c5.xlarge (2 instances): $250/month
- RDS db.m5.large: $150/month
- ElastiCache cache.m5.large: $100/month
- Load Balancer: $20/month
- CloudFront CDN: $30/month
- Data transfer: ~$50/month
- **Total: ~$600/month**

---

## Next Steps

1. **Review this plan** with the team
2. **Choose authentication strategy** (Recommended: Option 1 - JWT)
3. **Set up development environment** (Docker Compose)
4. **Start with backend API** (FastAPI + PostgreSQL)
5. **Build React frontend** in parallel
6. **Integrate CLI authentication**
7. **Deploy MVP to EC2**
8. **Iterate based on user feedback**
9. **Add OKTA when enterprise customers onboard**

---

## Questions to Answer

1. **Team size**: How many users initially? (Affects infrastructure sizing)
2. **Privacy requirements**: Can prompts be stored in cloud, or need on-prem option?
3. **LLM API keys**: User-provided or platform-managed?
4. **Pricing model**: Free tier? Subscription? Usage-based?
5. **Compliance**: GDPR, SOC2, or other requirements?
6. **Timeline**: MVP deadline?

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React + TypeScript Best Practices](https://react-typescript-cheatsheet.netlify.app/)
- [JWT.io](https://jwt.io/) - JWT debugger
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Security guidelines
- [12 Factor App](https://12factor.net/) - Deployment best practices
