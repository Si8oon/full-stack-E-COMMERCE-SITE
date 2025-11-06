import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nia_secret_key")

# ===== CONFIG =====
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# ===== DATABASE CONFIG =====
def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        # Render provides DATABASE_URL environment variable
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # For production (Render)
            conn = psycopg2.connect(database_url, sslmode='require')
        else:
            # For local development (SQLite as fallback)
            import sqlite3
            conn = sqlite3.connect('local.db')
            conn.row_factory = sqlite3.Row
            
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

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
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed", "error")
        return render_template("products.html", products=[])
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        
        # Convert to list of dictionaries for PostgreSQL
        columns = [desc[0] for desc in cursor.description]
        products_list = []
        for row in products:
            products_list.append(dict(zip(columns, row)))
            
        return render_template("products.html", products=products_list)
    except Exception as e:
        flash(f"Error loading products: {e}", "error")
        return render_template("products.html", products=[])
    finally:
        conn.close()

# ===== CART SYSTEM =====
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed", "error")
        return redirect(url_for("show_products"))
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product_row = cursor.fetchone()
        
        if not product_row:
            flash("Product not found!", "error")
            return redirect(url_for("show_products"))
        
        # Convert to dictionary
        columns = [desc[0] for desc in cursor.description]
        product = dict(zip(columns, product_row))

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
        flash(f"Error adding to cart: {e}", "error")
        return redirect(url_for("show_products"))
    finally:
        conn.close()

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

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (name, email, subject, message) VALUES (%s, %s, %s, %s)",
                    (name, email, subject, message)
                )
                conn.commit()
            except Exception as e:
                print(f"Database error: {e}")
            finally:
                conn.close()

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
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category = request.form["category"]
        file = request.files["image"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"images/{filename}"

            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO products (name, price, image, category) VALUES (%s, %s, %s, %s)",
                        (name, price, image_path, category)
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Database error: {e}")
                finally:
                    conn.close()

        return redirect(url_for("admin"))

    conn = get_db_connection()
    products = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            product_rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = [desc[0] for desc in cursor.description]
            for row in product_rows:
                products.append(dict(zip(columns, row)))
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    return render_template("admin.html", products=products)

@app.route("/delete_product/<int:id>")
def delete_product(id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = %s", (id,))
            conn.commit()
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    return redirect(url_for("admin"))

# ===== RUN APP =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)