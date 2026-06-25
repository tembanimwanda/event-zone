# EventZone — Live Event Ticketing Platform

## Project Structure

```
Event Zone system/
├── backend/          ← Flask REST API
│   ├── app.py        ← Application factory
│   ├── models.py     ← Database models
│   ├── auth.py       ← Authentication routes
│   ├── events.py     ← Events routes
│   ├── bookings.py   ← Bookings routes
│   ├── payments.py   ← Payments routes
│   ├── admin.py      ← Admin routes
│   ├── db.py         ← SQLAlchemy setup
│   ├── utils.py      ← Helpers
│   └── requirements.txt
├── frontend/         ← React + Vite app
│   ├── src/
│   │   ├── components/   ← Navbar, Footer, Modals
│   │   ├── pages/        ← HomePage, AdminPage
│   │   ├── App.jsx
│   │   ├── AuthContext.jsx
│   │   ├── api.js
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── render.yaml       ← Render.com deployment blueprint
└── README.md
```

## Local Development

### 1. Start the Flask backend
```bash
cd backend
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000
```

### 2. Start the React frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

Open **http://localhost:3000** in your browser.

**Default admin credentials:**
- Email: `admin@eventzone.com`
- Password: `Admin1234`

---

## Deploy to Render.com

### Option A — Automatic (Blueprint)
1. Push this project to a GitHub repository
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render reads `render.yaml` and deploys both services automatically

### Option B — Manual

#### Backend (Web Service)
1. New → Web Service → connect your repo
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2`
5. Add environment variables:
   - `JWT_SECRET_KEY` → any long random string
   - `ALLOWED_ORIGINS` → your frontend URL (e.g. `https://eventzone-app.onrender.com`)

#### Frontend (Static Site)
1. New → Static Site → connect your repo
2. Root Directory: `frontend`
3. Build Command: `npm install && npm run build`
4. Publish Directory: `dist`
5. Add environment variable:
   - `VITE_API_URL` → your backend URL (e.g. `https://eventzone-api.onrender.com`)
6. Add rewrite rule: `/* → /index.html` (for React Router)

---

## Tech Stack
- **Frontend:** React 18, Vite, React Router, CSS Modules
- **Backend:** Flask, SQLAlchemy, JWT, bcrypt
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Hosting:** Render.com
