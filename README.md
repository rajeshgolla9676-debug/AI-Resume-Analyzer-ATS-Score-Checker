# AI Resume Analyzer & ATS Score Checker

A student-friendly full-stack application that compares a PDF/DOCX resume with a job description, calculates an explainable ATS compatibility estimate, and generates improvement feedback.

## Architecture
- Frontend: vanilla HTML, CSS, JavaScript, Chart.js, Supabase Auth
- API: Python Flask (REST), Supabase token verification and database/storage
- Resume parsing: PyMuPDF and python-docx
- AI: Google Gemini (optional; deterministic matching still works without it)
- Database: Supabase Postgres with Row Level Security

## Repository layout
```
frontend/             Static Vercel frontend
  index.html
  css/style.css
  js/app.js
backend/              Flask API
  app.py config.py resume_parser.py ats_scorer.py ai_analyzer.py report_generator.py
  requirements.txt .env.example
database/schema.sql   Supabase schema and RLS policies
vercel.json           Static frontend deployment configuration
```

## 1. Supabase setup
1. Create a Supabase project.
2. Open SQL Editor and run `database/schema.sql`.
3. In Project Settings → API, copy the Project URL and anon key.
4. Enable Email authentication in Authentication → Providers.
5. Create a private Storage bucket named `resumes` (or let the backend create it if your service-role key has permission).

## 2. Backend setup
Use Python 3.10+.
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and optionally `GEMINI_API_KEY`. Never commit the real `.env` file.
```bash
python app.py
```
API runs at http://localhost:5000. Health check: http://localhost:5000/api/health.

## 3. Frontend setup
Open `frontend/index.html` through a local static server (for example VS Code Live Server). Set `API_BASE_URL`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` at the top of `frontend/js/app.js`. For local API use `http://localhost:5000`.

## 4. Deploy
- Backend: deploy the `backend` directory to Render, Railway, or another Python host. Configure all backend environment variables and set `CORS_ORIGINS` to your frontend origin.
- Frontend: import this GitHub repository into Vercel and set the Root Directory to `frontend`. Because this is a static site, no build command is required.
- Set the frontend configuration values in `frontend/js/app.js` before deploying. Do not put the Supabase service-role key or Gemini key in frontend code.
- Set `API_BASE_URL` to the deployed backend URL and `CORS_ORIGINS` on the backend to the Vercel domain.

## 5. Important notes
- The score is an estimate based on transparent weighted matching, not an official ATS result or a hiring guarantee.
- AI feedback is optional. If Gemini is unavailable, keyword/skill matching and scoring continue to work.
- Never add real secrets to Git. Rotate any key accidentally committed.
- For production, configure Supabase Auth redirect URLs, HTTPS, rate limiting, monitoring, and a retention policy for uploaded resumes.

## API
- POST /api/register, /api/login, /api/logout (Supabase Auth)
- POST /api/upload-resume
- POST /api/analyze-resume
- POST /api/improve-resume
- GET /api/dashboard
- GET /api/history
- GET /api/report/<report_id>
- DELETE /api/history/<report_id>
- GET /api/health

## Testing
Run `python -m compileall backend`, install requirements, start the API, then test upload/analysis using an authenticated Supabase user. Verify that a user cannot read another user's report and that the resumes bucket is private.
