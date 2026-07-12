<p align="center"><img src="src/assets/logo3.png" alt="EntryPoint" width="180"></p>

# Global Visa Document Readiness Platform

## Problem

Travellers do not have one integrated place to understand visa requirements, verify the documents they hold, and fix problems before travelling. This costs time and money and can contribute to unsafe or irregular migration when people attempt to cross borders without the required documentation. EntryPoint gives applicants an earlier, practical readiness check so they can prepare before an application or border crossing.

## Platform

EntryPoint lets an applicant create a visa application, select origin and destination countries, upload supporting documents, receive AI document analysis, track readiness, and ask an administrator for help. Administrators manage requirements, respond to queries, and mark them resolved.

## System flow

1. The applicant selects origin, destination, and visa type.
2. The platform loads the visa checklist.
3. The browser performs OCR with Tesseract.js and PDF.js before upload; the backend can perform server-side OCR as a fallback.
4. Supabase stores application records, document metadata, OCR text, and files.
5. FastAPI sends extracted text to DeepSeek V4 Pro through Fireworks AI.
6. The AI classifies every stored document and returns confidence, validity, extracted details, and issues.
7. The latest score, summary, and document classification are saved, so progress is present when the account is reopened.

## Deployment

The frontend and API are intended for AMD Cloud deployment. GitHub manages source control and delivery. Supabase provides PostgreSQL and file storage. Fireworks AI hosts DeepSeek; the model does not run locally. Docker packages the backend.

## Services

| Area | Service or technology | Purpose |
|---|---|---|
| Web app | React, TypeScript, Vite | Applicant and administrator interface |
| Styling | Tailwind CSS | Responsive UI |
| OCR | Tesseract.js, PDF.js, Tesseract, Pillow | Browser and server text extraction |
| API | Python, FastAPI, Uvicorn | Application, document, analysis, and query API |
| AI | DeepSeek V4 Pro via Fireworks AI | Document classification and analysis |
| AI transport | OpenAI-compatible API, HTTPX | Fireworks model requests |
| Data | Supabase PostgreSQL | Users, applications, requirements, queries, and AI results |
| File storage | Supabase Storage | Uploaded document files |
| Authentication | bcrypt and custom tokens | Applicant and administrator access |
| Hosting | AMD Cloud and Docker | Deployment runtime |
| Source control | GitHub | Version control and delivery |

