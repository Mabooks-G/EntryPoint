
# Feature 1: User Authentication

### US-01 – Register

**As a new applicant,** I want to create an EntryPoint account so that I can securely manage my immigration applications.

**Acceptance Criteria**

* User can register using email and password.
* Email verification is sent.
* User is redirected to the dashboard after verification.

---

### US-02 – Login

**As an applicant,** I want to securely log in so that I can continue my existing applications.

---

# Feature 2: Application Management

### US-03 – Create Application

**As an applicant,** I want to select my destination country, nationality, and visa type so that EntryPoint can determine the correct document requirements.

**Acceptance Criteria**

* User selects destination country.
* User selects nationality.
* User selects visa type.
* Application is created successfully.

---

### US-04 – View Dashboard

**As an applicant,** I want to view all my applications and their readiness scores so that I can track my progress.

Example

```
Applications

Canada Student Visa
84%

South Africa Work Visa
62%

+ New Application
```

---

# Feature 3: Document Management

### US-==0==5 – Upload Documents

**As an applicant,** I want to upload immigration documents so that AI can analyse and validate them.

Acceptance Criteria

* Drag and drop upload
* PDF
* JPG
* PNG

---

### US-==0==6 – AI Document Analysis

**As an applicant,** I want AI to analyse my uploaded documents so that I know whether my application is complete.

During processing

```
Reading Passport...

Checking Expiry Date...

Extracting Information...

Comparing Requirements...

Searching Missing Documents...
```

---

### US-==0==7 – View Validation Results

**As an applicant,** I want to view the validation results so that I know what must be corrected before submission.

Example

```
Application Readiness

84%

Passport ✔

Degree ✔

Police Clearance ⚠

Medical ❌

Biometrics ❌
```

---

### US-==0==8 – View Requirement Explanation

**As an applicant,** I want to understand why a document is required so that I know how to complete my application.

Example

```
Medical Examination

Required because

Canada requires all
student visa applicants
to complete a medical
exam before approval.
```

---

### US-==0==9 – View Readiness Score

**As an applicant,** I want to see my readiness score so that I know how close I am to submitting a complete application.

Example

```
Ready Score

91%

Excellent

Estimated Approval

High
```

---

### US-10 – Download Report

**As an applicant,** I want to download my validation report so that I can keep a record of my application status.

---

### US-11 – Receive Notifications

**As an applicant,** I want to receive notifications about document issues so that I can resolve them before submission.

Example

```
Passport expires in 2 months.

Your police clearance has expired.

Medical examination still required.
```

---

# Feature 4: Administrative Review

I **really like** that you added an admin side. Most hackathon teams forget that immigration applications often involve human review.

### US-012 – Manual Document Verification

**As an administrator,** I want to manually review documents that the AI cannot confidently validate so that applications receive an accurate assessment.

Example

| Document         | Status             | Reason             |
| ---------------- | ------------------ | ------------------ |
| Passport         | ✅ Approved        | -                  |
| Police Clearance | ❌ Rejected        | Expired            |
| Bank Statement   | ⚠ Review Required | Poor image quality |

---

### US-13 – Respond to Applicant Queries

**As an administrator,** I want to respond to applicant questions and review requests so that applicants receive guidance when AI cannot assist.

---

# One feature I'd add (this could impress judges)

## US-14 – Confidence Score

Instead of pretending the AI is always correct, show its confidence.

```
Passport

Verified

Confidence

98%
```

```
Marriage Certificate

Needs Manual Review

Confidence

52%
```

Then documents below a threshold (for example, **80%**) are automatically sent to the admin queue.

This demonstrates that your system is **designed with human oversight**, which is important for an application that deals with legal documentation. It also shows judges you've thought about responsible AI rather than treating the model as infallible.

---

## The overall product becomes:

* 📊 Dashboard
* 📄 Document Management
* 🤖 AI Validation
* 📈 Readiness Score
* 📥 Reports
* 🔔 Notifications
* 👨‍💼 Human Review
* 💬 Support
