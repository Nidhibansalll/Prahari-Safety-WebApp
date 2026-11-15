import re
import time
import requests
import mysql.connector
from flask import Flask, request, jsonify, send_from_directory, g
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_cors import CORS

from config import Config, BASE_DIR
from models import get_user_by_phone, get_user_by_id, create_user, update_user_pin
from sms import send_sms

app = Flask(__name__)
app.config.from_object(Config)


# ─────────────────────────────────────────
# Database: one connection per request
# ─────────────────────────────────────────
class MySQL:
    def _conn(self):
        if "db_conn" not in g:
            g.db_conn = mysql.connector.connect(
                host=app.config["MYSQL_HOST"],
                user=app.config["MYSQL_USER"],
                password=app.config["MYSQL_PASSWORD"],
                database=app.config["MYSQL_DB"],
            )
        return g.db_conn

    def cursor(self):
        return self._conn().cursor(dictionary=True)

    def commit(self):
        return self._conn().commit()


db     = MySQL()
bcrypt = Bcrypt(app)
jwt    = JWTManager(app)
CORS(app, origins="*")


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db_conn", None)
    if conn is not None and conn.is_connected():
        conn.close()


# ─────────────────────────────────────────
# Serve the frontend
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
def clean_phone(raw) -> str:
    """Strip spaces/dashes/+91/91/0 prefix → 10-digit Indian mobile number, or ''."""
    num = re.sub(r"\D", "", str(raw or ""))
    if len(num) == 12 and num.startswith("91"):
        num = num[2:]
    elif len(num) == 11 and num.startswith("0"):
        num = num[1:]
    return num if re.fullmatch(r"\d{10}", num) else ""


def sms(numbers, message):
    return send_sms(app.config, numbers, message)


# ═════════════════════════════════════════
# AUTH ROUTES
# ═════════════════════════════════════════
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data received"}), 400

    required = ["full_name", "phone_number", "gender",
                "date_of_birth", "area_pin_code", "login_pin"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    phone = str(data["phone_number"]).strip()
    pin   = str(data["login_pin"]).strip()

    if not re.fullmatch(r"\d{10}", phone):
        return jsonify({"error": "Phone must be exactly 10 digits"}), 400
    if not re.fullmatch(r"\d{4,}", pin):
        return jsonify({"error": "PIN must be at least 4 digits"}), 400
    if data["gender"] not in ("Male", "Female", "Other"):
        return jsonify({"error": "Gender must be Male, Female or Other"}), 400
    if not re.fullmatch(r"\d{6}", str(data["area_pin_code"]).strip()):
        return jsonify({"error": "Area PIN code must be 6 digits"}), 400

    cur = db.cursor()
    if get_user_by_phone(cur, phone):
        cur.close()
        return jsonify({"error": "Phone number already registered"}), 409

    data["phone_number"] = phone
    hashed_pin = bcrypt.generate_password_hash(pin).decode("utf-8")
    user_id = create_user(cur, data, hashed_pin)
    db.commit()
    cur.close()

    token = create_access_token(identity=str(user_id))
    return jsonify({
        "message": "Account created successfully!",
        "token":   token,
        "user": {
            "id":                 user_id,
            "full_name":          data["full_name"],
            "phone_number":       phone,
            "gender":             data["gender"],
            "is_specially_abled": bool(data.get("is_specially_abled", False)),
        }
    }), 201


@app.route("/api/auth/signin", methods=["POST"])
def signin():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data received"}), 400

    phone = str(data.get("phone_number", "")).strip()
    pin   = str(data.get("login_pin", "")).strip()

    if not phone or not pin:
        return jsonify({"error": "Phone number and PIN are required"}), 400

    cur  = db.cursor()
    user = get_user_by_phone(cur, phone)
    cur.close()

    if not user:
        return jsonify({"error": "No account found with this phone number"}), 404

    if not bcrypt.check_password_hash(user["pin_hash"], pin):
        return jsonify({"error": "Incorrect PIN. Try again."}), 401

    token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "message": "Login successful!",
        "token":   token,
        "user": {
            "id":                 user["id"],
            "full_name":          user["full_name"],
            "phone_number":       user["phone_number"],
            "gender":             user["gender"],
            "is_specially_abled": bool(user.get("is_abled", False))
        }
    }), 200


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_me():
    cur  = db.cursor()
    user = get_user_by_id(cur, get_jwt_identity())
    cur.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user["is_specially_abled"] = bool(user.get("is_specially_abled"))
    user["date_of_birth"] = str(user["date_of_birth"])
    user["created_at"]    = str(user["created_at"])
    return jsonify(user), 200


@app.route("/api/auth/change-pin", methods=["PUT"])
@jwt_required()
def change_pin():
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}
    old_pin = str(data.get("old_pin", "")).strip()
    new_pin = str(data.get("new_pin", "")).strip()

    if not old_pin or not new_pin:
        return jsonify({"error": "Both old and new PIN required"}), 400
    if len(new_pin) < 4:
        return jsonify({"error": "New PIN must be at least 4 characters"}), 400

    cur = db.cursor()
    cur.execute("SELECT pin_hash FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()

    if not row or not bcrypt.check_password_hash(row["pin_hash"], old_pin):
        cur.close()
        return jsonify({"error": "Old PIN is incorrect"}), 401

    new_hashed = bcrypt.generate_password_hash(new_pin).decode("utf-8")
    update_user_pin(cur, user_id, new_hashed)
    db.commit()
    cur.close()
    return jsonify({"message": "PIN updated successfully!"}), 200


# ═════════════════════════════════════════
# CONTACTS ROUTES
# ═════════════════════════════════════════
MAX_CONTACTS = 4


@app.route("/api/contacts", methods=["GET"])
@jwt_required()
def get_contacts():
    cur = db.cursor()
    cur.execute(
        "SELECT id, name, phone, relation, is_primary FROM contacts "
        "WHERE user_id = %s ORDER BY is_primary DESC, id ASC",
        (get_jwt_identity(),)
    )
    contacts = cur.fetchall()
    cur.close()
    for c in contacts:
        c["is_primary"] = bool(c["is_primary"])
    return jsonify(contacts), 200


@app.route("/api/contacts", methods=["POST"])
@jwt_required()
def add_contact():
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}

    name     = str(data.get("name", "")).strip()
    phone    = clean_phone(data.get("phone"))
    relation = str(data.get("relation") or "Other").strip()[:50]
    primary  = bool(data.get("is_primary"))

    if not name or not data.get("phone"):
        return jsonify({"error": "Name and phone required"}), 400
    if not phone:
        return jsonify({"error": "Enter a valid 10-digit mobile number"}), 400

    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM contacts WHERE user_id = %s", (user_id,))
    if cur.fetchone()["cnt"] >= MAX_CONTACTS:
        cur.close()
        return jsonify({"error": f"Maximum {MAX_CONTACTS} contacts allowed"}), 400

    cur.execute("SELECT id FROM contacts WHERE user_id = %s AND phone = %s", (user_id, phone))
    if cur.fetchone():
        cur.close()
        return jsonify({"error": "This number is already in your contacts"}), 409

    if primary:
        cur.execute("UPDATE contacts SET is_primary = FALSE WHERE user_id = %s", (user_id,))

    cur.execute(
        "INSERT INTO contacts (user_id, name, phone, relation, is_primary) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, name, phone, relation, primary)
    )
    db.commit()
    new_id = cur.lastrowid
    user = get_user_by_id(cur, user_id)
    cur.close()

    sms_result = {"success": False, "error": "Notification disabled"}
    if app.config["NOTIFY_ON_CONTACT_ADD"]:
        user_name = user["full_name"] if user else "A Prahari user"
        sms_result = sms([phone], (
            f"Hi {name}! {user_name} has added you as an emergency contact "
            f"in the Prahari Safety App. You will get an alert with their location "
            f"if they trigger an SOS. - Team Prahari"
        ))

    return jsonify({
        "message":  "Contact saved!",
        "id":       new_id,
        "sms_sent": sms_result["success"],
        "sms_info": "Alert delivered!" if sms_result["success"] else sms_result.get("error"),
    }), 201


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@jwt_required()
def delete_contact(contact_id):
    cur = db.cursor()
    cur.execute(
        "DELETE FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, get_jwt_identity())
    )
    db.commit()
    affected = cur.rowcount
    cur.close()
    if not affected:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"message": "Contact deleted!"}), 200


# ═════════════════════════════════════════
# SOS TRIGGER  — POST /api/sos/trigger
# ═════════════════════════════════════════
@app.route("/api/sos/trigger", methods=["POST"])
@jwt_required()
def sos_trigger():
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}

    latitude   = data.get("latitude")
    longitude  = data.get("longitude")
    transcript = str(data.get("transcript") or "").strip()
    ps_name    = str(data.get("ps_name") or "").strip()

    if latitude is not None and longitude is not None:
        try:
            latitude, longitude = float(latitude), float(longitude)
            location_link = f"https://maps.google.com/?q={latitude},{longitude}"
        except (TypeError, ValueError):
            latitude = longitude = None
            location_link = "Location unavailable"
    else:
        latitude = longitude = None
        location_link = "Location unavailable"

    cur  = db.cursor()
    user = get_user_by_id(cur, user_id)
    cur.execute(
        "SELECT name, phone, is_primary FROM contacts "
        "WHERE user_id = %s ORDER BY is_primary DESC",
        (user_id,)
    )
    contacts = cur.fetchall()
    cur.close()

    if not contacts:
        return jsonify({"error": "No emergency contacts saved. Add contacts first."}), 400

    phone_numbers = list(dict.fromkeys(
        n for n in (clean_phone(c["phone"]) for c in contacts) if n
    ))
    if not phone_numbers:
        return jsonify({"error": "No valid 10-digit phone numbers in contacts"}), 400

    user_name  = user["full_name"]    if user else "Prahari User"
    user_phone = user["phone_number"] if user else ""

    message = (
        f"SOS ALERT! {user_name} ({user_phone}) NEEDS HELP NOW!\n"
        f"Location: {location_link}"
    )
    if ps_name:
        message += f"\nPS: {ps_name}"
    if transcript:
        extra = f'\nVoice: "{transcript[:60]}"'
        if len(message) + len(extra) <= 320:
            message += extra
    message += "\n- Prahari Safety App"

    result = sms(phone_numbers, message)

    try:
        log_cur = db.cursor()
        log_cur.execute(
            "INSERT INTO sos_logs (user_id, latitude, longitude, transcript, sms_sent) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, latitude, longitude, transcript, result["success"])
        )
        db.commit()
        log_cur.close()
    except Exception as e:
        app.logger.warning("Could not write sos_logs: %s", e)

    if result["success"]:
        return jsonify({
            "message":          f"SOS alert sent to {result['sent']} contact(s)!",
            "contacts_alerted": result["sent"],
            "failed":           result["failed"],
            "location":         location_link,
            "details":          result["error"],
        }), 200

    return jsonify({
        "error":   "Alert sending failed",
        "details": result["error"],
    }), 502


# ═════════════════════════════════════════
# SOS CANCEL — POST /api/sos/cancel
# ═════════════════════════════════════════
@app.route("/api/sos/cancel", methods=["POST"])
@jwt_required()
def sos_cancel():
    user_id = get_jwt_identity()

    cur  = db.cursor()
    user = get_user_by_id(cur, user_id)
    cur.execute("SELECT phone FROM contacts WHERE user_id = %s", (user_id,))
    contacts = cur.fetchall()
    cur.close()

    phone_numbers = list(dict.fromkeys(
        n for n in (clean_phone(c["phone"]) for c in contacts) if n
    ))
    user_name = user["full_name"] if user else "Prahari User"

    notified = 0
    if phone_numbers:
        result = sms(phone_numbers, (
            f"UPDATE: {user_name} has CANCELLED the SOS alert. "
            f"They are safe. - Prahari Safety App"
        ))
        notified = result["sent"]

    return jsonify({
        "message": "SOS cancelled, contacts notified",
        "contacts_notified": notified
    }), 200


# ═════════════════════════════════════════
# GEMINI AI CHATBOT — POST /api/chat
# (With automatic fallback & 503 retry)
# ═════════════════════════════════════════
CHAT_SYSTEM = (
    "You are Prahari Assistant, a calm and helpful safety chatbot inside the Prahari "
    "women/personal safety app (India). Give short, practical safety tips, explain app "
    "features (SOS button, emergency contacts, voice trigger, nearest police station), "
    "and in danger always tell the user to press SOS or call 112 (emergency), 100 (police), "
    "1091 (women helpline). Keep answers under 120 words."
)


@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    key = app.config["GEMINI_API_KEY"]
    if not key:
        return jsonify({"error": "Chatbot not configured (set GEMINI_API_KEY in .env)"}), 503

    data    = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()[:1000]
    history = data.get("history") or []
    if not message:
        return jsonify({"error": "Message required"}), 400

    contents = []
    for h in history[-10:]:
        role = "model" if h.get("role") == "model" else "user"
        contents.append({"role": role, "parts": [{"text": str(h.get("text", ""))[:1000]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    # Try configured model first, then high-availability fallback models
    configured = app.config["GEMINI_MODEL"]
    candidate_models = list(dict.fromkeys([
        configured,
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]))

    last_status = 502
    last_detail = "Service temporarily unavailable."

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": CHAT_SYSTEM}]},
            "contents": contents
        }
        if "2.5" in model_name:
            payload["generationConfig"] = {"thinkingConfig": {"thinkingBudget": 0}}

        for attempt in range(3):
            try:
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=30,
                )
                if r.status_code == 200:
                    reply = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return jsonify({"reply": reply, "model": model_name}), 200

                last_status = r.status_code
                try:
                    last_detail = r.json().get("error", {}).get("message", r.text)
                except ValueError:
                    last_detail = r.text

                print(f"\n[GEMINI {model_name} attempt {attempt+1}] {last_status}: {last_detail}\n", flush=True)

                # Retry on temporary overload/rate limit
                if r.status_code in (429, 503):
                    time.sleep(2 * (attempt + 1))
                    continue
                # Non-retryable error (e.g. 404 model not found) -> move to next fallback model
                break

            except Exception as e:
                last_detail = str(e)
                print(f"\n[GEMINI {model_name} EXCEPTION] {e}\n", flush=True)
                break

    return jsonify({
        "reply": (
            "I'm experiencing high traffic right now. "
            "If this is an emergency, press and hold SOS for 3 seconds or dial 112 immediately."
        ),
        "error": f"Gemini error {last_status}: {last_detail[:180]}"
    }), 200


# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)