# app.py
import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from passlib.hash import bcrypt
from datetime import date
from dotenv import load_dotenv
from database import Base, engine, get_db
from models import User, DailyUsage
from recipes import generate_recipes
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session
from openai import OpenAI

# ✅ Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# ✅ Initialize OpenAI client using the API key from .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


load_dotenv()

app = Flask(__name__, static_folder=None)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
CORS(app, supports_credentials=True, origins=os.getenv("CORS_ORIGINS", "*"))
import os, requests
from flask import jsonify, request

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

@app.route("/api/checkout", methods=["POST"])
def create_checkout():
    data = request.get_json()
    email = data.get("email")  # user email
    amount = data.get("amount", 50000)  # amount in kobo (50000 = 500 NGN)

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "amount": amount
    }

    response = requests.post("https://api.paystack.co/transaction/initialize",
                             headers=headers, json=payload)
    res_data = response.json()

    if res_data.get("status"):
        return jsonify({"checkout_url": res_data["data"]["authorization_url"]})
    else:
        return jsonify({"error": res_data.get("message", "Payment init failed")}), 400
@app.route("/api/webhook/paystack", methods=["POST"])
def paystack_webhook():
    payload = request.get_json()
    event = payload.get("event")

    if event == "charge.success":
        email = payload["data"]["customer"]["email"]
        # ✅ Mark this user as premium in DB
        # e.g. User.query.filter_by(email=email).update({"is_premium": True})
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "ignored"}), 200


# Create tables if missing
Base.metadata.create_all(bind=engine)

DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))
PAYWALL_AMOUNT_KES = os.getenv("PAYWALL_AMOUNT_KES", "50")
INTASEND_CHECKOUT_BASE = os.getenv("INTASEND_CHECKOUT_BASE", "https://pay.intasend.com/checkout")

def _get_db_session():
    return next(get_db())

@app.post("/api/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    db = _get_db_session()
    try:
        user = User(username=username, password_hash=bcrypt.hash(password))
        db.add(user)
        db.commit()
        return jsonify({"ok": True}), 200
    except IntegrityError:
        db.rollback()
        return jsonify({"error": "username already exists"}), 409
    finally:
        db.close()

@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    db = _get_db_session()
    try:
        stmt = select(User).filter_by(username=username)
        user = db.execute(stmt).scalar_one_or_none()
        if not user or not bcrypt.verify(password, user.password_hash):
            return jsonify({"error": "invalid credentials"}), 401

        # set session
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        return jsonify({"ok": True, "username": user.username}), 200
    finally:
        db.close()

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"user": None}), 200
    uid = session["user_id"]
    db = _get_db_session()
    try:
        stmt = select(User).filter_by(id=uid)
        user = db.execute(stmt).scalar_one_or_none()
        if not user:
            return jsonify({"user": None}), 200

        # today's usage
        today = date.today()
        stmt2 = select(DailyUsage).filter_by(user_id=uid, date=today)
        du = db.execute(stmt2).scalar_one_or_none()
        used = du.count if du else 0
        return jsonify({"user": user.username, "used_today": used, "limit": DAILY_LIMIT}), 200
    finally:
        db.close()

@app.post("/api/generate")
def api_generate():
    if "user_id" not in session:
        return jsonify({"error": "auth required"}), 401

    payload = request.get_json(silent=True) or {}
    ingredients = payload.get("ingredients", "")
    notes = payload.get("notes", "")
    limit_requested = int(payload.get("limit", 3))

    if not ingredients:
        return jsonify({"error": "no ingredients provided"}), 400

    uid = session["user_id"]
    db = _get_db_session()
    try:
        today = date.today()
        # get or create daily usage row
        stmt = select(DailyUsage).filter_by(user_id=uid, date=today)
        du = db.execute(stmt).scalar_one_or_none()
        if du and du.count >= DAILY_LIMIT:
            # user hit the daily limit -> return a checkout url payload
            # NOTE: Replace with real IntaSend checkout creation call in production.
            checkout_url = f"{INTASEND_CHECKOUT_BASE}?amount={PAYWALL_AMOUNT_KES}&ref={session.get('username')}"
            return jsonify({
                "error": "limit_reached",
                "message": "Daily limit reached. Complete payment to unlock more recipes.",
                "checkout_url": checkout_url,
                "amount": PAYWALL_AMOUNT_KES
            }), 402

        # call OpenAI to generate recipes (blocking)
        try:
            model_result = generate_recipes(ingredients, notes, limit_requested)
        except Exception as e:
            return jsonify({"error": f"recipe generation failed: {str(e)}"}), 500

        # increment usage
        if not du:
            du = DailyUsage(user_id=uid, date=today, count=1)
            db.add(du)
        else:
            du.count += 1
        db.commit()

        return jsonify({"recipes": model_result.get("recipes", []), "used_today": du.count, "limit": DAILY_LIMIT}), 200
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    data = request.get_json()
    ingredients = data.get("ingredients", "")

    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful recipe assistant."},
            {"role": "user", "content": f"Suggest 3 recipes using: {ingredients}"}
        ],
        max_tokens=300
    )

    recipes = response.choices[0].message.content.strip()
    return jsonify({"recipes": recipes})
