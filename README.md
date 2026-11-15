# 🛡️ Prahari — Your Safety, Our Priority

**Prahari** is a full-stack personal and women's safety web application engineered for rapid emergency response, real-time GPS tracking, hands-free voice SOS activation, multi-channel emergency alerts (SMTP & Twilio SMS), and AI-powered safety guidance[cite: 3, 9].

Built with **Python (Flask)**, **MySQL**, **JWT Authentication**, **Leaflet.js**, and **Google Gemini AI**, Prahari minimizes response time during critical situations with one-tap and voice-triggered emergency workflows[cite: 3, 9].

---

## ✨ Key Features

- **🚨 5-Second Buffer Emergency SOS Trigger**: Features a 5-second safety buffer countdown (to prevent accidental false alarms) before capturing live GPS coordinates and dispatching immediate alerts to up to 4 saved emergency contacts, with an option to broadcast a "Safe / SOS Cancelled" update[cite: 3, 9].
- **🎤 Hands-Free Voice Activation**: Continuous browser-based speech recognition listens for emergency phrases (such as *"Help me"*) and automatically triggers the SOS protocol along with the captured voice transcript[cite: 1, 3, 9].
- **📍 Live GPS Map & Safe-Zone Navigation**: Real-time location tracking powered by **Leaflet.js**, displaying exact coordinates, accuracy radius, and quick navigation to the nearest police station and safe zones[cite: 1, 19].
- **🤖 Prahari AI Safety Assistant**: Embedded floating chatbot powered by **Google Gemini** (`gemini-3.5-flash-lite` with automatic fallback and retry resilience) providing calm, practical safety guidance and instant Indian emergency helpline numbers (`112`, `100`, `1091`)[cite: 3, 6].
- **📩 Multi-Provider Alert Delivery (Brevo SMTP + Twilio + Offline Fallback)**:
  - **SMTP Relay (Brevo / Gmail)**: Primary zero-cost alert engine dispatching instant emergency alerts containing live Google Maps links[cite: 3, 4].
  - **Twilio SMS**: Optional plug-and-play SMS integration for direct carrier messaging[cite: 3, 9].
  - **Offline / Console Fallback**: Prints alerts in the server console for local testing or opens the device's native SMS app pre-filled when offline[cite: 4, 9].
- **🔐 Secure PIN & JWT Authentication**: Login PINs are hashed with `Flask-Bcrypt`, and protected API routes use `Flask-JWT-Extended` bearer tokens[cite: 3, 9].
- **👥 Emergency Contact Management**: Store up to 4 trusted contacts with relationship tags, primary contact prioritization, and automatic opt-in notification alerts when added[cite: 3, 9].

---

## 🏗️ Tech Stack & Architecture

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3, Flask, Flask-CORS[cite: 3] |
| **Database** | MySQL (`mysql-connector-python`)[cite: 3] |
| **Authentication & Security** | Flask-JWT-Extended (JWT), Flask-Bcrypt[cite: 3] |
| **AI Assistant** | Google Gemini API (Multi-model fallback & retry architecture)[cite: 3] |
| **Alert & Messaging Engine** | Python `smtplib` (Brevo/Gmail SMTP), Twilio REST API[cite: 3, 9] |
| **Frontend & Maps** | HTML5, CSS3, Vanilla JavaScript, Leaflet.js, Web Speech API[cite: 3, 6, 9] |

---

## 📂 Repository Structure

- `app.py` — Main Flask REST API, auth, SOS routes & Gemini AI endpoint[cite: 3, 21]
- `sms.py` — Unified alert dispatcher (SMTP relay, Twilio SMS & console modes)[cite: 3, 21]
- `config.py` — Environment variable loader and Flask configuration[cite: 5, 21]
- `models.py` — MySQL query helpers for user creation, lookup & PIN updates[cite: 8, 21]
- `init_db.py` — Automated MySQL database and table setup script[cite: 12, 21]
- `schema.sql` — Database schema (`users`, `contacts`, `sos_logs`)[cite: 10, 21]
- `chat.js` — Floating Prahari AI Assistant widget and chat history UI[cite: 6, 21]
- `prahari-v3 (1).html` — Main safety dashboard, Leaflet map, 5-second SOS buffer & voice listener[cite: 3, 21]
- `test_sms.py` — CLI utility to test SMS/SMTP alert delivery[cite: 11, 21]
- `requirements.txt` — Python dependencies[cite: 9, 21]
- `logo.png` — Prahari brand logo[cite: 7, 21]

---

## ⚙️ How the System Works

1. **Authentication Flow**: Users sign up with their profile details, 6-digit area PIN code, and numeric login PIN[cite: 3, 9]. The backend hashes the PIN with Bcrypt and issues a signed JWT stored in `localStorage` (`prahari_token`)[cite: 3, 6].
2. **SOS Dispatch Pipeline (5-Second Buffer)**:
   - Triggered via the **SOS** button or **Voice Trigger** (*"Help me"*)[cite: 1, 19].
   - A **5-second buffer window** runs so users can cancel accidental activations before any alert is sent.
   - Once the 5-second buffer completes, the frontend sends `latitude`, `longitude`, nearest police station info, and any voice `transcript` to `POST /api/sos/trigger`[cite: 3].
   - Flask retrieves the user's prioritized contacts from MySQL, formats a Google Maps link (`https://maps.google.com/?q=lat,lng`), dispatches alerts via `sms.py` (`SMTP` or `Twilio`), and records the incident in `sos_logs`[cite: 3, 10].
3. **Resilient AI Chatbot (`POST /api/chat`)**:
   - `chat.js` sends the user's message and conversation history with the JWT token to `/api/chat`[cite: 3, 6].
   - `app.py` queries Google Gemini with exponential backoff and automatic model fallback (`gemini-3.5-flash-lite` → `gemini-3.8-flash` → `gemini-2.5-flash-lite`) so temporary traffic spikes (`503`) never interrupt user support[cite: 1].

---

## 🔑 How to Create Required API Keys

### 1. Google Gemini API Key (For Prahari Assistant Chatbot)
1. Visit **[Google AI Studio](https://aistudio.google.com/apikey)** and sign in with your Google account.
2. Click **Create API key** and select or create a Google Cloud project.
3. Copy the generated key and paste it into `.env` as `GEMINI_API_KEY`[cite: 4].

### 2. Brevo SMTP Credentials (Primary Alert Engine — Free, No 2FA Needed)
1. Create a free account at **[Brevo](https://www.brevo.com)** (includes 300 free alerts/day).
2. Click your profile name in the top-right corner → **SMTP & API** → open the **SMTP** tab[cite: 16].
3. Copy your **Login** (e.g., `xxxxxxx@smtp-brevo.com`) into `SMTP_USER`[cite: 4].
4. Click **Generate a new SMTP key**, name it `Prahari`, and paste the generated key into `SMTP_PASSWORD`[cite: 4, 16].

*(Optional — Twilio SMS: Sign up at [twilio.com](https://www.twilio.com), copy your Account SID, Auth Token, and Trial Phone Number into `.env`, and set `SMS_PROVIDER=twilio`[cite: 4, 9].)*

---

## 🚀 Setup & Installation

1. **Clone the Repository**:
   Run `git clone https://github.com/<your-username>/prahari-safety-app.git` and `cd prahari-safety-app`.
2. **Install Dependencies**:
   Run `pip install -r requirements.txt`[cite: 9].
3. **Configure Environment Variables**:
   Create a `.env` file in the root directory (never commit this file to GitHub) with the following keys:
   - `MYSQL_HOST=localhost`[cite: 4]
   - `MYSQL_USER=your_mysql_user`[cite: 4]
   - `MYSQL_PASSWORD=your_mysql_password`[cite: 4]
   - `MYSQL_DB=prahari_db`[cite: 4]
   - `SECRET_KEY=your_random_flask_secret_key`[cite: 4]
   - `JWT_SECRET_KEY=your_random_jwt_secret_key`[cite: 4]
   - `JWT_ACCESS_TOKEN_EXPIRES=86400`[cite: 4]
   - `SMS_PROVIDER=smtp`[cite: 4, 13]
   - `NOTIFY_ON_CONTACT_ADD=true`[cite: 4, 13]
   - `SMTP_HOST=smtp-relay.brevo.com`
   - `SMTP_PORT=587`[cite: 4]
   - `SMTP_USER=your_smtp_login@smtp-brevo.com`[cite: 4]
   - `SMTP_PASSWORD=your_smtp_key`[cite: 4]
   - `SMTP_FROM=your_verified_sender@gmail.com`[cite: 4]
   - `SMTP_SMS_GATEWAY=airtelkk.com`[cite: 4]
   - `GEMINI_API_KEY=your_gemini_api_key`[cite: 4]
   - `GEMINI_MODEL=gemini-3.5-flash-lite`
4. **Initialize the MySQL Database**:
   Run `python init_db.py` once to automatically create `prahari_db` and the `users`, `contacts`, and `sos_logs` tables[cite: 12].
5. **Run the Application**:
   Run `python app.py` and open **`http://127.0.0.1:5000`** in your browser[cite: 1, 9].

---

## 🔌 REST API Reference

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/auth/signup` | Public | Register a new user account[cite: 3, 9] |
| `POST` | `/api/auth/signin` | Public | Authenticate via phone & PIN; returns JWT[cite: 3, 9] |
| `GET` | `/api/auth/me` | JWT | Fetch logged-in user profile[cite: 3, 9] |
| `PUT` | `/api/auth/change-pin` | JWT | Update user login PIN[cite: 3, 9] |
| `GET` | `/api/contacts` | JWT | List saved emergency contacts (max 4)[cite: 3, 9] |
| `POST` | `/api/contacts` | JWT | Add emergency contact & send opt-in alert[cite: 3, 9] |
| `DELETE` | `/api/contacts/<id>` | JWT | Remove an emergency contact[cite: 3, 9] |
| `POST` | `/api/sos/trigger` | JWT | Dispatch SOS alerts after 5-second buffer with GPS & voice transcript[cite: 3, 9] |
| `POST` | `/api/sos/cancel` | JWT | Notify contacts that user is safe[cite: 3, 9] |
| `POST` | `/api/chat` | JWT | Send message to Prahari Gemini AI Assistant[cite: 3] |
| `GET` | `/api/health` | Public | Check server, SMS provider & Gemini model status[cite: 3] |

---

## 🔮 Future Enhancements

- Native Android/iOS Progressive Web App (PWA) background GPS tracking[cite: 1, 9]
- Direct email + SMS dual-channel alerts per emergency contact[cite: 3, 4]
- Automated audio/video evidence recording during active SOS sessions[cite: 1, 3]
- One-tap Google OAuth Sign-In integration[cite: 9]
