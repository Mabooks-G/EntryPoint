# EntryPoint - Functionality

This document describes the responsibility of every file in the project. Each file should have a single responsibility to keep the project modular and easy to maintain.

---

# Backend

## app.py

### Purpose

Main entry point of the backend application.

### Responsibilities

- Start the FastAPI server
- Register all API routes
- Configure CORS
- Connect to the database
- Initialize AI services
- Serve API endpoints

---

# routes/

Routes only receive HTTP requests and return responses.

Business logic belongs in the Services folder.

---

## auth.py

### Purpose

Authentication endpoints.

### Endpoints

POST /login

POST /register

POST /logout

POST /forgot-password

---

## users.py

### Purpose

Manage user information.

### Endpoints

GET /user

PUT /user

DELETE /user

---

## applications.py

### Purpose

Manage immigration applications.

### Endpoints

POST /application/new

GET /applications

GET /application/{id}

DELETE /application/{id}

Responsibilities

- Create application
- Retrieve application
- Update application
- Delete application

---

## documents.py

### Purpose

Handle document uploads.

### Endpoints

POST /upload

GET /documents

DELETE /document/{id}

Responsibilities

- Receive uploaded files
- Store uploaded files
- Send files to OCR
- Trigger AI validation pipeline

---

## admin.py

### Purpose

Administrator functions.

### Endpoints

GET /admin/applications

POST /admin/review

POST /admin/respond

Responsibilities

- View flagged applications
- Manually verify documents
- Respond to applicant queries

---

# services/

Services contain all business logic.

---

## ocr_service.py

### Purpose

Extract text from uploaded documents.

### Input

PDF

Image

e.g Passport, Bank Statement

### Output

Plain text

Responsibilities

- OCR
- Text extraction
- Image preprocessing

---

## classifier_service.py

### Purpose

Determine document type.

Example

Passport

Bank Statement

Police Clearance

Birth Certificate

### Output

JSON

Example

{
    "document_type":"Passport",
    "confidence":0.99
}

---

## requirement_service.py

### Purpose

Determine required documents.

Input

Country

Nationality

Visa Type

Output

Requirement JSON

Example

Canada Student Visa

↓

Passport

Medical

Biometrics

Bank Statement

Responsibilities

- Load requirements
- Compare destination country
- Return required documents

---

## quality_check_service.py

### Purpose

Check uploaded document quality.

Checks

- Blurry images
- Missing pages
- Corrupted PDF
- Low resolution
- Unsupported format

Output

Warnings

---

## validation_service.py

### Purpose

Compare uploaded documents against requirements.

Responsibilities

- Detect missing documents
- Detect expired documents
- Detect incorrect documents
- Calculate readiness score
- Produce validation JSON

Example Output

{
    "score":84,
    "missing":[
        "Medical Exam"
    ],
    "warnings":[
        "Passport expires in 5 months"
    ]
}

---

## gemma_service.py

### Purpose

Generate AI explanations using Gemma.

Input

Validation JSON

Output

Human-friendly explanation

Example

Your application is almost ready.
You still need to complete your medical examination before submission.

Responsibilities

- Explain validation results
- Generate recommendations
- Generate summary

---

# database/

## db.py

### Purpose

Database connection.

Responsibilities

- Connect database
- Create tables
- CRUD operations

Tables

Users

Applications

Documents

Notifications

---

# Frontend

---

## index.js

Application entry point.

Responsibilities

- Render React App
- Load global styles

---

## App.js

Main application controller.

Responsibilities

- Configure routes
- Navigate pages
- Authentication guard

Routes

/

/login

/register

/dashboard

/upload

/ready

/admin

---

# Pages

Every page represents one screen.

---

## Login.jsx

Responsibilities

- Login form
- Authenticate user
- Redirect to dashboard

---

## Register.jsx

Responsibilities

- Register account
- Validate inputs
- Redirect to login

---

## Dashboard.jsx

Responsibilities

Display

- Applications
- Readiness score
- Notifications
- New Application button

---

## NewApplication.jsx

Responsibilities

Collect

Destination Country

Nationality

Visa Type

Create application

---

## UploadDocuments.jsx

Responsibilities

- Upload files
- Show uploaded documents
- Start AI analysis

---

## Ready.jsx

Responsibilities

Display

- Readiness Score
- Missing Documents
- Passed Documents
- Warnings
- AI Explanation
- Download Report

---

## Notification.jsx

Responsibilities

Display notifications

Examples

Passport expires soon

Medical examination missing

Application updated

---

## AdminDashboard.jsx

Responsibilities

Display

Applications needing review

Applicant messages

Manual verification

Validation history

---

# AI Pipeline

The complete processing flow

User uploads document

↓

OCR Service

↓

Document Classifier

↓

Requirement Service

↓

Quality Check

↓

Validation Service

↓

Gemma Service

↓

Frontend displays results
