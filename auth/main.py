from flask import Flask, request, jsonify
import secrets
import time

app = Flask(__name__)

# Простая "база" пользователей
USERS = {"admin": "1234"}

# Токены: token -> (username, expiry)
TOKENS = {}
TOKEN_TTL = 300  # 5 минут


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = secrets.token_hex(16)
    TOKENS[token] = (username, time.time() + TOKEN_TTL)

    return jsonify({"token": token})


@app.route('/protected', methods=['GET'])
def protected():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({"error": "Authorization header missing"}), 401

    token = auth.split(' ')[1]
    user_data = TOKENS.get(token)

    if not user_data:
        return jsonify({"error": "Invalid or expired token"}), 401

    username, expiry = user_data
    if time.time() > expiry:
        del TOKENS[token]
        return jsonify({"error": "Token expired"}), 401

    return jsonify({"message": f"Hello, {username}! Access granted."})


# 🔹 Новый контроллер: /pf — возвращает GET-параметры
@app.route('/pf', methods=['GET'])
def pf():
    params = request.args.to_dict()
    return jsonify(params)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
