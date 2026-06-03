# Core Inventory System

A Flask-based inventory management demo built for an Odoo hackathon.
This repository provides a lightweight warehouse system with product pricing, receipts, deliveries, inventory adjustments, audit logging, and role-aware user flows.

## What’s Included

- User authentication with registration, login, logout, and profile management
- Role support for Managers and Warehouse Staff
- Product catalog with unique SKU validation, pricing, quantity tracking, and category support
- Location management for warehouses, vendors, customers, and adjustment partners
- Dashboard summaries with total asset value, inventory charts, low stock alerts, and recent activity
- Receipt creation to add stock and delivery creation to remove stock
- Stock adjustment workflow with correction records and audit tracking
- Audit log tracking for critical actions across the app
- OTP-based password reset demo flow
- API endpoints for seeding demo data and managing receipts, deliveries, and adjustments

## Recent Improvements

- Enhanced product form and product table with pricing details and stock metadata
- Dashboard improvements with asset value display and chart visualizations
- Authentication flow fixes using the PRG pattern to improve form behavior and redirect handling
- Updated deployment and dependency support with `gunicorn` in `requirements.txt`

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2
- HTML/CSS templates

## Prerequisites

- Python 3.11+ recommended
- `pip`

[Live Deployment](https://core-inventory-system-rpi1.onrender.com)
[![Database](https://img.shields.io/badge/Database-Neon_PostgreSQL-316192)](https://neon.tech/)
## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/devc2255/CoreInventorySystem_odoo_hackathon_26.git
   cd CoreInventorySystem_odoo_hackathon_26
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Running the App

Start the application with:

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.




## Seed Demo Data

Create sample users, products, categories, and locations with:

```bash
curl -X POST http://localhost:5000/api/seed
```

Sample seeded credentials:

- Manager: `admin@test.com` / `password`
- Warehouse Staff: `staff@test.com` / `password`

## Project Structure

- `app.py` — Main Flask application containing routes, models, and business logic
- `requirements.txt` — Python dependencies
- `templates/` — UI templates for pages such as dashboard, products, receipts, deliveries, and adjustments
- `instance/` — runtime folder for app configuration and local state

## Notes

- This app uses a demo OTP reset flow and a development-grade secret key; it is intended for demonstration and hackathon use.
- Database tables are created automatically on first run.
- For production use, replace the hard-coded secret key, secure the database, and configure a proper email service.

## License

Provided as-is for hackathon/demo purposes.
