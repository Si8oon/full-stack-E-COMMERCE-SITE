import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# ===== LOAD ENV =====
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nia_secret_key")

# ===== CONFIG =====
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DATABASE'] = 'database.db'

# ===== DATABASE SETUP =====
def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            stock_quantity INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create messages table for contact form
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if doesn't exist
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        default_password = generate_password_hash("admin123")
        cursor.execute('''
            INSERT INTO users (email, password_hash, full_name, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ("admin@niastore.com", default_password, "Store Admin", 1))
        print("✅ Default admin user created: admin@niastore.com / admin123")
    
    # Check if products table is empty and add sample data
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_products = [
            ('Nike Air Max', 299.99, 'images/sneaker1.jpg', 'sneakers', 'Comfortable running shoes', 10),
            ('Cotton T-Shirt', 49.99, 'images/shirt1.jpg', 'shirts', 'Premium cotton t-shirt', 25),
            ('Denim Jeans', 199.99, 'images/jeans1.jpg', 'trousers', 'Classic blue denim', 15),
            ('Summer Shorts', 89.99, 'images/shorts1.jpg', 'shorts', 'Lightweight summer shorts', 20),
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, price, image, category, description, stock_quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        print("✅ Sample products added to database")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ===== DATABASE HELPERS =====
def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# ===== AUTHENTICATION HELPERS =====
def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# ===== EMAIL CONFIG =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# ===== HELPERS =====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_cart_total():
    total = 0
    if 'cart' in session:
        for item in session['cart']:
            total += float(item['price']) * item['quantity']
    return round(total, 2)

# ===== AUTH ROUTES =====
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
            session['is_admin'] = bool(user['is_admin'])
            
            flash(f"Welcome back, {user['full_name'] or user['email']}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        full_name = request.form["full_name"]
        
        db = get_db()
        
        # Check if user already exists
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("Email already registered. Please login.", "error")
            db.close()
            return redirect(url_for('login'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
            (email, password_hash, full_name)
        )
        db.commit()
        db.close()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# ===== ROUTES =====
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def show_products():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    return render_template("products.html", products=products)

# ===== CART SYSTEM =====
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    db.close()
    
    if not product:
        flash("Product not found!", "error")
        return redirect(url_for("show_products"))

    cart = session.get('cart', [])
    found = False

    for item in cart:
        if item['id'] == product['id']:
            item['quantity'] += 1
            found = True
            break

    if not found:
        cart.append({
            'id': product['id'],
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        })

    session['cart'] = cart
    flash(f"{product['name']} added to cart!", "success")
    return redirect(url_for("show_products"))

@app.route("/cart")
def cart():
    cart = session.get('cart', [])
    total = get_cart_total()
    return render_template("cart.html", cart=cart, total=total)

@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    new_cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = new_cart
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))

@app.route("/clear_cart")
def clear_cart():
    session.pop('cart', None)
    flash("Cart cleared.", "info")
    return redirect(url_for("cart"))

# ===== CONTACT PAGE =====
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        db = get_db()
        db.execute("INSERT INTO messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
                  (name, email, subject, message))
        db.commit()
        db.close()

        try:
            msg = Message(
                subject=f"New Contact Message: {subject}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[os.getenv("ADMIN_EMAIL", "your_email@gmail.com")],
                body=f"From: {name} <{email}>\n\n{message}"
            )
            mail.send(msg)
        except Exception as e:
            print("Email send failed:", e)

        flash("Message sent successfully!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

# ===== ADMIN DASHBOARD =====
@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    db = get_db()
    
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category = request.form["category"]
        description = request.form.get("description", "")
        stock_quantity = request.form.get("stock_quantity", 0)
        file = request.files["image"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_path = f"images/{filename}"

            db.execute('''INSERT INTO products 
                         (name, price, image, category, description, stock_quantity) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (name, price, image_path, category, description, stock_quantity))
            db.commit()
            flash("Product added successfully!", "success")
        else:
            flash("Please select a valid image file.", "error")

    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    return render_template("admin.html", products=products)

@app.route("/delete_product/<int:id>")
@admin_required
def delete_product(id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (id,))
    db.commit()
    db.close()
    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin"))

# ===== USER PROFILE =====
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


#checkooooooout hhahahahahh#
# ===== CHECKOUT ROUTE =====
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get('cart', [])
    total = get_cart_total()

    if not cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    if request.method == "POST":
        user_name = request.form["user_name"]
        phone = request.form["phone"]
        address = request.form["address"]
        momo_reference = request.form.get("momo_reference", "")

        db = get_db()
        db.execute('''
            INSERT INTO orders (user_name, phone, address, momo_reference, total)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_name, phone, address, momo_reference, total))
        db.commit()
        db.close()

        session.pop('cart', None)
        flash("Order placed successfully! Our team will confirm your MoMo payment soon.", "success")
        return redirect(url_for("home"))

    return render_template("checkout.html", cart=cart, total=total)





# ===== RUN APP =====
if __name__ == "__main__":
    # Initialize database when app starts
    print("🔄 Initializing database...")
    init_db()
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)