# Deployment & Local Development

Quick steps to run the project locally and notes for production deployment.

Prereqs
- Node.js 18+ and npm
- Python 3.11+
- GitHub OAuth App (Client ID/Secret)
- OpenAI API key

Local: Backend
1. cd `code-review-backend`
2. Create venv and install:
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create `.env` with keys:
   - GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
   - OPENAI_API_KEY
   - JWT_SECRET, JWT_EXPIRE_MINUTES, ENV
4. Run:
   ```
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
Backend entry: [code-review-backend/app/main.py](code-review-backend/app/main.py)

Local: Frontend
1. cd `code-review-frontend`
2. npm install
3. npm run dev
Frontend entry: [code-review-frontend/package.json](code-review-frontend/package.json) and vite config: [code-review-frontend/vite.config.js](code-review-frontend/vite.config.js)

Production notes
- Serve frontend build from a static host (Netlify/Cloudflare Pages/Vercel) or from backend behind a CDN.
- Set `ENV=production` and configure secure cookie flags in [`/api/auth/github/callback`](code-review-backend/app/api/auth.py).
- Use Docker for reproducible deployments; consider a docker-compose setup with a web service (Uvicorn/Gunicorn) and a static file server or reverse proxy (Nginx).
- Rotate secrets; restrict OAuth callback URL in GitHub app settings.

Security checklist before production
- Use HTTPS and set `secure=True` for cookies
- Move session store out of process (replace in-memory `sessions` with Redis)
- Add persistent logging/monitoring and alerting