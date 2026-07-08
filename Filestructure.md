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
│   ├── models/
│   │     user.py
│   │     application.py
│   │     document.py
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
│        ├── layouts/
│        │      MainLayout.jsx
│        │      AdminLayout.jsx
│        │
│        ├── components/
│        │      Navbar.jsx
│        │      Sidebar.jsx
│        │      Footer.jsx
│        │      UploadBox.jsx
│        │      ReadinessCard.jsx
│        │      Notification.jsx
│        │      DocumentCard.jsx
│        │      ProgressBar.jsx
│        │
│        ├── pages/
│        │      Login.jsx
│        │      Register.jsx
│        │      Dashboard.jsx
│        │      NewApplication.jsx
│        │      UploadDocuments.jsx
│        │      AIAnalysis.jsx
│        │      Results.jsx
│        │      Report.jsx
│        │      AdminDashboard.jsx
│        │
│        ├── services/
│        │      api.jsx
│        │      authService.jsx
│        │      applicationService.jsx
│        │      documentService.jsx
│        │
│        ├── assets/
│
├── README.md
├── FileStructure.md
├── Stories.md
```
