const API_BASE = "/api";

interface FetchOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string>;
}

async function request<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let url = `${API_BASE}${endpoint}`;
  if (options.params) {
    const searchParams = new URLSearchParams(options.params);
    url += `?${searchParams.toString()}`;
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const errorData = data as { detail?: string; message?: string };
    const detail = errorData.detail || errorData.message || "Request failed with status " + response.status;
    console.error("API request failed (" + response.status + ") for " + endpoint + ": " + detail);
    throw new Error(detail);
  }

  return data as T;
}

// ─── Auth ───────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  user_type: "applicant" | "admin";
  created_at?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export const authApi = {
  register: (email: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: { email, password },
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  me: () => request<User>("/auth/me"),
};

// ─── Reference Data ─────────────────────────────────

export interface Country {
  name: string;
  code: string;
}

export interface Requirement {
  id: string;
  visa_type: string;
  requirement_label: string;
  applies_to_all: boolean;
  applies_to_countries: string[];
  excluded_countries?: string[];
  sort_order: number;
  is_override?: boolean;
}

export const referenceApi = {
  countries: (search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return request<{ countries: Country[] }>("/reference/countries", { params });
  },
  visaTypes: () => request<{ visa_types: string[] }>("/reference/visa-types"),
  requirements: (visaType: string, destinationCountry?: string) => {
    const params: Record<string, string> = { visa_type: visaType };
    if (destinationCountry) params.destination_country = destinationCountry;
    return request<{ requirements: Requirement[] }>("/reference/requirements", { params });
  },
};

// ─── Applications ───────────────────────────────────

export interface VisaApplication {
  id: string;
  userid: string;
  visa_type: string;
  origin_country: string;
  destination_country: string;
  applicant_name: string;
  status: "in_progress" | "submitted" | "approved" | "rejected";
  overall_score: number;
  ai_summary?: string;
  created_at: string;
  updated_at?: string;
}

export interface Document {
  id: string;
  application_id: string;
  file_name: string;
  document_type: string;
  status: string;
  requirement_label?: string;
  public_url?: string;
  document_classifications?: DocumentClassification[];
}

export interface DocumentClassification {
  id: string;
  document_id: string;
  classified_as: string;
  confidence: number;
  details?: Record<string, unknown>;
  issues?: string[];
}

export interface Query {
  id: string;
  application_id: string;
  user_id: string;
  message: string;
  reply?: string;
  admin_id?: string;
  created_at: string;
  replied_at?: string;
  status?: "open" | "resolved";
  resolved_at?: string;
}

export interface ApplicationDetail {
  application: VisaApplication;
  requirements: Requirement[];
  documents: Document[];
  queries: Query[];
}

export interface RequirementStatus {
  requirement_label: string;
  status: "matched" | "issues" | "missing";
  matched_doc_name: string | null;
  classified_as: string | null;
  confidence: number;
  issues?: string[];
}

export interface ReadinessResult {
  overall_score: number;
  summary: string;
  passed: number;
  failed: number;
  missing: number;
  requirement_statuses: RequirementStatus[];
}

export interface MultiUploadResponse {
  message: string;
  documents: Document[];
  readiness: ReadinessResult;
  requirements: Requirement[];
}

export interface AnalysisResult {
  message: string;
  readiness_score: number;
  summary: string;
  classifications: Array<{
    document_id: string;
    document_name: string;
    classified_as: string;
    confidence: number;
    is_valid: boolean;
    issues: string[];
  }>;
  stats: {
    passed: number;
    failed: number;
    missing: number;
    analyzed: number;
    total_documents: number;
    analysis_errors: number;
  };
  requirement_statuses: RequirementStatus[];
}

export const applicationsApi = {
  create: (data: { visa_type: string; origin_country: string; destination_country: string; applicant_name?: string }) =>
    request<{ application: VisaApplication }>("/applications", {
      method: "POST",
      body: data,
    }),
  list: () => request<{ applications: VisaApplication[] }>("/applications"),
  get: (id: string) => request<ApplicationDetail>(`/applications/${id}`),
  submit: (id: string) =>
    request<AnalysisResult>(`/applications/${id}/submit`, { method: "POST" }),
  analyze: (id: string, mode: "all" | "new" = "all") =>
    request<AnalysisResult>(`/applications/${id}/analyze`, {
      method: "POST",
      params: { mode },
    }),
};

// ─── Documents ──────────────────────────────────────

export const documentsApi = {
  upload: async (applicationId: string, file: File, requirementLabel?: string) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    formData.append("file", file);
    if (requirementLabel) {
      formData.append("requirement_label", requirementLabel);
    }

    const response = await fetch(`${API_BASE}/applications/${applicationId}/documents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail || "Upload failed";
      console.error("Document upload failed (" + response.status + "): " + detail);
      throw new Error(detail);
    }
    return data;
  },
  uploadMultiple: async (
    applicationId: string,
    files: File[],
    ocrTexts?: Map<string, { text: string; confidence: number }>,
  ) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    // Send pre-extracted OCR text as JSON so the backend uses real text
    if (ocrTexts && ocrTexts.size > 0) {
      const textsObj: Record<string, { text: string; confidence: number }> = {};
      ocrTexts.forEach((val, key) => { textsObj[key] = val; });
      formData.append("extracted_texts", JSON.stringify(textsObj));
    }

    const response = await fetch(
      `${API_BASE}/applications/${applicationId}/documents/upload-multiple`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    );

    const data: MultiUploadResponse = await response.json();
    if (!response.ok) {
      const detail = (data as unknown as { detail: string }).detail || "Bulk upload failed";
      console.error("Bulk document upload failed (" + response.status + "): " + detail);
      throw new Error(detail);
    }
    return data;
  },
  list: (applicationId: string) =>
    request<{ documents: Document[] }>(`/applications/${applicationId}/documents`),
  delete: (documentId: string) =>
    request<{ message: string }>(`/applications/documents/${documentId}`, {
      method: "DELETE",
    }),
};

// ─── Queries ────────────────────────────────────────

export const queriesApi = {
  list: (applicationId: string) =>
    request<{ queries: Query[] }>(`/applications/${applicationId}/queries`),
  create: (applicationId: string, message: string) =>
    request<{ query: Query }>(`/applications/${applicationId}/queries`, {
      method: "POST",
      body: { message },
    }),
};

// ─── Admin ──────────────────────────────────────────

export interface AdminApplication extends VisaApplication {
  users?: { email: string; user_type: string };
}

export interface AdminQuery extends Query {
  users?: { email: string };
  visa_applications?: {
    visa_type: string;
    destination_country: string;
    origin_country: string;
  };
}

export interface AdminUser {
  id: string;
  email: string;
  user_type: string;
  created_at: string;
  application_count?: number;
}

export const adminApi = {
  applications: () => request<{ applications: AdminApplication[] }>("/admin/applications"),
  queries: () => request<{ queries: AdminQuery[] }>("/admin/queries"),
  replyToQuery: (queryId: string, reply: string) =>
    request<{ query: Query }>(`/queries/${queryId}/reply`, {
      method: "POST",
      body: { reply },
    }),
  setQueryResolution: (queryId: string, resolved: boolean) =>
    request<{ query: Query }>(`/queries/${queryId}/resolution`, {
      method: "PATCH",
      body: { resolved },
    }),
  requirements: (visaType?: string) => {
    const params: Record<string, string> = {};
    if (visaType) params.visa_type = visaType;
    return request<{ requirements: Requirement[] }>("/admin/requirements", { params });
  },
  createRequirement: (data: {
    visa_type: string;
    requirement_label: string;
    sort_order: number;
    scope: "all" | "include" | "exclude";
    countries: string[];
  }) =>
    request<{ message: string }>("/admin/requirements", {
      method: "POST",
      body: data,
    }),
  updateRequirement: (id: string, data: { visa_type: string; requirement_label: string; sort_order: number; scope: "all" | "include" | "exclude"; countries: string[] }) =>
    request<{ requirement: Requirement }>(`/admin/requirements/item/${id}`, { method: "PUT", body: data }),
  deleteRequirement: (id: string) =>
    request<{ message: string }>(`/admin/requirements/item/${id}`, { method: "DELETE" }),
  // Legacy country override endpoint retained for existing saved workflows.
  setRequirementsOverride: (data: { visa_type: string; country: string; requirements: Array<{ requirement_label: string; sort_order: number }> }) =>
    request<{ message: string }>("/admin/requirements/overrides", { method: "PUT", body: data }),
  users: () => request<{ users: AdminUser[] }>("/admin/users"),
};

// ─── Health ─────────────────────────────────────────

export const healthApi = {
  check: () => request<{ status: string; version: string }>("/health"),
};
