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
db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST", "localhost"),
    user=os.getenv("MYSQLUSER", "flaskuser"),
    password=os.getenv("MYSQLPASSWORD", "Flask@123!"),
    database=os.getenv("MYSQLDATABASE", "nia_store"),
    port=os.getenv("MYSQLPORT", 3306)
)
cursor = db.cursor(dictionary=True)

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
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("products.html", products=products)

# ===== CART SYSTEM =====
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
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

        cursor.execute(
            "INSERT INTO messages (name, email, subject, message) VALUES (%s, %s, %s, %s)",
            (name, email, subject, message)
        )
        db.commit()

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

            cursor.execute(
                "INSERT INTO products (name, price, image, category) VALUES (%s, %s, %s, %s)",
                (name, price, image_path, category)
            )
            db.commit()

        return redirect(url_for("admin"))

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("admin.html", products=products)

@app.route("/delete_product/<int:id>")
def delete_product(id):
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for("admin"))

# ===== RUN APP =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
