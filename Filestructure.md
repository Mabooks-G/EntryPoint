```
EntryPoint/
│
├── backend/
│   ├── app.py                    # FastAPI entry point
│   │
│   ├── routes/
│   │     auth.py
│   │     users.py
│   │     applications.py
│   │     documents.py
│   │     admin.py
│   │
│   ├── services/
│   │     ocr_service.py
│   │     classifier_service.py
│   │     validation_service.py
│   │     gemma_service.py
│   │     requirement_service.py
│   │     quality_check_service.py
│   │
│   ├── database/
│   │     db.py
│
├── frontend/
│   ├── public/
│   │
│   └── src/
│        ├── App.js
│        ├── index.js
│        │
│        ├── pages/
│        │      Login.jsx
│        │      Register.jsx
│        │      Dashboard.jsx
│        │      NewApplication.jsx
│        │      UploadDocuments.jsx
│        │      Ready.jsx
│        │      AdminDashboard.jsx
│        │      Notification.jsx
│        │
│        ├── assets/
│
├── README.md
├── FileStructure.md
├── Stories.md
```
