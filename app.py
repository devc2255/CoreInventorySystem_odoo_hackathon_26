import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) # Used for 'Name'
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Manager')

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

# --- AUTHENTICATION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTH ROUTES ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please log in.')
            return redirect(url_for('signup'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=name, email=email, password_hash=hashed_pw)
        
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
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- FRONTEND ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_products = Product.query.count()
    pending_receipts = InventoryOperation.query.filter_by(document_type='Receipt').filter(InventoryOperation.status != 'Done').count()
    pending_deliveries = InventoryOperation.query.filter_by(document_type='Delivery').filter(InventoryOperation.status != 'Done').count()
    return render_template('dashboard.html', total_products=total_products, pending_receipts=pending_receipts, pending_deliveries=pending_deliveries)

# Placeholder routes for the other sidebar features
@app.route('/products')
@login_required
def products(): return render_template('feature.html', title="Products")

@app.route('/receipts')
@login_required
def receipts(): return render_template('feature.html', title="Receipts")

@app.route('/deliveries')
@login_required
def deliveries(): return render_template('feature.html', title="Deliveries")

@app.route('/adjustments')
@login_required
def adjustments(): return render_template('feature.html', title="Stock Adjustments")

@app.route('/profile')
@login_required
def profile(): return render_template('feature.html', title="My Profile")


# --- INITIALIZATION ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True, port=5000)