# database.py - SQLite Database Setup
import sqlite3

DB_NAME = "food_orders.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            phone        TEXT UNIQUE NOT NULL,
            email        TEXT,
            password     TEXT NOT NULL,
            points       INTEGER DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            price        INTEGER NOT NULL,
            emoji        TEXT,
            category     TEXT,
            description  TEXT,
            badge        TEXT,
            badge_class  TEXT,
            is_available INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id         TEXT UNIQUE NOT NULL,
            customer_id      INTEGER,
            customer_name    TEXT NOT NULL,
            customer_phone   TEXT NOT NULL,
            customer_address TEXT,
            subtotal         INTEGER NOT NULL,
            delivery_fee     INTEGER DEFAULT 0,
            taxes            INTEGER DEFAULT 0,
            total_amount     INTEGER NOT NULL,
            order_type       TEXT DEFAULT 'Dine-in',
            payment_method   TEXT DEFAULT 'Cash',
            points_earned    INTEGER DEFAULT 0,
            status           TEXT DEFAULT 'Placed',
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   TEXT NOT NULL,
            item_id    INTEGER NOT NULL,
            item_name  TEXT NOT NULL,
            item_price INTEGER NOT NULL,
            quantity   INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            rating        INTEGER NOT NULL,
            feedback      TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        menu_data = [
            ("Paneer Tikka",      180, "🧀", "Starters",    "Marinated paneer grilled to perfection",      "Veg",        "veg"),
            ("Chicken Wings",     220, "🍗", "Starters",    "Crispy spiced chicken wings with dip",        "Spicy",      ""),
            ("Veg Spring Rolls",  150, "🥢", "Starters",    "Crispy rolls filled with seasonal veggies",   "Veg",        "veg"),
            ("Soup of the Day",   120, "🍜", "Starters",    "Chef's special daily soup",                   None,         ""),
            ("Butter Chicken",    320, "🍛", "Main Course", "Creamy tomato-based chicken curry",           "Bestseller", ""),
            ("Dal Makhani",       240, "🫘", "Main Course", "Slow-cooked black lentils in rich gravy",     "Veg",        "veg"),
            ("Veg Biryani",       260, "🍚", "Main Course", "Fragrant basmati rice with vegetables",       "Veg",        "veg"),
            ("Chicken Biryani",   340, "🍚", "Main Course", "Aromatic rice with tender chicken pieces",    "Bestseller", ""),
            ("Palak Paneer",      280, "🥬", "Main Course", "Fresh cottage cheese in spiced spinach gravy","Veg",        "veg"),
            ("Fish Curry",        360, "🐟", "Main Course", "Coastal-style tangy fish curry",              None,         ""),
            ("Garlic Naan",        60, "🫓", "Breads",      "Soft leavened bread with garlic butter",      "Veg",        "veg"),
            ("Tandoori Roti",      40, "🫓", "Breads",      "Whole wheat bread from clay oven",            "Veg",        "veg"),
            ("Lachha Paratha",     70, "🫓", "Breads",      "Flaky layered whole wheat flatbread",         "Veg",        "veg"),
            ("Chocolate Brownie", 120, "🍫", "Desserts",    "Warm fudgy brownie with vanilla ice cream",   None,         ""),
            ("Mango Kulfi",        90, "🍦", "Desserts",    "Traditional Indian ice cream with mango",     "Veg",        "veg"),
            ("Mango Lassi",        80, "🥭", "Drinks",      "Chilled yogurt drink with fresh mango",       "Veg",        "veg"),
            ("Fresh Lime Soda",    60, "🍋", "Drinks",      "Refreshing fizzy lime drink",                 "Veg",        "veg"),
            ("Cold Coffee",       100, "☕", "Drinks",      "Blended cold coffee with ice cream",          None,         ""),
        ]
        cursor.executemany('''
            INSERT INTO menu_items (name,price,emoji,category,description,badge,badge_class)
            VALUES (?,?,?,?,?,?,?)
        ''', menu_data)

    conn.commit()
    conn.close()
    print("✅ Database ready!")

if __name__ == "__main__":
    init_db()