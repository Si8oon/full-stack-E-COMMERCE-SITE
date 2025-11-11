import sqlite3
import os

def setup_database():
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect('database.db')
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
    
    # Insert sample products
    sample_products = [
        ('Nike Air Max', 299.99, 'images/sneaker1.jpg', 'sneakers', 'Comfortable running shoes', 10),
        ('Cotton T-Shirt', 49.99, 'images/shirt1.jpg', 'shirts', 'Premium cotton t-shirt', 25),
        ('Denim Jeans', 199.99, 'images/jeans1.jpg', 'trousers', 'Classic blue denim', 15),
        ('Summer Shorts', 89.99, 'images/shorts1.jpg', 'shorts', 'Lightweight summer shorts', 20),
        ('Jordan Sneakers', 399.99, 'images/sneaker2.jpg', 'sneakers', 'Limited edition', 5),
        ('Polo Shirt', 79.99, 'images/shirt2.jpg', 'shirts', 'Classic polo', 18),
    ]
    
    cursor.executemany('''
        INSERT INTO products (name, price, image, category, description, stock_quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_products)


    # ===== Add to init_db() =====
# Create orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        momo_reference TEXT,
        total REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')

    
    conn.commit()
    conn.close()
    print("✅ Database setup completed!")
    print("✅ Tables created: products, messages")
    print("✅ Sample products added")

if __name__ == "__main__":
    setup_database()