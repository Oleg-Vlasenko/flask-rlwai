import os
import psycopg2
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Загружаем переменные из .env, только в локальной среде
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))