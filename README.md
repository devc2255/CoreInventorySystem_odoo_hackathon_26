# 📦 CoreInventory System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Framework-black.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey.svg)
![Status](https://img.shields.io/badge/Status-Hackathon_Ready-success.svg)

## 🚀 Overview
**CoreInventory** is an enterprise-grade, mathematically rigorous inventory management system built for the **Odoo Hackathon**. 

Designed with the precision and security required for FinTech and Investment Advisory platforms, this application abandons simple "quantity overwrites" in favor of a robust, transaction-based **Stock Ledger**. Every receipt, delivery, and adjustment is recorded as an immutable operation, ensuring perfect data integrity and auditability. 

This project demonstrates core computer engineering principles, integrating secure role-based access control, dynamic data visualization, and the analytical rigor of a research analyst into a seamless web application. It serves as a cornerstone piece for a broader data science and software portfolio.

---

## ✨ Key Features

* **🔒 Role-Based Access Control (RBAC):** Strict segregation of duties. **Managers** have full configuration access (Catalog, Audit Logs), while **Warehouse Staff** are restricted to execution tasks (Receipts, Deliveries, Counts).
* **🧮 Transactional Stock Ledger:** Calculates real-time inventory levels dynamically using `SQLAlchemy func.sum()`, eliminating race conditions and ensuring perfect historical accuracy.
* **🛡️ Enterprise Security:** Implements `Werkzeug` PBKDF2 password hashing, secure session management, and a custom OTP (One-Time Password) recovery flow.
* **🚦 Graceful Error Handling:** Global error interceptors (`@app.errorhandler`) protect the database from locking up during failed transactions, falling back to clean JSON responses or custom UI alerts without crashing.
* **📊 Dynamic FinTech Dashboard:** A dark-themed, responsive Bootstrap UI featuring real-time KPI calculations, critical low-stock alerts, and recent operation feeds.

---

## 🛠️ Technical Stack

* **Backend:** Python, Flask
* **Database:** SQLite, Flask-SQLAlchemy (ORM)
* **Frontend:** HTML5, CSS3, Bootstrap 5, Jinja2 Templating
* **Security:** Werkzeug Security, Custom Authentication Middleware

---

## 💻 Local Setup & Installation

Follow these steps to run the system locally:

**1. Clone the repository**
```bash
git clone https://github.com/devc2255/CoreInventorySystem_odoo_hackathon_26.git
cd CoreInventory
```

**2. Create a virtual environment (Recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install Flask Flask-SQLAlchemy Werkzeug
```

**4. Start the Application**
```bash
python app.py
```

**5. Seed the Database**  
Open a new terminal tab and run the following command to inject the baseline schema, dummy locations, products, and test accounts:
```bash
curl -X POST http://127.0.0.1:5000/api/seed
```

---

## 🔐 Default Test Accounts
Use these credentials to test the RBAC security functionality:

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Manager** | admin@test.com | password | Full System Access, Catalog Management |
| **Staff** | staff@test.com | password | Execution Only (Receipts/Deliveries) |

---

## 🧠 System Architecture Highlight
Rather than storing a static integer for a product's stock, CoreInventory uses a ledger-based approach. When an order is fulfilled, an `InventoryOperation` is created alongside an `OperationLine`. Simultaneously, a `StockLedger` entry is committed:

```python
# Outbound Delivery Logic Snippet
db.session.add(StockLedger(
    product_id=item['product_id'], 
    location_id=data['warehouse_id'], 
    operation_id=new_delivery.id, 
    quantity_change=-float(item['quantity']) # Mathematically deducts stock
))
```

This architecture mirrors financial double-entry bookkeeping, making it highly extensible for future integrations with accounting or ERP software.
