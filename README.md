# Prahari
Prahari is a web-based safety application designed to provide instant emergency assistance, real-time location tracking, and secure communication during critical situations. The system focuses on enhancing personal safety by enabling users to quickly alert trusted contacts and authorities with minimal effort.

The application features a user-friendly dashboard where individuals can securely log in using a PIN-based authentication system or Google Sign-In, ensuring both accessibility and security. In emergency scenarios, users can activate a one-tap SOS button, which triggers alerts, shares live location, and initiates safety protocols.

The platform integrates real-time map services to help users navigate to nearby safe locations such as police stations. It also supports voice-triggered commands, allowing hands-free activation of emergency alerts. Additionally, an offline SMS fallback mechanism ensures alerts can still be sent even without internet connectivity.

On the backend, the system uses a Flask-based REST API to manage authentication, user data, and emergency contacts. Sensitive information such as login PINs is securely handled using encryption techniques, and user sessions are maintained using token-based authentication (JWT). Data is stored in a MySQL database, ensuring reliability and scalability.

Overall, Prahari provides a comprehensive, secure, and intelligent safety solution, combining modern web technologies with practical real-world use cases to improve emergency response and personal security.

🎯 Key Objectives
Provide instant emergency alert system
Enable real-time location sharing
Ensure secure user authentication
Support quick access to emergency services
Work reliably even in low connectivity scenarios

⭐ Key Features
🚨 One-tap SOS alert system
📍 Live location tracking (map integration)
🎤 Voice-activated emergency trigger
🔐 Secure login with PIN & JWT
👥 Emergency contacts management
📶 Offline SMS fallback
🌐 Google Sign-In integration (in future)


---

## 🛠 Setup & Run

```bash
pip install -r requirements.txt
# 1. edit .env  (MySQL user/password/db name)
python init_db.py        # creates the database + tables (safe to run again)
python app.py            # open http://localhost:5000
```

## 📲 SMS alerts

SOS, SOS-cancel and "you were added as emergency contact" messages all go through `sms.py`.
Choose the provider in `.env`:

| `SMS_PROVIDER` | What happens |
|---|---|
| `console` (default) | Nothing is sent. The SMS text is printed in the terminal. Use this to test the whole app for free. |
| `twilio` | Real SMS through Twilio. Fill `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`. |

**Twilio free trial notes**
1. Sign up at twilio.com → get a trial phone number.
2. Console → *Phone Numbers → Verified Caller IDs* → verify every contact number you want to alert (trial accounts can only text verified numbers, max 5).
3. Put the SID / token / number in `.env`, set `SMS_PROVIDER=twilio`.
4. Check it: `python test_sms.py 98XXXXXXXX`

Trial messages carry a "Sent from your Twilio trial account" prefix. Upgrading the account removes the
verified-only restriction.

**Fallback:** if the server can't send the SMS (no credits, server down, guest SOS), the app opens the
phone's own SMS app with the alert pre-filled for all emergency contacts – the user just presses Send.

## 🔌 API

| Method | Route | Auth |
|---|---|---|
| POST | `/api/auth/signup`, `/api/auth/signin` | – |
| GET | `/api/auth/me` | JWT |
| PUT | `/api/auth/change-pin` | JWT |
| GET / POST | `/api/contacts` (max 4) | JWT |
| DELETE | `/api/contacts/<id>` | JWT |
| POST | `/api/sos/trigger`, `/api/sos/cancel` | JWT |
| GET | `/api/health` | – |
