<p align="center"><img src="src/assets/logo3.png" alt="EntryPoint" width="180"></p>

# Global Visa Document Readiness Platform

Demo link1(Render): [entrypoint-v7fz.onrender.com/dashboard](https://entrypoint-v7fz.onrender.com/dashboard)

Demo link2(AMD Droplet):[http://165.245.135.33:5173](http://165.245.135.33:5173/)

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

| Area           | Service or technology                   | Purpose                                                    |
| -------------- | --------------------------------------- | ---------------------------------------------------------- |
| Web app        | React, TypeScript, Vite                 | Applicant and administrator interface                      |
| Styling        | Tailwind CSS                            | Responsive UI                                              |
| OCR            | Tesseract.js, PDF.js, Tesseract, Pillow | Browser and server text extraction                         |
| API            | Python, FastAPI, Uvicorn                | Application, document, analysis, and query API             |
| AI             | DeepSeek V4 Pro via Fireworks AI        | Document classification and analysis                       |
| AI transport   | OpenAI-compatible API, HTTPX            | Fireworks model requests                                   |
| Data           | Supabase PostgreSQL                     | Users, applications, requirements, queries, and AI results |
| File storage   | Supabase Storage                        | Uploaded document files                                    |
| Authentication | bcrypt and custom tokens                | Applicant and administrator access                         |
| Hosting        | AMD Cloud and Docker                    | Deployment runtime                                         |
| Source control | GitHub                                  | Version control and deliver                                |

# Skills Gained

Building EntryPoint was more than developing an AI-powered immigration platform—it was an opportunity to gain hands-on experience with cloud deployment, Linux, remote development, and modern backend workflows.

## Linux and Remote Development

Throughout this project, I learned how to work entirely on a remote Linux server hosted on the AMD Developer Cloud. Instead of developing only on my local machine, I connected to the server using SSH and managed the application through the terminal.

Skills gained include:

* Connecting securely to remote Linux servers using SSH.
* Generating and managing SSH key pairs for authentication.
* Using Linux terminal commands for navigation and file management.
* Editing files directly on the server using Nano.
* Creating and managing Python virtual environments.
* Installing Python dependencies using pip.
* Running and debugging FastAPI applications from the command line.
* Using Git from the terminal to synchronize changes between GitHub and the remote server.

## Git and Deployment Workflow

I learned how to deploy code directly from GitHub to a remote Linux server by using Git over SSH. This made it possible to update the backend quickly during development while keeping the repository synchronized.

Typical workflow:

1. Develop locally.
2. Commit and push changes to GitHub.
3. Connect to the AMD server using SSH.
4. Pull the latest changes from GitHub.
5. Install any new dependencies.
6. Restart the FastAPI backend.

## AMD Developer Cloud Experience

Working with the AMD Developer Cloud introduced me to cloud-based development environments and remote deployment. Instead of relying solely on a local machine, I learned how to prepare a backend that can run on dedicated cloud infrastructure, providing a foundation for deploying AI-enabled applications.

## Useful Commands

### SSH

```bash
ssh Mabooks-21@165.245.135.33

ssh root@165.245.135.33

ssh-keygen -t ed25519 -C "entrypoint-deploy-key" -f ~/.ssh/entrypoint_deploy_key
```

### Git

```bash
cd ~/EntryPoint

git pull
```

### Python Environment

```bash
python3 -m venv venv

source venv/bin/activate
```

### Installing Dependencies

```bash
pip install -r server/requirements.txt

pip install "pydantic[email]"
```

### Running the Backend

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

## Technical Growth

This project strengthened my understanding of:

* Linux command-line development.
* Remote server administration.
* SSH authentication and key management.
* Git-based deployment workflows.
* Python virtual environments.
* FastAPI backend deployment.
* Cloud-hosted application development.
* Building AI-enabled web applications using modern development tools.

These skills will be valuable for future software engineering projects involving cloud infrastructure, backend services, and AI deployment.
