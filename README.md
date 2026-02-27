# ArtVerse AR Gallery

ArtVerse is a full-stack web application for discovering, managing, and viewing artwork in augmented reality. It combines a Flask backend with a React + Vite frontend and includes role-based experiences for buyers and sellers.

## Overview

- Session-based authentication (signup/login/logout)
- Buyer and seller dashboards
- Artwork detail pages with AR/3D viewing support
- Admin and API routes for artwork management
- Modern React UI with reusable components and Tailwind setup

## Tech Stack

- Backend: Flask, Flask-SQLAlchemy, Flask-CORS, Gunicorn
- Frontend: React, Vite, React Router, Tailwind CSS, Framer Motion
- Database: SQLite (default)

## Project Structure

```text
arArtGallery/
├── app/                    # Flask app package (routes, models, config)
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── css/
│   └── package.json
├── data/                   # Artwork source assets and data notes
├── run.py                  # Local Flask entry point
├── requirements.txt        # Python dependencies
├── Dockerfile
├── docker-compose.yml
└── wsgi.py                 # WSGI entry point for deployment
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### 1) Backend Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Frontend Setup

```bash
cd frontend
npm install --legacy-peer-deps
cd ..
```

### 3) Run in Development

Backend (from repo root):

```bash
PORT=5001 .venv/bin/python run.py
```

Frontend (from `frontend/`):

```bash
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5001`

## Build and Production

Build frontend assets:

```bash
cd frontend
npm run build
cd ..
```

Run with Gunicorn:

```bash
gunicorn wsgi:app
```

## Key Routes

- `/` — Landing/Gallery
- `/start` — Authentication entry
- `/select-role` — Role selection
- `/buyer` — Buyer experience
- `/seller` — Seller experience
- `/artwork/:id` — Artwork detail view

## API Highlights

- `GET /api/me`
- `POST /api/login`
- `POST /api/signup`
- `POST /make-glb`
- `GET /artworks`

## Notes

- If port `5000` is occupied on macOS, use `PORT=5001` for local backend runs.
- CORS and proxy settings are configured for local frontend-backend development.

## License

This project is licensed under the MIT License.
