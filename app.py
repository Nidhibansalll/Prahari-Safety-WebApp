import os
import re
import time
import sqlite3
import requests
from flask import Flask, request, jsonify, send_from_directory, g
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_cors import CORS

from config import Config, BASE_DIR
from sms import send_sms

app = Flask(__name__)
app.config.from_object(Config)

DB_PATH = "/tmp/prahari.db" if os.getenv("VERCEL") else os.path.join(BASE_DIR, "prahari.db")


def get_db():
    if "db_conn" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db_conn = conn
    return g.db_conn


def init_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            gender TEXT NOT NULL,
            dob TEXT NOT NULL,
            pincode TEXT NOT NULL,
            is_abled INTEGER DEFAULT 0,
            pin_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            relation TEXT DEFAULT 'Other',
            is_primary INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sos_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            latitude REAL,
            longitude REAL,
            transcript TEXT,
            sms_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


init_sqlite()

bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app, origins="*")


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "prahari-v3 (1).html")


@app.route("/logo.png")
def logo():
    return send_from_directory(BASE_DIR, "logo.png")


@app.route("/chat.js")
def chat_js():
    return send_from_directory(BASE_DIR, "chat.js")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "sms_provider": app.config["SMS_PROVIDER"],
        "gemini_model": app.config["GEMINI_MODEL"]
    }), 200


def clean_phone(raw) -> str:
    num = re.sub(r"\D", "", str(raw or ""))
    if len(num) == 12 and num.startswith("91"):
        num = num[2:]
    elif len(num) == 11 and num.startswith("0"):
        num = num[1:]
    return num if re.fullmatch(r"\d{10}", num) else ""


def sms(numbers, message):
    return send_sms(app.config, numbers, message)


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    required = ["full_name", "phone_number", "gender", "date_of_birth", "area_pin_code", "login_pin"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    phone = str(data["phone_number"]).strip()
    pin = str(data["login_pin"]).strip()

    if not re.fullmatch(r"\d{10}", phone):
        return jsonify({"error": "Phone must be exactly 10 digits"}), 400
    if not re.fullmatch(r"\d{4,}", pin):
        return jsonify({"error": "PIN must be at least 4 digits"}), 400
    if data["gender"] not in ("Male", "Female", "Other"):
        return jsonify({"error": "Gender must be Male, Female or Other"}), 400
    if not re.fullmatch(r"\d{6}", str(data["area_pin_code"]).strip()):
        return jsonify({"error": "Area PIN code must be 6 digits"}), 400

    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE phone_number = ?", (phone,)).fetchone():
        return jsonify({"error": "Phone number already registered"}), 409

    hashed_pin = bcrypt.generate_password_hash(pin).decode("utf-8")
    cur = conn.execute(
        "INSERT INTO users (full_name, phone_number, gender, dob, pincode, is_abled, pin_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["full_name"], phone, data["gender"], data["date_of_birth"],
         str(data["area_pin_code"]).strip(), int(bool(data.get("is_specially_abled", False))), hashed_pin)
    )
    conn.commit()
    user_id = cur.lastrowid

    token = create_access_token(identity=str(user_id))
    return jsonify({
        "message": "Account created successfully!",
        "token": token,
        "user": {
            "id": user_id,
            "full_name": data["full_name"],
            "phone_number": phone,
            "gender": data["gender"],
            "is_specially_abled": bool(data.get("is_specially_abled", False)),
        }
    }), 201


@app.route("/api/auth/signin", methods=["POST"])
def signin():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone_number", "")).strip()
    pin = str(data.get("login_pin", "")).strip()

    if not phone or not pin:
        return jsonify({"error": "Phone number and PIN are required"}), 400

    user = get_db().execute("SELECT * FROM users WHERE phone_number = ?", (phone,)).fetchone()
    if not user:
        return jsonify({"error": "No account found with this phone number"}), 404
    if not bcrypt.check_password_hash(user["pin_hash"], pin):
        return jsonify({"error": "Incorrect PIN. Try again."}), 401

    token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "message": "Login successful!",
        "token": token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "phone_number": user["phone_number"],
            "gender": user["gender"],
            "is_specially_abled": bool(user["is_abled"])
        }
    }), 200


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_me():
    user = get_db().execute(
        "SELECT id, full_name, phone_number, gender, dob AS date_of_birth, pincode AS area_pin_code, is_abled AS is_specially_abled, created_at FROM users WHERE id = ?",
        (get_jwt_identity(),)
    ).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    res = dict(user)
    res["is_specially_abled"] = bool(res["is_specially_abled"])
    return jsonify(res), 200


@app.route("/api/auth/change-pin", methods=["PUT"])
@jwt_required()
def change_pin():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    old_pin = str(data.get("old_pin", "")).strip()
    new_pin = str(data.get("new_pin", "")).strip()

    if not old_pin or not new_pin or len(new_pin) < 4:
        return jsonify({"error": "Valid old and new PIN (4+ chars) required"}), 400

    conn = get_db()
    row = conn.execute("SELECT pin_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or not bcrypt.check_password_hash(row["pin_hash"], old_pin):
        return jsonify({"error": "Old PIN is incorrect"}), 401

    new_hashed = bcrypt.generate_password_hash(new_pin).decode("utf-8")
    conn.execute("UPDATE users SET pin_hash = ? WHERE id = ?", (new_hashed, user_id))
    conn.commit()
    return jsonify({"message": "PIN updated successfully!"}), 200


MAX_CONTACTS = 4


@app.route("/api/contacts", methods=["GET"])
@jwt_required()
def get_contacts():
    rows = get_db().execute(
        "SELECT id, name, phone, relation, is_primary FROM contacts WHERE user_id = ? ORDER BY is_primary DESC, id ASC",
        (get_jwt_identity(),)
    ).fetchall()
    return jsonify([{**dict(r), "is_primary": bool(r["is_primary"])} for r in rows]), 200


@app.route("/api/contacts", methods=["POST"])
@jwt_required()
def add_contact():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = clean_phone(data.get("phone"))
    relation = str(data.get("relation") or "Other").strip()[:50]
    primary = int(bool(data.get("is_primary")))

    if not name or not phone:
        return jsonify({"error": "Name and valid 10-digit phone required"}), 400

    conn = get_db()
    cnt = conn.execute("SELECT COUNT(*) AS cnt FROM contacts WHERE user_id = ?", (user_id,)).fetchone()["cnt"]
    if cnt >= MAX_CONTACTS:
        return jsonify({"error": f"Maximum {MAX_CONTACTS} contacts allowed"}), 400

    if conn.execute("SELECT id FROM contacts WHERE user_id = ? AND phone = ?", (user_id, phone)).fetchone():
        return jsonify({"error": "This number is already in your contacts"}), 409

    if primary:
        conn.execute("UPDATE contacts SET is_primary = 0 WHERE user_id = ?", (user_id,))

    cur = conn.execute(
        "INSERT INTO contacts (user_id, name, phone, relation, is_primary) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, phone, relation, primary)
    )
    conn.commit()
    new_id = cur.lastrowid
    user = conn.execute("SELECT full_name FROM users WHERE id = ?", (user_id,)).fetchone()

    sms_result = {"success": False, "error": "Notification disabled"}
    if app.config["NOTIFY_ON_CONTACT_ADD"]:
        user_name = user["full_name"] if user else "A Prahari user"
        sms_result = sms([phone], (
            f"Hi {name}! {user_name} has added you as an emergency contact "
            f"in the Prahari Safety App. - Team Prahari"
        ))

    return jsonify({
        "message": "Contact saved!",
        "id": new_id,
        "sms_sent": sms_result["success"],
        "sms_info": "Alert delivered!" if sms_result["success"] else sms_result.get("error"),
    }), 201


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@jwt_required()
def delete_contact(contact_id):
    conn = get_db()
    cur = conn.execute("DELETE FROM contacts WHERE id = ? AND user_id = ?", (contact_id, get_jwt_identity()))
    conn.commit()
    if not cur.rowcount:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"message": "Contact deleted!"}), 200


@app.route("/api/sos/trigger", methods=["POST"])
@jwt_required()
def sos_trigger():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    transcript = str(data.get("transcript") or "").strip()
    ps_name = str(data.get("ps_name") or "").strip()

    try:
        latitude, longitude = float(latitude), float(longitude)
        location_link = f"https://maps.google.com/?q={latitude},{longitude}"
    except (TypeError, ValueError):
        latitude = longitude = None
        location_link = "Location unavailable"

    conn = get_db()
    user = conn.execute("SELECT full_name, phone_number FROM users WHERE id = ?", (user_id,)).fetchone()
    contacts = conn.execute(
        "SELECT name, phone FROM contacts WHERE user_id = ? ORDER BY is_primary DESC",
        (user_id,)
    ).fetchall()

    if not contacts:
        return jsonify({"error": "No emergency contacts saved. Add contacts first."}), 400

    phone_numbers = list(dict.fromkeys(n for n in (clean_phone(c["phone"]) for c in contacts) if n))
    user_name = user["full_name"] if user else "Prahari User"
    user_phone = user["phone_number"] if user else ""

    message = f"SOS ALERT! {user_name} ({user_phone}) NEEDS HELP NOW!\nLocation: {location_link}"
    if ps_name:
        message += f"\nPS: {ps_name}"
    if transcript:
        message += f'\nVoice: "{transcript[:60]}"'
    message += "\n- Prahari Safety App"

    result = sms(phone_numbers, message)

    conn.execute(
        "INSERT INTO sos_logs (user_id, latitude, longitude, transcript, sms_sent) VALUES (?, ?, ?, ?, ?)",
        (user_id, latitude, longitude, transcript, int(bool(result["success"])))
    )
    conn.commit()

    if result["success"]:
        return jsonify({
            "message": f"SOS alert sent to {result['sent']} contact(s)!",
            "contacts_alerted": result["sent"],
            "location": location_link,
        }), 200
    return jsonify({"error": "Alert sending failed", "details": result["error"]}), 502


@app.route("/api/sos/cancel", methods=["POST"])
@jwt_required()
def sos_cancel():
    user_id = get_jwt_identity()
    conn = get_db()
    user = conn.execute("SELECT full_name FROM users WHERE id = ?", (user_id,)).fetchone()
    contacts = conn.execute("SELECT phone FROM contacts WHERE user_id = ?", (user_id,)).fetchall()
    phone_numbers = list(dict.fromkeys(n for n in (clean_phone(c["phone"]) for c in contacts) if n))
    user_name = user["full_name"] if user else "Prahari User"

    notified = 0
    if phone_numbers:
        result = sms(phone_numbers, f"UPDATE: {user_name} has CANCELLED the SOS alert. They are safe. - Prahari Safety App")
        notified = result["sent"]

    return jsonify({"message": "SOS cancelled, contacts notified", "contacts_notified": notified}), 200


CHAT_SYSTEM = (
    "You are Prahari Assistant, a calm and helpful safety chatbot inside the Prahari "
    "women/personal safety app (India). Give short, practical safety tips, explain app "
    "features (5-second SOS buffer, emergency contacts, voice trigger, nearest police station), "
    "and in danger always tell the user to press SOS or call 112 (emergency), 100 (police), "
    "1091 (women helpline). Keep answers under 120 words."
)


@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    key = app.config["GEMINI_API_KEY"]
    if not key:
        return jsonify({"error": "Chatbot not configured"}), 503

    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()[:1000]
    history = data.get("history") or []
    if not message:
        return jsonify({"error": "Message required"}), 400

    contents = []
    for h in history[-10:]:
        role = "model" if h.get("role") == "model" else "user"
        contents.append({"role": role, "parts": [{"text": str(h.get("text", ""))[:1000]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    candidate_models = list(dict.fromkeys([
        app.config["GEMINI_MODEL"],
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-2.5-flash-lite",
    ]))

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        payload = {"systemInstruction": {"parts": [{"text": CHAT_SYSTEM}]}, "contents": contents}
        for attempt in range(3):
            try:
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=25,
                )
                if r.status_code == 200:
                    reply = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return jsonify({"reply": reply, "model": model_name}), 200
                if r.status_code in (429, 503):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            except Exception:
                break

    return jsonify({
        "reply": "I'm experiencing high traffic right now. If this is an emergency, press SOS or dial 112 immediately."
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
