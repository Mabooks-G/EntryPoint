# Database

EntryPoint uses Supabase PostgreSQL for persistent application data and Supabase Storage for uploaded files.

| Table | Purpose | Key data |
|---|---|---|
| users | Accounts | id, email, password, user_type |
| visa_applications | Visa application and latest result | visa_type, countries, status, overall_score, ai_summary |
| visa_requirements | Checklist per visa type | requirement_label, country scope, sort_order |
| documents | Uploaded-document state and OCR text | file_name, document_type, status, file_contents, storage_path |
| document_classifications | Saved AI result per document | classified_as, confidence, details, issues |
| queries | Applicant questions and admin replies | message, reply, admin_id, status, resolved_at |
| requirement_overrides | Legacy country-specific checklist data | country, visa_type, requirements |

## Requirement country scope

| Meaning | applies_to_all | applies_to_countries | excluded_countries |
|---|---:|---|---|
| Applies everywhere | true | [ALL] | [ALL] |
| Applies only to named countries | false | [Botswana,United States] | [ALL] |
| Applies everywhere except named countries | true | [ALL] | [ALLex,Botswana,United States] |

The database migration in backend/database/global_requirements_migration.sql adds query status, resolved time, and resolving administrator fields.

Each new completed analysis replaces the stored application score and AI summary. Successful document analysis saves a classification and retains the document classified status.

