# app.py - Shirke's Hotel Backend
from flask import Flask, render_template, request, jsonify
from database import init_db, get_connection
import random, string, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'shirkes_secret_2024'

# Ensure DB tables exist (runs on every cold start - needed for serverless platforms like Vercel)
init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data  = request.get_json()
    name  = data.get('name','').strip()
    phone = str(data.get('phone','')).strip()
    email = data.get('email','').strip()
    pwd   = data.get('password','').strip()
    if not name:
        return jsonify({'status':'error','message':'Name required!'}), 400
    if not phone or not phone.isdigit() or len(phone) != 10:
        return jsonify({'status':'error','message':'Valid 10-digit phone required!'}), 400
    if not pwd or len(pwd) < 4:
        return jsonify({'status':'error','message':'Password must be at least 4 characters!'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
        if cursor.fetchone():
            return jsonify({'status':'error','message':'Phone number already registered!'}), 400
        cursor.execute(
            "INSERT INTO customers (name, phone, email, password, points) VALUES (?,?,?,?,0)",
            (name, phone, email, hash_password(pwd))
        )
        conn.commit()
        customer_id = cursor.lastrowid
        return jsonify({'status':'success','message':'Registration successful!',
                        'customer':{'id':customer_id,'name':name,'phone':phone,'email':email,'points':0}})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data  = request.get_json()
    phone = str(data.get('phone','')).strip()
    pwd   = data.get('password','').strip()
    if not phone or not pwd:
        return jsonify({'status':'error','message':'Phone and password required!'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE phone = ? AND password = ?",
                   (phone, hash_password(pwd)))
    customer = cursor.fetchone()
    conn.close()
    if not customer:
        return jsonify({'status':'error','message':'Invalid phone or password!'}), 401
    return jsonify({'status':'success','message':'Login successful!',
                    'customer':{'id':customer['id'],'name':customer['name'],
                                'phone':customer['phone'],'email':customer['email'] or '',
                                'points':customer['points']}})

@app.route('/api/customer/<int:customer_id>/orders', methods=['GET'])
def customer_orders(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    orders = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','orders':[dict(o) for o in orders]})

@app.route('/api/customers', methods=['GET'])
def get_customers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, email, points, created_at FROM customers ORDER BY created_at DESC")
    customers = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','customers':[dict(c) for c in customers]})

@app.route('/api/customer/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
        if not cursor.fetchone():
            return jsonify({'status':'error','message':'Customer not found!'}), 404
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return jsonify({'status':'success','message':'Customer deleted successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/menu', methods=['GET'])
def get_menu():
    category = request.args.get('category', 'All')
    conn = get_connection()
    cursor = conn.cursor()
    if category == 'All':
        cursor.execute("SELECT * FROM menu_items WHERE is_available = 1")
    else:
        cursor.execute("SELECT * FROM menu_items WHERE category = ? AND is_available = 1", (category,))
    items = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','items':[{
        'id':i['id'],'name':i['name'],'price':i['price'],
        'emoji':i['emoji'],'category':i['category'],
        'description':i['description'],'badge':i['badge'],'badge_class':i['badge_class']
    } for i in items]})

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data.get('customer_name'):
        return jsonify({'status':'error','message':'Name required!'}), 400
    phone = str(data.get('customer_phone','')).strip()
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({'status':'error','message':'Valid 10-digit phone required!'}), 400
    cart_items = data.get('cart', [])
    if not cart_items:
        return jsonify({'status':'error','message':'Cart is empty!'}), 400
    timestamp   = datetime.now().strftime('%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    order_id    = f"MB{timestamp}{random_part}"
    subtotal    = sum(item['price'] * item['qty'] for item in cart_items)
    delivery_fee= data.get('delivery_fee', 0)
    discount    = data.get('discount', 0)
    total       = subtotal + delivery_fee - discount
    points_earned = total // 10
    customer_id = data.get('customer_id', None)
    payment     = data.get('payment_method', 'Cash')
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO orders
            (order_id, customer_id, customer_name, customer_phone, customer_address,
             subtotal, delivery_fee, taxes, total_amount, order_type, payment_method, points_earned, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'Placed')
        ''', (order_id, customer_id, data['customer_name'], phone,
              data.get('customer_address',''), subtotal, delivery_fee, 0,
              total, data.get('order_type','Dine-in'), payment, points_earned))
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, item_id, item_name, item_price, quantity)
                VALUES (?,?,?,?,?)
            ''', (order_id, item['id'], item['name'], item['price'], item['qty']))
        if customer_id:
            cursor.execute("UPDATE customers SET points = points + ? WHERE id = ?",
                           (points_earned, customer_id))
        conn.commit()
        return jsonify({'status':'success','order_id':order_id,'total':total,'points_earned':points_earned})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/orders', methods=['GET'])
def get_orders():
    search = request.args.get('search','').strip()
    conn = get_connection()
    cursor = conn.cursor()
    if search:
        cursor.execute("""
            SELECT * FROM orders
            WHERE customer_name LIKE ? OR customer_phone LIKE ? OR order_id LIKE ?
            ORDER BY created_at DESC LIMIT 50
        """, (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
    orders = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','orders':[dict(o) for o in orders]})

@app.route('/api/order/<order_id>', methods=['GET'])
def get_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'status':'error','message':'Order not found!'}), 404
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','order':dict(order),'items':[dict(i) for i in items]})

VALID_STATUSES = ['Placed', 'Preparing', 'Ready', 'Delivered', 'Cancelled']

@app.route('/api/order/<order_id>/status', methods=['PATCH'])
def update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    if new_status not in VALID_STATUSES:
        return jsonify({'status':'error','message':'Invalid status value!'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
        if not cursor.fetchone():
            return jsonify({'status':'error','message':'Order not found!'}), 404
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
        conn.commit()
        return jsonify({'status':'success','message':'Order status updated to '+new_status+'!','order_id':order_id,'new_status':new_status})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/order/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
        if not cursor.fetchone():
            return jsonify({'status':'error','message':'Order not found!'}), 404
        cursor.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        cursor.execute("DELETE FROM ratings WHERE order_id = ?", (order_id,))
        conn.commit()
        return jsonify({'status':'success','message':'Order deleted successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/rating', methods=['POST'])
def save_rating():
    data = request.get_json()
    if not data.get('order_id') or not data.get('rating'):
        return jsonify({'status':'error','message':'Order ID and rating required!'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO ratings (order_id, customer_name, rating, feedback, created_at)
            VALUES (?,?,?,?,CURRENT_TIMESTAMP)
        ''', (data['order_id'], data.get('customer_name','Anonymous'),
              data['rating'], data.get('feedback','')))
        conn.commit()
        return jsonify({'status':'success','message':'Thank you for your feedback! ⭐'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

@app.route('/api/ratings', methods=['GET'])
def get_ratings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ratings ORDER BY created_at DESC LIMIT 20")
    ratings = cursor.fetchall()
    conn.close()
    return jsonify({'status':'success','ratings':[dict(r) for r in ratings]})

@app.route('/api/rating/<order_id>', methods=['DELETE'])
def delete_rating(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT order_id FROM ratings WHERE order_id = ?", (order_id,))
        if not cursor.fetchone():
            return jsonify({'status':'error','message':'Rating not found!'}), 404
        cursor.execute("DELETE FROM ratings WHERE order_id = ?", (order_id,))
        conn.commit()
        return jsonify({'status':'success','message':'Rating deleted successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status':'error','message':str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    try:
        from pyngrok import ngrok
        init_db()
        public_url = ngrok.connect(5000)
        print("🍽️  Shirke's Hotel - Food Ordering System")
        print(f"🌐  Public Link: {public_url}")
    except:
        init_db()
        print("🍽️  Shirke's Hotel - Food Ordering System")
        print("🌐  Local: http://localhost:5000")
    app.run(port=5000, debug=False)