import os
import psycopg2
from flask import Flask, jsonify
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

@app.route("/languages")
def get_languages():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, code, title FROM public.languages ORDER BY id;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify([
            {"id": row[0], "code": row[1].strip(), "title": row[2]}
            for row in rows
        ])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Запуск в локальной среде
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
