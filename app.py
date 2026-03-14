import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELS (Database Schema)
# ==========================================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Manager')
    address = db.Column(db.Text, nullable=True)
    preferred_payment = db.Column(db.String(20), nullable=True, default='UPI')

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)

class ProductCategory(db.Model):
    __tablename__ = 'product_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'))
    unit_of_measure = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryOperation(db.Model):
    __tablename__ = 'inventory_operations'
    id = db.Column(db.Integer, primary_key=True)
    document_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    source_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    dest_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OperationLine(db.Model):
    __tablename__ = 'operation_lines'
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('inventory_operations.id', ondelete="CASCADE"))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Float, nullable=False)

class StockLedger(db.Model):
    __tablename__ = 'stock_ledger'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    operation_id = db.Column(db.Integer, db.ForeignKey('inventory_operations.id'))
    quantity_change = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# AUTHENTICATION & RBAC MIDDLEWARE
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            flash('Your session has expired. Please log in again.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != allowed_role:
                flash(f'Access Denied: Requires {allowed_role} clearance.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Manager')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please log in.')
            return redirect(url_for('signup'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=name, email=email, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.username
            session['user_role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# FRONTEND VIEWS (Pages)
# ==========================================
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_products = Product.query.count()
    pending_receipts = InventoryOperation.query.filter_by(document_type='Receipt').filter(InventoryOperation.status != 'Done').count()
    pending_deliveries = InventoryOperation.query.filter_by(document_type='Delivery').filter(InventoryOperation.status != 'Done').count()
    
    # Mathematical Logic for "Low / Out of Stock" KPI
    stock_levels = db.session.query(
        StockLedger.product_id,
        func.sum(StockLedger.quantity_change).label('total_stock')
    ).group_by(StockLedger.product_id).all()
    
    # Threshold set to 10 units
    low_stock_count = sum(1 for item in stock_levels if item.total_stock <= 10)
    
    products_with_ledger = len(stock_levels)
    products_without_ledger = total_products - products_with_ledger
    final_low_stock_count = low_stock_count + products_without_ledger

    return render_template('dashboard.html', 
                           total_products=total_products, 
                           pending_receipts=pending_receipts, 
                           pending_deliveries=pending_deliveries,
                           low_stock=final_low_stock_count)

@app.route('/products', methods=['GET', 'POST'])
@login_required
@role_required('Manager') 
def products():
    if request.method == 'POST':
        name = request.form.get('name')
        sku = request.form.get('sku')
        category_id = request.form.get('category_id')
        uom = request.form.get('uom')
        
        if Product.query.filter_by(sku=sku).first():
            flash('Error: A product with this SKU already exists.', 'danger')
            return redirect(url_for('products'))
            
        new_product = Product(name=name, sku=sku, category_id=category_id, unit_of_measure=uom)
        db.session.add(new_product)
        db.session.commit()
        flash(f'Success: Product "{name}" added to catalog.', 'success')
        return redirect(url_for('products'))

    products_list = db.session.query(
        Product.id, Product.name, Product.sku, Product.unit_of_measure, 
        ProductCategory.name.label('category_name')
    ).outerjoin(ProductCategory, Product.category_id == ProductCategory.id).all()
    categories = ProductCategory.query.all()
    return render_template('products.html', products=products_list, categories=categories)

@app.route('/receipts')
@login_required
def receipts():
    vendors = Location.query.filter_by(type='Vendor').all()
    warehouses = Location.query.filter_by(type='Internal').all()
    product_list = Product.query.all()
    return render_template('receipts.html', vendors=vendors, warehouses=warehouses, products=product_list)

@app.route('/deliveries')
@login_required
def deliveries():
    customers = Location.query.filter_by(type='Customer').all()
    warehouses = Location.query.filter_by(type='Internal').all()
    product_list = Product.query.all()
    return render_template('deliveries.html', customers=customers, warehouses=warehouses, products=product_list)

@app.route('/adjustments')
@login_required
def adjustments():
    warehouses = Location.query.filter_by(type='Internal').all()
    product_list = Product.query.all()
    return render_template('adjustments.html', warehouses=warehouses, products=product_list)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.username = request.form.get('name')
        user.email = request.form.get('email')
        new_password = request.form.get('password')
        if new_password and new_password.strip() != '':
            user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        user.address = request.form.get('address')
        user.preferred_payment = request.form.get('preferred_payment')
        db.session.commit()
        session['user_name'] = user.username
        flash('System Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

# ==========================================
# API ENDPOINTS (Data Processing)
# ==========================================
@app.route('/api/seed', methods=['POST'])
def seed_data():
    if User.query.first():
        return jsonify({"message": "Dummy data already exists!"}), 200

    admin = User(username="Admin Manager", email="admin@test.com", password_hash=generate_password_hash("password", method='pbkdf2:sha256'), role="Manager")
    staff = User(username="Warehouse Staff", email="staff@test.com", password_hash=generate_password_hash("password", method='pbkdf2:sha256'), role="Warehouse_Staff")
    
    vendor = Location(name="Steel Supplier Inc.", type="Vendor")
    warehouse = Location(name="Main Warehouse", type="Internal")
    customer = Location(name="Acme Manufacturing", type="Customer")
    adjustment_loc = Location(name="Virtual Adjustment Log", type="Inventory Loss")
    category = ProductCategory(name="Raw Materials")
    
    db.session.add_all([admin, staff, vendor, warehouse, customer, adjustment_loc, category])
    db.session.commit()
    
    product = Product(name="Steel Rods", sku="SR-001", category_id=category.id, unit_of_measure="kg")
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Dummy data created! Use admin@test.com or staff@test.com to test RBAC."}), 201

@app.route('/api/receipts', methods=['POST'])
def process_receipt():
    data = request.get_json()
    new_receipt = InventoryOperation(document_type='Receipt', status='Done', source_location_id=data['vendor_id'], dest_location_id=data['warehouse_id'], created_by=data['user_id'])
    db.session.add(new_receipt)
    db.session.flush() 
    for item in data['items']:
        db.session.add(OperationLine(operation_id=new_receipt.id, product_id=item['product_id'], quantity=item['quantity']))
        db.session.add(StockLedger(product_id=item['product_id'], location_id=data['warehouse_id'], operation_id=new_receipt.id, quantity_change=item['quantity']))
    db.session.commit()
    return jsonify({"message": "Receipt validated and stock updated!", "receipt_id": new_receipt.id}), 201

@app.route('/api/deliveries', methods=['POST'])
def process_delivery():
    data = request.get_json()
    new_delivery = InventoryOperation(document_type='Delivery', status='Done', source_location_id=data['warehouse_id'], dest_location_id=data['customer_id'], created_by=data['user_id'])
    db.session.add(new_delivery)
    db.session.flush()
    for item in data['items']:
        db.session.add(OperationLine(operation_id=new_delivery.id, product_id=item['product_id'], quantity=item['quantity']))
        db.session.add(StockLedger(product_id=item['product_id'], location_id=data['warehouse_id'], operation_id=new_delivery.id, quantity_change=-float(item['quantity'])))
    db.session.commit()
    return jsonify({"message": "Delivery validated! Stock reduced.", "delivery_id": new_delivery.id}), 201

@app.route('/api/adjustments', methods=['POST'])
def process_adjustment():
    data = request.get_json()
    product_id = int(data['product_id'])
    warehouse_id = int(data['warehouse_id'])
    counted_qty = float(data['counted_quantity'])
    current_stock = db.session.query(db.func.sum(StockLedger.quantity_change)).filter_by(product_id=product_id, location_id=warehouse_id).scalar() or 0.0
    diff = counted_qty - current_stock
    if diff == 0:
        return jsonify({"message": "Count matches recorded stock. No adjustment needed."}), 200
    adj_location = Location.query.filter_by(type='Inventory Loss').first()
    new_adj = InventoryOperation(document_type='Adjustment', status='Done', source_location_id=warehouse_id if diff < 0 else adj_location.id, dest_location_id=adj_location.id if diff < 0 else warehouse_id, created_by=data['user_id'])
    db.session.add(new_adj)
    db.session.flush()
    db.session.add(OperationLine(operation_id=new_adj.id, product_id=product_id, quantity=abs(diff)))
    db.session.add(StockLedger(product_id=product_id, location_id=warehouse_id, operation_id=new_adj.id, quantity_change=diff))
    db.session.commit()
    return jsonify({"message": f"Adjustment successful. Stock updated by {diff:+.2f} units."}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True, port=5000)