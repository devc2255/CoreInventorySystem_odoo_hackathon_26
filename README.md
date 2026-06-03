# Core Inventory System

A lightweight Flask-based inventory management demo built for an Odoo hackathon. This repository includes user authentication, product and location management, stock receipts, deliveries, adjustments, and audit logging backed by SQLite.

## Key Features

- User registration, login, logout, and profile management
- Role-based access control for Managers and Warehouse Staff
- Product catalog with unique SKU and duplicate validation
- Location management for vendors, customers, warehouses, and inventory adjustment partner
- Dashboard with inventory summaries, pending operations, low stock alerts, and recent activity
- Receipt processing to add stock
- Delivery processing to remove stock
- Stock adjustment workflow with inventory correction and ledger tracking
- Audit log capture for critical user actions
- OTP-based password reset demo flow
- JSON API endpoints for seeding, receipts, deliveries, and adjustments

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2 templates

## Prerequisites

- Python 3.11+ recommended
- `pip` package manager

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

Start the Flask application with:

```bash
python app.py
```

Open your browser at `http://localhost:5000`.

## Live Demo

Paste your deployed application URL here:

`https://your-deployment-link.example.com`

## Seed Demo Data

To create sample users, product categories, product records, and locations, send a POST request to:

```bash
curl -X POST http://localhost:5000/api/seed
```

Sample credentials created by seed data:

- Manager: `admin@test.com` / `password`
- Warehouse Staff: `staff@test.com` / `password`

## Project Structure

- `app.py` - Main Flask application with routes, models, and business logic
- `requirements.txt` - Python dependencies
- `templates/` - HTML templates for the user interface
- `inventory.db` - SQLite database file generated at runtime (not committed)

## Notes

- The app uses a hard-coded Flask secret key and demo OTP email output to the console; this is intended for hackathon/demo use only.
- Database migrations are not included; the app creates required tables automatically on startup.
- For production use, update the secret key, secure the database, and enable a proper email delivery flow.

## License

This project is provided as-is for hackathon/demo purposes.
