import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "nia_secret_key"

# ===== CONFIG =====
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# ===== DATABASE CONNECTION =====
db = mysql.connector.connect(
    host="localhost",
    user="nia_user",
    password="Nia@1234!",
    database="nia_store"
)
cursor = db.cursor(dictionary=True)

# ===== EMAIL CONFIG =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'abinbiresimon@gmail.com'   # change this
app.config['MAIL_PASSWORD'] = 'si834on56'  # change to your app password

mail = Mail(app)

# ===== HELPERS =====
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    
    cart = session.get("cart", [])
    # check if item already in cart
    for item in cart:
        if item["id"] == product_id:
            item["quantity"] += 1
            break
    else:
        product["quantity"] = 1
        cart.append(product)
    
    session["cart"] = cart
    flash(f"{product['name']} added to cart!", "success")
    return redirect(url_for("show_products"))

@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum(float(item["price"]) * item["quantity"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", [])
    cart = [item for item in cart if item["id"] != product_id]
    session["cart"] = cart
    flash("Item removed from cart!", "info")
    return redirect(url_for("cart"))

@app.route("/clear_cart")
def clear_cart():
    session.pop("cart", None)
    flash("Cart cleared!", "info")
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
                recipients=['your_email@gmail.com'],
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
    app.run(debug=True)
