# File Description

| Location | Role |
|---|---|
| index.html | HTML shell, page metadata, and tab icon |
| package.json | Frontend dependencies and scripts |
| vite.config.ts | Vite, React, Tailwind, and API proxy configuration |
| src/main.tsx | React startup |
| src/App.tsx | Frontend routes |
| src/index.css | Global visual styles |
| src/assets | Logos and image assets |
| src/lib/api.ts | Typed frontend API client |
| src/lib/auth.tsx | Login state and token handling |
| src/lib/ocr.ts | Browser-side OCR |
| src/lib/countries.ts | Ordered country selector data |
| src/pages/Login.tsx | Login, registration, and demos |
| src/pages/NewApplication.tsx | New application workflow |
| src/pages/Dashboard.tsx | Applicant overview |
| src/pages/ApplicationDetail.tsx | Uploads, AI results, readiness, and queries |
| src/pages/AdminDashboard.tsx | Requirement, query, user, and application administration |
| backend/app.py | FastAPI application and router registration |
| backend/config/settings.py | Environment and server settings |
| backend/database/db.py | Supabase client |
| backend/database/global_requirements_migration.sql | Query-resolution schema migration |
| backend/middleware/auth.py | Token and role checks |
| backend/services/auth_service.py | Registration and login |
| backend/services/ocr_service.py | Server OCR fallback |
| backend/services/gemma_service.py | Fireworks DeepSeek analysis and readiness scoring |
| backend/services/requirements_service.py | Requirement country-scope matching |
| backend/routes/auth.py | Authentication endpoints |
| backend/routes/applications.py | Application endpoints |
| backend/routes/documents.py | Upload, storage, OCR, and document endpoints |
| backend/routes/analysis.py | Multi-document AI analysis |
| backend/routes/queries.py | Applicant queries and admin replies |
| backend/routes/reference.py | Visa and requirement lookup |
| backend/routes/admin.py | Administration endpoints |
| backend/requirements.txt | Python packages |
| backend/Dockerfile | Backend container definition |
| backend/docker-compose.yml | Container service configuration |
| example_docs | OCR and analysis sample documents |
| public | Public web assets |
