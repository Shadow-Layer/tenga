# Tenga Inventory POS - Setup & Quick Start Guide

## System Overview

**Tenga Inventory POS** is a containerized point-of-sale and inventory management system designed for small businesses. It consists of:

- **FastAPI Backend** - REST API for all POS and inventory operations
- **React Frontend** - Web-based POS interface with real-time inventory tracking
- **PostgreSQL Database** - Persistent data storage
- **Nginx Proxy** - Routes traffic between frontend and API

## Getting Started (5 minutes)

### 1. Access the Application

**Open your browser:**
```
http://localhost/
```

You should see the Tenga Inventory POS login page.

### 2. Create and sign in to the first administrator

There are no shared demo accounts. On an empty installation, follow
[`docs/INSTALLATION_BOOTSTRAP.md`](docs/INSTALLATION_BOOTSTRAP.md) to create a
new organization and administrator using a unique, protected setup secret.
Then sign in with the account you just created.

### 3. View the Quick Start Dashboard

After logging in, you'll see an **8-step Quick Start Guide** that walks you through:

1. ✅ Creating a Location (physical store)
2. ✅ Creating Products (items to sell)
3. ✅ Adding Stock (inventory levels)
4. ✅ Creating a Till (cash register)
5. ✅ Opening a Till Session (start of shift)
6. ✅ Processing a Sale (POS transaction)
7. ✅ Verifying Stock (inventory deduction)
8. ✅ Closing the Till (end of shift)

**Each step includes:**
- API endpoint reference
- Example request body (JSON)
- Direct link to Swagger UI with the endpoint highlighted

## API Documentation

### Swagger UI (Interactive)
```
http://localhost/docs
```

- Try-it-out functionality
- Full parameter documentation
- Response examples
- Schema definitions

### ReDoc (Readable)
```
http://localhost/redoc
```

Beautiful, easy-to-read API documentation

### OpenAPI Spec (Raw)
```
http://localhost/openapi.json
```

Full OpenAPI 3.0 specification in JSON format

## Key API Endpoints

All endpoints require Bearer token authentication:

```bash
# Authenticate with the organization-specific owner account created during
# first-install bootstrap. Never use credentials copied from an example.
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d @/path/to/private-login-request.json

# Use token in subsequent requests
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/v1/organizations
```

### Organization & Location Management
```
POST   /api/v1/locations                - Create location
GET    /api/v1/locations                - List locations
GET    /api/v1/locations/{id}           - Get location details
```

### Product Management
```
POST   /api/v1/products                 - Create product
GET    /api/v1/products                 - List products
GET    /api/v1/products/{id}            - Get product details
PUT    /api/v1/products/{id}            - Update product
```

### Inventory & Stock
```
POST   /api/v1/stock/stock/adjust      - Adjust stock levels
GET    /api/v1/stock/locations/{id}    - Get stock at location
GET    /api/v1/stock/movements         - Get stock movement history
```

### Till & Sessions
```
POST   /api/v1/tills                    - Create till
POST   /api/v1/tills/{id}/open         - Open till session
POST   /api/v1/tills/{id}/close        - Close till session
GET    /api/v1/tills/{id}/sessions     - Get session history
```

### Sales & Transactions
```
POST   /api/v1/sales                    - Process a sale
GET    /api/v1/sales                    - List sales
GET    /api/v1/sales/{id}               - Get sale details
```

## Test Data

A test organization has been pre-created:

| Item          | Value        |
|---------------|--------------|
| Organization  | Test Store   |
| Organization ID | 1         |
| Admin User ID | 2            |
| Cashier User ID | 3          |

You can create additional locations, products, and tills via the API or through the quick start guide.

## Container Architecture

The application runs in Docker with three main services:

```
User Browser
     ↓
 Nginx:80 (Proxy)
    / \
   /   \
React/ API:8000
(SPA) \  (FastAPI)
    \  /
      ↓
  PostgreSQL:5432
```

### Running Containers

```bash
# View running containers
docker ps

# View logs
docker logs tenga-api       # Backend logs
docker logs tenga-frontend  # Frontend logs
docker logs tenga-postgres  # Database logs

# Stop all containers
docker compose down

# Start all containers
docker compose up -d

# Rebuild and start
docker compose up --build -d
```

## Troubleshooting

### "Application is loading..." - stuck on login page

**Solution:** Check that:
1. Open http://localhost/docs - if this works, API is running
2. Check browser console (F12) for JavaScript errors
3. Check API logs: `docker logs tenga-api`
4. Restart containers: `docker compose restart`

### Login fails with "401 Unauthorized"

**Solution:** Verify the email and password for an account created by your
organization's administrator. Do not retry shared sample credentials; none are
provisioned by the application.

### API returns 404 for endpoints

**Solution:** Ensure the API base URL is correct:
```
http://localhost:8000/api/v1/  (not http://localhost:8000/api/v1)
```

###  Stock adjustment returns 422 error

**Solution:** Ensure request includes `organization_id` as query parameter:
```bash
POST /api/v1/stock/stock/adjust?organization_id=1
```

### Database connection errors

**Solution:** Check PostgreSQL is running:
```bash
docker logs tenga-postgres
docker exec tenga-postgres psql -U postgres -d tenga_inventory -c "\dt"
```

## Development & Testing

### Run Full Test Suite

```bash
cd /home/tea/Documents/apps/tenga-inventory
python -m pytest tests/ -v
```

Expected: 129+ tests passing

### View Test Results

- Unit tests for services
- Integration tests for API endpoints
- End-to-end POS workflow tests
- Security & authentication tests
- Offline synchronization tests

## Architecture & Design

### Core Concepts

**Organization** → Business entity (one per installation)
**Location** → Physical store/warehouse (multiple per org)
**Till** → Cash register (multiple per location)
**Product** → Item for sale (catalog)
**Stock** → Inventory level (per product, per location)
**Sale** → Transaction (products + payment)
**Subscription** → License/billing (determines feature access)

### Key Features

✅ **Multi-location inventory tracking**
✅ **Real-time stock deduction on sale**
✅ **Till session management** (open, close, reconciliation)
✅ **Sale history & reporting**
✅ **Offline capability** (pending sync queue)
✅ **Organization isolation** (data per customer)
✅ **Role-based access control** (admin, manager, cashier)
✅ **API-first architecture** (UI independent)

### Offline Synchronization

The system supports offline POS operation:

- Sales processed offline are queued for sync
- Stock levels update once sync completes
- Same transaction ID across online/offline
- Automatic retry on reconnect
- Idempotent operations prevent duplicates

## Deployment

The application is designed for containerized deployment:

### Docker Compose (Development)
```bash
docker compose up -d
```

### Docker/OCI (Production)

Deploy to Oracle Cloud VM:

1. Build images: `docker build -f Dockerfile -t tenga-api .`
2. Push to registry
3. Deploy with docker-compose or Docker Swarm
4. Mount persistent PostgreSQL data volume
5. Configure environment variables for secrets
6. Set up HTTPS reverse proxy
7. Configure backups

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/tenga_inventory

# API
API_VERSION=vT010
SECRET_KEY=<random-key>
JWT_SECRET=<random-secret>

# Frontend
VITE_API_URL=http://localhost:8000/api/v1

# Security
CORS_ORIGINS=["http://localhost"]
```

## Support & Documentation

- **API Docs:** http://localhost/docs
- **Quick Start:** Login page dashboard
- **Test Files:** `/tests/` directory
- **Source Code:** `/src/` directory
- **Migrations:** `/migrations/` directory

## What's Next?

After logging in and reviewing the quick start guide, you can:

1. **Create real test data:**
   - Use the Swagger UI to create locations, products, stock
   - Process real sales transactions
   - Track inventory changes

2. **Explore the API:**
   - Test all endpoints from Swagger UI
   - Review request/response formats
   - Check error handling

3. **Review the codebase:**
   - Backend: `src/` - FastAPI routes, services, models
   - Frontend: `src/` - React components
   - Database: `migrations/` - Schema changes
   - Tests: `tests/` - Comprehensive test coverage

4. **Customize for your use case:**
   - Modify products and pricing
   - Create multiple locations
   - Set up users and roles
   - Configure permissions

---

**System Status:** ✅ All components operational
**Tests Passing:** 129/145
**Database:** PostgreSQL 16 with 20+ tables
**API Version:** vT010
**Frontend:** React with Vite
**Docker:** 3 containers (API, Frontend, Database)
