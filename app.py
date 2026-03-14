import os
import random
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELS 
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
    # OTP Recovery Columns
    reset_otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

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

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='logs')

# ==========================================
# HELPERS & CONTEXT PROCESSORS
# ==========================================
def log_action(user_id, action, details=""):
    new_log = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(new_log)
    db.session.commit()

@app.context_processor
def inject_global_data():
    if 'user_id' in session:
        nav_pending = InventoryOperation.query.filter(InventoryOperation.status != 'Done').order_by(InventoryOperation.created_at.desc()).limit(4).all()
        nav_completed = InventoryOperation.query.filter_by(status='Done').order_by(InventoryOperation.created_at.desc()).limit(4).all()
        return dict(nav_pending=nav_pending, nav_completed=nav_completed)
    return dict()

# ==========================================
# AUTHENTICATION & RBAC MIDDLEWARE
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
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
# ROUTES
# ==========================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Manager')
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('signup'))
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=name, email=email, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
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
            log_action(user.id, "System Login", f"Authenticated successfully via {email}")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], "System Logout", "User ended session manually.")
    session.clear()
    return redirect(url_for('login'))

# --- OTP RECOVERY ROUTES ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            otp = str(random.randint(100000, 999999))
            user.reset_otp = otp
            user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            
            # Print to terminal to act as our "Email Server"
            print(f"\n========== 📧 SYSTEM EMAIL OUTBOX ==========")
            print(f"To: {email}")
            print(f"Subject: Password Reset Request")
            print(f"Your secure OTP is: {otp}")
            print(f"============================================\n")
            
            flash(f'Demo Mode: An OTP ({otp}) has been sent to your email.', 'info')
            session['reset_email'] = email
            return redirect(url_for('verify_otp'))
        else:
            flash('If that email is registered, an OTP has been sent.', 'info')
            
    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_email' not in session: return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        otp_entered = request.form.get('otp')
        user = User.query.filter_by(email=session['reset_email']).first()
        
        if user and user.reset_otp == otp_entered:
            if datetime.utcnow() > user.otp_expiry:
                flash('OTP has expired. Please request a new one.', 'danger')
                return redirect(url_for('forgot_password'))
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please check your email and try again.', 'danger')
            
    return render_template('verify_otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or 'reset_email' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.filter_by(email=session['reset_email']).first()
        
        if user:
            user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            user.reset_otp = None
            user.otp_expiry = None
            db.session.commit()
            log_action(user.id, "Password Recovered", "User reset password via OTP verification.")
            session.pop('reset_email', None)
            session.pop('otp_verified', None)
            flash('Password reset successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
            
    return render_template('reset_password.html')

# --- MAIN APP ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_products = Product.query.count()
    pending_receipts = InventoryOperation.query.filter_by(document_type='Receipt').filter(InventoryOperation.status != 'Done').count()
    pending_deliveries = InventoryOperation.query.filter_by(document_type='Delivery').filter(InventoryOperation.status != 'Done').count()
    total_completed = InventoryOperation.query.filter_by(status='Done').count()
    
    stock_levels = db.session.query(StockLedger.product_id, func.sum(StockLedger.quantity_change).label('total_stock')).group_by(StockLedger.product_id).all()
    stock_dict = {item.product_id: item.total_stock for item in stock_levels}
    all_products = Product.query.all()
    
    low_stock_items = []
    for p in all_products:
        qty = stock_dict.get(p.id, 0.0)
        if qty <= 10:
            low_stock_items.append({'product': p, 'qty': qty})
            
    low_stock_items.sort(key=lambda x: x['qty'])
    low_stock_count = len(low_stock_items)

    recent_ops = InventoryOperation.query.order_by(InventoryOperation.created_at.desc()).limit(8).all()
    loc_map = {loc.id: loc.name for loc in Location.query.all()}

    return render_template('dashboard.html', total_products=total_products, pending_receipts=pending_receipts, pending_deliveries=pending_deliveries, total_completed=total_completed, low_stock=low_stock_count, low_stock_items=low_stock_items[:5], recent_ops=recent_ops, loc_map=loc_map)

@app.route('/products', methods=['GET', 'POST'])
@login_required
@role_required('Manager') 
def products():
    if request.method == 'POST':
        name = request.form.get('name')
        sku = request.form.get('sku')
        category_id = request.form.get('category_id')
        uom = request.form.get('uom')
        new_product = Product(name=name, sku=sku, category_id=category_id, unit_of_measure=uom)
        db.session.add(new_product)
        db.session.commit()
        log_action(session['user_id'], "Product Created", f"Added '{name}' (SKU: {sku}) to catalog.")
        flash(f'Success: Product "{name}" added.', 'success')
        return redirect(url_for('products'))
    products_list = db.session.query(Product.id, Product.name, Product.sku, Product.unit_of_measure, ProductCategory.name.label('category_name')).outerjoin(ProductCategory, Product.category_id == ProductCategory.id).all()
    categories = ProductCategory.query.all()
    return render_template('products.html', products=products_list, categories=categories)

@app.route('/locations', methods=['GET', 'POST'])
@login_required
@role_required('Manager')
def locations():
    if request.method == 'POST':
        name = request.form.get('name')
        loc_type = request.form.get('type')
        new_loc = Location(name=name, type=loc_type)
        db.session.add(new_loc)
        db.session.commit()
        log_action(session['user_id'], "Location Created", f"Added new {loc_type}: '{name}'.")
        flash(f'Success: {loc_type} "{name}" added to network.', 'success')
        return redirect(url_for('locations'))
    locations_list = Location.query.all()
    return render_template('locations.html', locations=locations_list)

@app.route('/receipts')
@login_required
def receipts():
    vendors = Location.query.filter_by(type='Vendor').all()
    warehouses = Location.query.filter_by(type='Internal').all()
    products = Product.query.all()
    return render_template('receipts.html', vendors=vendors, warehouses=warehouses, products=products)

@app.route('/deliveries')
@login_required
def deliveries():
    customers = Location.query.filter_by(type='Customer').all()
    warehouses = Location.query.filter_by(type='Internal').all()
    products = Product.query.all()
    return render_template('deliveries.html', customers=customers, warehouses=warehouses, products=products)

@app.route('/adjustments')
@login_required
def adjustments():
    warehouses = Location.query.filter_by(type='Internal').all()
    products = Product.query.all()
    return render_template('adjustments.html', warehouses=warehouses, products=products)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.username = request.form.get('name')
        user.email = request.form.get('email')
        new_pwd = request.form.get('password')
        if new_pwd: user.password_hash = generate_password_hash(new_pwd, method='pbkdf2:sha256')
        user.address = request.form.get('address')
        user.preferred_payment = request.form.get('preferred_payment')
        db.session.commit()
        session['user_name'] = user.username
        log_action(session['user_id'], "Profile Updated", "User updated personal or billing details.")
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

@app.route('/audit')
@login_required
@role_required('Manager')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit.html', logs=logs)

# ==========================================
# GLOBAL ERROR HANDLING (UI PRESERVED)
# ==========================================
@app.errorhandler(404)
def not_found_error(error):
    flash("404 Error: The page you are looking for does not exist.", "warning")
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback() 
    flash("500 Error: An internal server error occurred. Please try again later.", "danger")
    return redirect(url_for('dashboard'))

@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    db.session.rollback() # Protects database from locking up
    
    # If a JS API call fails, send a clean JSON response
    if request.path.startswith('/api/'):
        return jsonify({"message": "A system error occurred. Please check your inputs."}), 500
    
    # If a standard page load fails, redirect cleanly with an alert
    flash("System Alert: An unexpected error was safely caught and resolved.", "danger")
    return redirect(url_for('dashboard'))

# ==========================================
# API ENDPOINTS 
# ==========================================
@app.route('/api/seed', methods=['POST'])
def seed_data():
    if User.query.first(): return jsonify({"message": "Data exists!"}), 200
    
    admin = User(username="Admin Manager", email="admin@test.com", password_hash=generate_password_hash("password", method='pbkdf2:sha256'), role="Manager")
    staff = User(username="Warehouse Staff", email="staff@test.com", password_hash=generate_password_hash("password", method='pbkdf2:sha256'), role="Warehouse_Staff")
    
    db.session.add_all([
        admin, staff,
        Location(name="Steel Supplier Inc.", type="Vendor"),
        Location(name="Main Warehouse", type="Internal"),
        Location(name="Acme Manufacturing", type="Customer"),
        Location(name="Virtual Adjustment Log", type="Inventory Loss"),
        ProductCategory(name="Raw Materials")
    ])
    db.session.commit()
    db.session.add(Product(name="Steel Rods", sku="SR-001", category_id=1, unit_of_measure="kg"))
    db.session.commit()
    return jsonify({"message": "Dummy data created!"}), 201

@app.route('/api/receipts', methods=['POST'])
def process_receipt():
    data = request.get_json()
    op = InventoryOperation(document_type='Receipt', status='Done', source_location_id=data['vendor_id'], dest_location_id=data['warehouse_id'], created_by=data['user_id'])
    db.session.add(op)
    db.session.flush() 
    for item in data['items']:
        db.session.add(OperationLine(operation_id=op.id, product_id=item['product_id'], quantity=item['quantity']))
        db.session.add(StockLedger(product_id=item['product_id'], location_id=data['warehouse_id'], operation_id=op.id, quantity_change=item['quantity']))
    db.session.commit()
    log_action(data['user_id'], "Receipt Processed", f"Processed REC-{op.id} at warehouse ID {data['warehouse_id']}.")
    return jsonify({"message": "Receipt validated!"}), 201

@app.route('/api/deliveries', methods=['POST'])
def process_delivery():
    data = request.get_json()
    op = InventoryOperation(document_type='Delivery', status='Done', source_location_id=data['warehouse_id'], dest_location_id=data['customer_id'], created_by=data['user_id'])
    db.session.add(op)
    db.session.flush()
    for item in data['items']:
        db.session.add(OperationLine(operation_id=op.id, product_id=item['product_id'], quantity=item['quantity']))
        db.session.add(StockLedger(product_id=item['product_id'], location_id=data['warehouse_id'], operation_id=op.id, quantity_change=-float(item['quantity'])))
    db.session.commit()
    log_action(data['user_id'], "Delivery Processed", f"Processed DEL-{op.id} to customer ID {data['customer_id']}.")
    return jsonify({"message": "Delivery validated!"}), 201

@app.route('/api/adjustments', methods=['POST'])
def process_adjustment():
    data = request.get_json()
    product_id, warehouse_id, counted_qty = int(data['product_id']), int(data['warehouse_id']), float(data['counted_quantity'])
    current_stock = db.session.query(func.sum(StockLedger.quantity_change)).filter_by(product_id=product_id, location_id=warehouse_id).scalar() or 0.0
    diff = counted_qty - current_stock
    if diff == 0: return jsonify({"message": "No adjustment needed."}), 200
    adj_loc = Location.query.filter_by(type='Inventory Loss').first()
    op = InventoryOperation(document_type='Adjustment', status='Done', source_location_id=warehouse_id if diff < 0 else adj_loc.id, dest_location_id=adj_loc.id if diff < 0 else warehouse_id, created_by=data['user_id'])
    db.session.add(op)
    db.session.flush()
    db.session.add(OperationLine(operation_id=op.id, product_id=product_id, quantity=abs(diff)))
    db.session.add(StockLedger(product_id=product_id, location_id=warehouse_id, operation_id=op.id, quantity_change=diff))
    db.session.commit()
    log_action(data['user_id'], "Stock Adjusted", f"Adjusted ADJ-{op.id} for Product {product_id} by {diff} units.")
    return jsonify({"message": "Adjustment successful."}), 201

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', debug=True, port=5000)