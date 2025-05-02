import os
import psycopg2
from flask import Flask, jsonify, request
from dotenv import load_dotenv

if os.environ.get("RAILWAY_ENVIRONMENT") is None:
    load_dotenv()

app = Flask(__name__)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL не задана.")
    return psycopg2.connect(db_url)

@app.route('/products', methods=['GET'])
def get_products():
    category_id = request.args.get('ctg_id')
    currency = request.args.get('curr', 'EUR')
    lang = request.args.get('lang', 'ua')
    if lang not in ['ua', 'en']:
        lang = 'ua'

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            SELECT 
                p.id AS product_id,
                pn.name AS product_name,
                c.name AS category_name,
                pl.price,
                pl.stock_quantity,
                pl.currency_id
            FROM products p
            INNER JOIN product_names pn ON p.id = pn.product_id
            INNER JOIN categories c ON p.category_id = c.id
            INNER JOIN price_list pl ON p.id = pl.product_id AND pl.currency_id = %s
            WHERE pn.lang_id = %s
        """

        params = [currency, lang]

        if category_id:
            sql += " AND c.id = %s"
            params.append(category_id)

        sql += " ORDER BY c.name, p.id"

        cur.execute(sql, params)
        rows = cur.fetchall()

        products = []
        for row in rows:
            products.append({
                'product_id': row[0],
                'product_name': row[1],
                'category_name': row[2],
                'price': float(row[3]),
                'stock_quantity': row[4],
                'currency_id': row[5]
            })

        cur.close()
        conn.close()

        if products:
            return jsonify(products), 200
        else:
            return jsonify({"message": "No products found"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/languages")
def get_languages():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, code, title FROM public.languages ORDER BY id;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = [
            {"id": row[0], "code": row[1].strip(), "title": row[2]}
            for row in rows
        ]
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    
    if not data or 'customer_id' not in data or 'items' not in data:
        return jsonify({"error": "Missing data"}), 400
    
    customer_id = data['customer_id']
    items = data['items']

    if not items or not isinstance(items, list):
        return jsonify({"error": "Items list is required"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO orders (customer_id, invoice_date) VALUES (%s, CURRENT_TIMESTAMP) RETURNING order_id;",
            (customer_id,)
        )
        order_id = cursor.fetchone()[0]
        
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            price = item.get('price')
            
            if not all([product_id, quantity, price]):
                continue

            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s);",
                (order_id, product_id, quantity, price)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Order created successfully", "order_id": order_id}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.order_id, o.customer_id, o.invoice_date, 
                   oi.order_item_id, oi.product_id, oi.quantity, oi.price,
                   pn.name as product_name
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN product_names pn ON oi.product_id = pn.product_id AND pn.lang_id = 'ua';
        """)
        
        orders = cursor.fetchall()
        
        if orders:
            orders_list = []
            current_order = None
            for order in orders:
                order_id, customer_id, invoice_date, order_item_id, product_id, quantity, price, product_name = order
                if current_order != order_id:
                    if current_order is not None:
                        orders_list.append(current_order_data)
                    current_order_data = {
                        "order_id": order_id,
                        "customer_id": customer_id,
                        "invoice_date": invoice_date,
                        "items": []
                    }
                    current_order = order_id
                
                current_order_data["items"].append({
                    "order_item_id": order_item_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity": quantity,
                    "price": price
                })
            
            orders_list.append(current_order_data)
            cursor.close()
            conn.close()
            return jsonify({"orders": orders_list}), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"message": "No orders found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))