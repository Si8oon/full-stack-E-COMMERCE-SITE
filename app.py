import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nia_secret_key")

# ===== CONFIG =====
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# ===== DATABASE CONFIG =====
def get_db_connection():
    try:
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "flaskuser"),
            password=os.getenv("DB_PASSWORD", "Flask@123!"),
            database=os.getenv("DB_NAME", "nia_store"),
            port=os.getenv("DB_PORT", "3306")
        )
        return db
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database and create tables if they don't exist"""
    db = get_db_connection()
    if db:
        cursor = db.cursor(dictionary=True)
        try:
            # Create products table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                image VARCHAR(255),
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create messages table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject VARCHAR(255),
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Check if products table is empty and add sample data
            cursor.execute("SELECT COUNT(*) as count FROM products")
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute("""
                INSERT INTO products (name, price, image, category) VALUES
                ('Plain White Shirt', 80.00, 'images/T-shirts.jpeg', 'Shirts'),
                ('Cargo Pants', 150.00, 'images/cargo pants.jpeg', 'Trousers'),
                ('Denim Jeans', 170.00, 'images/Denim Jeans.jpeg', 'Trousers'),
                ('Athletic Shorts', 110.00, 'images/Athletic Shorts.jpeg', 'Shorts'),
                ('Wireless Headphones', 99.99, 'images/headphones.jpg', 'Electronics')
                """)
                print("✓ Sample products added")
            
            db.commit()
            print("✓ Database initialized successfully")
            
        except Exception as e:
            print(f"Database initialization error: {e}")
        finally:
            cursor.close()
            db.close()

# Initialize database on startup
init_database()

# ===== EMAIL CONFIG =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# ===== HELPERS =====
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_cart_total():
    total = 0
    if 'cart' in session:
        for item in session['cart']:
            total += float(item['price']) * item['quantity']
    return round(total, 2)

# ===== ROUTES =====
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def show_products():
    db = get_db_connection()
    if not db:
        flash("Database connection error", "error")
        return render_template("products.html", products=[])
    
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return render_template("products.html", products=products)
    except Exception as e:
        flash("Error loading products", "error")
        print(f"Error: {e}")
        return render_template("products.html", products=[])
    finally:
        cursor.close()
        db.close()

# ===== CART SYSTEM =====
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    db = get_db_connection()
    if not db:
        flash("Database connection error", "error")
        return redirect(url_for("show_products"))
    
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
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
    except Exception as e:
        flash("Error adding product to cart", "error")
        print(f"Error: {e}")
        return redirect(url_for("show_products"))
    finally:
        cursor.close()
        db.close()

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

        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            try:
                cursor.execute(
                    "INSERT INTO messages (name, email, subject, message) VALUES (%s, %s, %s, %s)",
                    (name, email, subject, message)
                )
                db.commit()
            except Exception as e:
                print(f"Error saving message: {e}")
            finally:
                cursor.close()
                db.close()

        # send email
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
def admin():
    db = get_db_connection()
    if not db:
        flash("Database connection error", "error")
        return render_template("admin.html", products=[])
    
    cursor = db.cursor(dictionary=True)
    
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category = request.form["category"]
        file = request.files["image"]

        image_path = "images/placeholder.jpg"
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"images/{filename}"

        try:
            cursor.execute(
                "INSERT INTO products (name, price, image, category) VALUES (%s, %s, %s, %s)",
                (name, price, image_path, category)
            )
            db.commit()
            flash("Product added successfully!", "success")
        except Exception as e:
            flash("Error adding product", "error")
            print(f"Error: {e}")

        return redirect(url_for("admin"))

    try:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return render_template("admin.html", products=products)
    except Exception as e:
        flash("Error loading products", "error")
        print(f"Error: {e}")
        return render_template("admin.html", products=[])
    finally:
        cursor.close()
        db.close()

@app.route("/delete_product/<int:id>")
def delete_product(id):
    db = get_db_connection()
    if not db:
        flash("Database connection error", "error")
        return redirect(url_for("admin"))
    
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        db.commit()
        flash("Product deleted successfully!", "success")
    except Exception as e:
        flash("Error deleting product", "error")
        print(f"Error: {e}")
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for("admin"))

# ===== RUN APP =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)