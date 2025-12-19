# My SaaS Skeleton

A production-ready SaaS application skeleton built with the [lessweb](https://github.com/lessweb/lessweb) framework.

## Features

- **Admin Authentication**: JWT-based authentication with Redis session management
- **Database Management**: MySQL with async operations via commondao ORM
- **Database Migrations**: Automated schema migrations using pyway
- **Task Queue**: Background job processing with BullMQ and Redis
- **System Monitoring**: Scheduled health checks for database connectivity
- **API Documentation**: Auto-generated OpenAPI/Swagger specifications
- **Testing**: Comprehensive E2E tests with pytest

## Tech Stack

- **Framework**: lessweb (Python web framework with dependency injection)
- **Database**: MySQL with aiomysql async driver
- **ORM**: commondao (async MySQL toolkit with Pydantic integration)
- **Cache/Queue**: Redis with BullMQ for job scheduling
- **Authentication**: JWT tokens with bcrypt password hashing
- **Testing**: pytest with aiohttp test client

## Quick Start

### Prerequisites

- Python 3.11+
- MySQL 5.7+
- Redis 6.0+

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database and Redis credentials
```

3. Run database migrations:
```bash
make pyway-migrate
```

4. Start the application:
```bash
python main.py
```

The server will start at `http://localhost:8080`

### Default Admin Credentials

- Username: `admin`
- Password: `admin123`

**Important**: Change the default password in production!

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests --cov=src --cov-report=html

# Run linting
make lint
```

### Database Migrations

```bash
# Create new migration
# 1. Create migration file in migration/ directory following naming convention:
#    V{major}_{minor}_{patch}__{description}.sql

# 2. Run migration
make pyway-migrate
```

### OpenAPI Documentation

The OpenAPI specification is automatically updated on startup. To manually update:

```bash
make dump-openapi
```

In staging environment, access the OpenAPI spec at: `http://localhost:8080/openapi/openapi.json`

## Project Structure

```
.
├── config/              # Configuration files (TOML format)
│   ├── mysql.toml
│   ├── redis.toml
│   ├── lessweb.toml
│   ├── bullmq.toml
│   └── jwt_gateway.toml
├── migration/           # Database migration scripts
├── openapi/            # OpenAPI specification
├── shared/             # Shared modules and plugins
│   ├── bullmq_plugin.py
│   ├── error_middleware.py
│   ├── jwt_gateway.py
│   ├── lessweb_commondao.py
│   └── redis_plugin.py
├── src/
│   ├── controller/     # API endpoints
│   ├── entity/         # Database models
│   ├── service/        # Business logic services
│   └── processor/      # Background job processors
├── tests/
│   └── e2e/           # End-to-end tests
├── main.py            # Application entry point
└── Dockerfile         # Docker container definition
```

## API Endpoints

### Authentication

- `POST /login/admin` - Admin login (returns JWT token)
- `GET /admin/me` - Get current admin info (requires auth)

### Configuration

Environment-specific configurations are managed through:

- `.env` - Local development
- `.env.testci` - CI/CD testing
- `.env.staging` - Staging environment
- `.env.production` - Production environment

Configuration files in `config/` can also have environment-specific versions:
- `config/redis.production.toml` - Production Redis with password

## Background Jobs

The application uses BullMQ for scheduled tasks:

- **Database Health Check** (every 2 hours): Executes `SELECT 1` to verify database connectivity

## Docker Deployment

```bash
# Build image
docker build -t my-saas-skeleton .

# Run container
docker run -p 8080:8080 --env-file .env.production my-saas-skeleton
```

## License

MIT
