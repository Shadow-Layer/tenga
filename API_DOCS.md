# Tenga Inventory POS API Documentation

## Overview

The Tenga Inventory POS API is a FastAPI-based REST API for managing point-of-sale transactions, inventory, locations, and organizations. The API supports both online and offline operations with automatic synchronization.

## Getting Started

### OpenAPI Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI (Interactive)**: http://localhost:8000/docs
- **ReDoc (Read-only)**: http://localhost:8000/redoc
- **OpenAPI 3.0 Schema**: http://localhost:8000/openapi.json

The `openapi.json` file in this directory contains the complete OpenAPI 3.1.0 specification.

### Health Check

```bash
# Basic health check
curl http://localhost:8000/health

# Readiness check (verifies database connectivity)
curl http://localhost:8000/ready
```

## API Endpoints

### Organizations

Manage organizations (top-level tenant containers).

#### Create Organization
```bash
curl -X POST http://localhost:8000/organizations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Store",
    "code": "MAIN001",
    "description": "Main retail location"
  }'
```

#### List Organizations
```bash
curl http://localhost:8000/organizations?skip=0&limit=10
```

#### Get Organization Details
```bash
curl http://localhost:8000/organizations/1
```

### Products

Manage products and catalog.

#### Create Product
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Widget A",
    "sku": "WIDGET-A-001",
    "description": "Premium widget",
    "category": "Widgets",
    "price": 29.99,
    "cost": 15.00,
    "organization_id": 1
  }'
```

#### List Products
```bash
curl http://localhost:8000/api/v1/products?organization_id=1&skip=0&limit=20
```

#### Get Product Details
```bash
curl http://localhost:8000/api/v1/products/1
```

### Locations

Manage store locations and warehouses.

#### Create Location
```bash
curl -X POST http://localhost:8000/api/v1/locations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Store",
    "code": "LOC001",
    "description": "Main retail location",
    "organization_id": 1
  }'
```

#### List Locations
```bash
curl http://localhost:8000/api/v1/locations?organization_id=1&skip=0&limit=10
```

### Tills

Manage point-of-sale tills and sessions.

#### Create Till
```bash
curl -X POST http://localhost:8000/api/v1/tills/ \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": 1,
    "code": "TILL001",
    "name": "Till 1 - Main Floor"
  }'
```

#### List Tills
```bash
curl http://localhost:8000/api/v1/tills/?organization_id=1&location_id=1&skip=0&limit=10
```

#### Open Till Session
```bash
curl -X POST http://localhost:8000/api/v1/tills/1/open \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "opening_balance": 5000.00
  }'
```

#### Check Till Status
```bash
curl http://localhost:8000/api/v1/tills/1/status
```

#### Close Till Session
```bash
curl -X POST http://localhost:8000/api/v1/tills/1/close \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "closing_amount_cents": 50000.0,
    "notes": "Balance verified"
  }'
```

### Sales

Process point-of-sale transactions.

#### Create Sale (Online)
```bash
curl -X POST http://localhost:8000/api/v1/sales \
  -H "Content-Type: application/json" \
  -d '{
    "till_id": 1,
    "cashier_id": 1,
    "payment_method": "CASH",
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "unit_price": 29.99
      },
      {
        "product_id": 2,
        "quantity": 1,
        "unit_price": 15.50
      }
    ],
    "is_offline": false,
    "notes": "Customer order #123"
  }'
```

#### Create Sale (Offline/Pending)
```bash
curl -X POST http://localhost:8000/api/v1/sales \
  -H "Content-Type: application/json" \
  -d '{
    "till_id": 1,
    "cashier_id": 1,
    "payment_method": "CARD",
    "items": [
      {
        "product_id": 1,
        "quantity": 1,
        "unit_price": 29.99
      }
    ],
    "is_offline": true,
    "notes": "Created while offline"
  }'
```

#### Commit Pending Sale
```bash
curl -X POST http://localhost:8000/api/v1/sales/1/commit \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1
  }'
```

#### List Sales
```bash
curl http://localhost:8000/api/v1/sales?organization_id=1&till_id=1&status=COMPLETED&skip=0&limit=20
```

#### Get Sale Details
```bash
curl http://localhost:8000/api/v1/sales/1
```

### Inventory

Manage stock levels and movements.

#### Get Stock at Location
```bash
curl http://localhost:8000/api/v1/stock/locations/1/stock
```

#### Record Inventory Movement
```bash
curl -X POST http://localhost:8000/api/v1/stock/stock/movements \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "location_id": 1,
    "from_location_id": null,
    "to_location_id": null,
    "quantity": 50,
    "movement_type": "receipt",
    "reason": "Goods receipt from supplier",
    "recorded_by_id": 1,
    "metadata": {
      "purchase_order": "PO-2026-001"
    }
  }'
```

#### Adjust Stock
```bash
curl -X POST http://localhost:8000/api/v1/stock/stock/adjust \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "location_id": 1,
    "quantity": -5,
    "reason": "PHYSICAL_COUNT_DISCREPANCY",
    "recorded_by_id": 1,
    "note": "Damaged items found during count"
  }'
```

#### List Inventory Movements
```bash
curl http://localhost:8000/api/v1/stock/stock/movements?product_id=1&location_id=1&skip=0&limit=20
```

#### View Discrepancies
```bash
curl http://localhost:8000/api/v1/stock/stock/discrepancies?location_id=1
```

### Subscriptions

Manage organization subscriptions.

#### Get Subscription Details
```bash
curl http://localhost:8000/subscriptions/1
```

#### Get Subscription State
```bash
curl http://localhost:8000/subscriptions/1/state
```

#### Renew Subscription
```bash
curl -X POST http://localhost:8000/subscriptions/1/renew \
  -H "Content-Type: application/json" \
  -d '{
    "new_expiry_date": "2027-10-07T00:00:00Z"
  }'
```

### Users

Manage users within organizations.

#### Create User
```bash
curl -X POST http://localhost:8000/organizations/1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "password_hash": "hashed_password_here",
    "role": "operator"
  }'
```

#### List Users
```bash
curl http://localhost:8000/organizations/1/users?skip=0&limit=10
```

#### Get User Details
```bash
curl http://localhost:8000/organizations/1/users/1
```

### Sync (Offline/Online)

Synchronize offline transactions and manage device state.

#### Submit Sync Batch
```bash
curl -X POST http://localhost:8000/api/v1/sync/sync/batch \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device-001",
    "organization_id": 1,
    "items": [
      {
        "batch_id": "batch-001",
        "sequence": 1,
        "action": "SALE_COMMIT",
        "payload": {
          "sale_id": 1
        }
      }
    ]
  }'
```

#### Check Sync Status
```bash
curl http://localhost:8000/api/v1/sync/sync/status/batch-001
```

#### Cache Subscription State
```bash
curl -X POST http://localhost:8000/api/v1/sync/cache/subscription-state \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device-001",
    "organization_id": 1,
    "subscription_state": {
      "state": "ACTIVE",
      "expiry_date": "2027-10-07T00:00:00Z",
      "grace_end_date": null,
      "days_remaining": 365,
      "operational": true
    }
  }'
```

## Response Format

All successful responses follow this format:

```json
{
  "id": 1,
  "name": "Example",
  "created_at": "2026-10-07T16:13:50.467Z",
  "updated_at": "2026-10-07T16:13:50.467Z"
}
```

### Paginated Responses

List endpoints return paginated responses:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Item 1"
    },
    {
      "id": 2,
      "name": "Item 2"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 10
}
```

## Error Responses

Error responses use standard HTTP status codes:

- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `409 Conflict` - Data conflict (e.g., duplicate SKU)
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

Error response format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "type": "http_error"
}
```

## Authentication

Authentication will be added in a future phase (T010-Authentication).

## Key Features

### Multi-Tenancy
- All data is organization-scoped
- Provide `organization_id` in relevant requests

### Offline Support
- Sales can be created with `is_offline: true`
- Offline sales are synced when connection is restored
- Subscription state is cached on devices

### Subscription States
- **ACTIVE**: Full functionality available
- **GRACE**: Subscription expired but within grace period
- **LIMITED**: Expired and grace period ended - limited functionality

### Stock Management
- No oversell restrictions (per design U006)
- Tracks inventory movements with reasons
- Supports physical count reconciliation
- Handles adjustments (damage, shrinkage, discrepancies)

### Till Sessions
- Tills must have open sessions for sales
- Opening and closing balances tracked
- Session history maintained for reconciliation

## API Versioning

Current API version: **1.0.0**

All endpoints use the prefix `/api/v1` for consistency and future-proofing.

## Rate Limiting

Currently not implemented. Will be added based on subscription tier in future phases.

## Webhooks

Currently not implemented. Can be added for real-time event notifications.

## SDKs

No official SDKs yet. Clients should use the OpenAPI specification to generate SDK code using:
- OpenAPI Generator
- Swagger Codegen
- Other code generation tools

## Support

For API issues and questions:
1. Check the interactive documentation at `/docs`
2. Review the OpenAPI specification at `/openapi.json`
3. Review the source code in `src/routers/`
4. File an issue in the project repository

## API Status

- **Health**: `/health` - Always available status
- **Readiness**: `/ready` - Checks database connectivity
- **Docs**: `/docs` - Swagger UI (dev/test only)
- **ReDoc**: `/redoc` - ReDoc documentation (dev/test only)
- **OpenAPI**: `/openapi.json` - OpenAPI 3.1.0 specification

## Database Schema

The API uses SQLAlchemy ORM with support for:
- Organizations (multi-tenancy)
- Products and inventory
- Locations/warehouses
- Users and permissions
- Tills and sessions
- Sales transactions
- Inventory movements
- Subscriptions and licensing
- Sync batches and caching

See `src/models/entities.py` for the complete schema definition.

## Next Steps

Upcoming features and improvements:

1. **T010-Authentication** - JWT-based authentication
2. **Rate Limiting** - By subscription tier
3. **Webhooks** - Real-time event notifications
4. **Advanced Reporting** - Sales analytics and inventory reports
5. **Bulk Operations** - Batch import/export
6. **Analytics API** - Real-time dashboard data

---

*Generated by T008-J: OpenAPI & Documentation*
*Last updated: 2026-10-07*
