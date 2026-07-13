import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  applicationsApi, documentsApi, queriesApi,
  type ApplicationDetail as AppDetailType,
  type Document, type Query, type ReadinessResult,
  type MultiUploadResponse, type AnalysisResult,
} from "../lib/api";
import { extractTextFromFiles } from "../lib/ocr";
import {
  ArrowLeft, Send, Loader2, FileText, CheckCircle2, AlertCircle,
  Clock, Brain, MessageCircle, ChevronDown, ChevronUp, X, FolderUp,
  FileUp,
} from "lucide-react";

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // General
  const [detail, setDetail] = useState<AppDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Multi file upload with OCR
  const [allFiles, setAllFiles] = useState<File[]>([]);
  const [uploadAllError, setUploadAllError] = useState("");
  const [ocrProgress, setOcrProgress] = useState<{ current: number; total: number; filename: string } | null>(null);
  const [ocrResults, setOcrResults] = useState<Map<string, { text: string; confidence: number }>>(new Map());

  // Readiness / bulk upload result
  const [readinessResult, setReadinessResult] = useState<ReadinessResult | null>(null);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [analysisDocuments, setAnalysisDocuments] = useState<AnalysisResult["classifications"]>([]);

  // Expanded requirement accordion
  const [expandedReq, setExpandedReq] = useState<string | null>(null);

  // Query
  const [queryMsg, setQueryMsg] = useState("");
  const [queryLoading, setQueryLoading] = useState(false);

  // Collapsible sections
  //const showAI = false; // const [showAI, setShowAI] = useState(false);
  const [showUploadAll, setShowUploadAll] = useState(false);

  // AI analysis mode modal
  const [showAIModal, setShowAIModal] = useState(false);
  const [aiMode, setAiMode] = useState<"all" | "new">("all");

  // Polled queries (live from server, separate from detail snapshot)
  const [liveQueries, setLiveQueries] = useState<Query[]>([]);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    try {
      const data = await applicationsApi.get(id);
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  // Poll queries every 10s for admin replies
  useEffect(() => {
    if (!id) return;
    const poll = async () => {
      try {
        const result = await queriesApi.list(id);
        setLiveQueries(result.queries);
      } catch {
        // silent – don't spam errors
      }
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, [id]);

  // Keep readiness result from the last bulk upload or analysis

  function handleAnalyzeAll() {
    setShowAIModal(true);
  }

  async function handleConfirmAnalyze() {
    if (!id) return;
    setShowAIModal(false);
    setActionLoading("analyze");
    try {
      const result = await applicationsApi.analyze(id, aiMode);
      setAnalysisMessage(result.message);
      setAnalysisDocuments(result.classifications);
      // Update readiness result with analysis response
      setReadinessResult({
        overall_score: result.readiness_score,
        summary: result.summary,
        passed: result.stats.passed,
        failed: result.stats.failed,
        missing: result.stats.missing,
        requirement_statuses: result.requirement_statuses || [],
      });
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleUploadAll() {
    if (!id || allFiles.length === 0) return;
    setUploadAllError("");
    setActionLoading("upload-all");
    try {
      // Step 1: Run client-side OCR on all files
      const supportedCount = allFiles.filter(
        (f) => /\.(png|jpg|jpeg|bmp|gif|webp|pdf)$/i.test(f.name)
      ).length;
      if (supportedCount > 0) {
        setOcrProgress({ current: 0, total: supportedCount, filename: "Starting OCR..." });
      }

      const texts = new Map<string, { text: string; confidence: number }>();
      let processed = 0;
      for (const file of allFiles) {
        const isSupported = /\.(png|jpg|jpeg|bmp|gif|webp|pdf)$/i.test(file.name);
        if (isSupported) {
          setOcrProgress({ current: processed + 1, total: supportedCount, filename: file.name });
          try {
            const result = await extractTextFromFiles([file]);
            const entry = result.get(file.name);
            if (entry) {
              texts.set(file.name, entry);
            }
          } catch (ocrErr) {
            console.warn(`OCR failed for ${file.name}:`, ocrErr);
          }
          processed++;
        }
      }
      setOcrProgress(null);
      setOcrResults(texts);

      // Step 2: Upload with OCR text attached
      const result: MultiUploadResponse = await documentsApi.uploadMultiple(id, allFiles, texts);
      setAllFiles([]);
      setOcrResults(new Map());
      // Store readiness result so we can show the breakdown UI
      setReadinessResult(result.readiness);
      await loadDetail();
    } catch (err) {
      setUploadAllError(err instanceof Error ? err.message : "Bulk upload failed");
    } finally {
      setActionLoading(null);
      setOcrProgress(null);
    }
  }

  function handleAddFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    setAllFiles((prev) => [...prev, ...files]);
    e.target.value = "";
  }

  function removeFileFromList(index: number) {
    setAllFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function toggleRequirement(label: string) {
    setExpandedReq((prev) => (prev === label ? null : label));
  }

  async function handleSendQuery() {
    if (!id || !queryMsg.trim()) return;
    setQueryLoading(true);
    try {
      await queriesApi.create(id, queryMsg.trim());
      setQueryMsg("");
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send query");
    } finally {
      setQueryLoading(false);
    }
  }

  // ── Loading State ─────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  // ── Error / Not Found ─────────────────────────────
  if (!detail) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
        <AlertCircle className="mx-auto mb-3 h-8 w-8 text-destructive" />
        <p className="font-medium text-destructive">{error || "Application not found"}</p>
        <button onClick={() => navigate("/dashboard")} className="mt-4 cursor-pointer text-sm text-accent underline">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const { application, requirements, documents } = detail;

  // Use polled queries if available, otherwise fall back to detail snapshot
  const queries = liveQueries.length > 0 ? liveQueries : detail.queries;

  // Group docs by requirement label
  const docsByReq: Record<string, Document[]> = {};
  for (const req of requirements) {
    docsByReq[req.requirement_label] = documents.filter(
      (d) => d.requirement_label === req.requirement_label
    );
  }

  // Map requirement labels to readiness statuses if we have readiness
  const readinessMap: Record<string, { status: string; matched_doc_name: string | null; issues?: string[] }> = {};
  if (readinessResult) {
    for (const rs of readinessResult.requirement_statuses) {
      readinessMap[rs.requirement_label] = { status: rs.status, matched_doc_name: rs.matched_doc_name, issues: rs.issues };
    }
  }

  // Count how many missing requirements still need files
  // const missingCount = readinessResult
  //   ? readinessResult.missing
  //   : requirements.filter((r) => (docsByReq[r.requirement_label] || []).length === 0).length;

  // Show AI-assessed score when available, otherwise the stored DB score
  const displayScore = readinessResult
    ? Math.round(readinessResult.overall_score)
    : Math.round(application.overall_score);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate("/dashboard")}
        className="flex cursor-pointer items-center gap-1 text-sm text-secondary transition-colors hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Applications
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-primary">
            {application.visa_type} Visa
          </h2>
          <p className="mt-1 text-secondary">
            {application.origin_country} → {application.destination_country}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`rounded-full border px-3 py-1 text-xs font-medium ${
            application.status === "approved" ? "border-emerald-200 bg-emerald-50 text-emerald-700" :
            application.status === "rejected" ? "border-red-200 bg-red-50 text-red-700" :
            application.status === "submitted" ? "border-blue-200 bg-blue-50 text-blue-700" :
            "border-amber-200 bg-amber-50 text-amber-700"
          }`}>
            {application.status.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Readiness Score Card (live from last AI assessment) */}
      <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="relative flex h-20 w-20 shrink-0 items-center justify-center">
            <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="oklch(0.9288 0.0126 255.51)" strokeWidth="3" />
              <circle
                cx="18" cy="18" r="15.5" fill="none" stroke="oklch(0.5 0.1193 242.75)"
                strokeWidth="3" strokeLinecap="round"
                strokeDasharray={`${displayScore * 0.97} ${100 - displayScore * 0.97}`}
              />
            </svg>
            <span className="absolute text-xl font-bold text-primary">
              {displayScore}%
            </span>
          </div>
          <div>
            <h3 className="font-heading text-xl font-bold text-primary">Readiness Score</h3>
            <p className="text-sm text-secondary">
              Based on {Array.isArray(documents) ? documents.length : 1} document{Array.isArray(documents) && documents.length !== 1 ? "s" : ""} uploaded across {requirements.length} requirements
            </p>
          </div>
        </div>

        {/* Summary + stats bar - only shown after AI assessment */}
        {readinessResult && (
          <>
            <p className="mt-4 border-t border-border pt-4 text-sm text-secondary leading-relaxed">
              {readinessResult.summary}
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
                ✅ {readinessResult.passed} passed
              </span>
              <span className="rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700">
                ❌ {readinessResult.failed} with issues
              </span>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-sm font-medium text-amber-700">
                ⏳ {readinessResult.missing} missing
              </span>
            </div>
            {/* Document-level issues summary */}
            {(() => {
              const issuesList = readinessResult.requirement_statuses.filter(
                (r) => r.status === "issues" && r.issues && r.issues.length > 0
              );
              if (issuesList.length === 0) return null;
              return (
                <div className="mt-3 space-y-1.5 border-t border-border pt-3">
                  <p className="text-xs font-semibold text-red-700">Documents with issues:</p>
                  {issuesList.map((r) => (
                    <div key={r.requirement_label} className="flex items-start gap-2 text-xs text-red-600">
                      <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                      <span>
                        <strong className="font-medium">{r.matched_doc_name || r.requirement_label}</strong>
                        {r.issues && r.issues.length > 0 && (
                          <>: {r.issues.slice(0, 2).join("; ")}</>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              );
            })()}
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${readinessResult.overall_score}%`,
                  backgroundColor: readinessResult.overall_score >= 70 ? "oklch(0.6 0.15 145)" :
                    readinessResult.overall_score >= 40 ? "oklch(0.65 0.17 85)" :
                    "oklch(0.58 0.18 25)",
                }}
              />
            </div>
          </>
        )}
        {!readinessResult && (
          <p className="mt-4 border-t border-border pt-4 text-sm text-secondary">
            {documents.length === 0
              ? "Upload documents and run AI analysis to check your readiness."
              : "Run AI analysis (below) to get a detailed readiness breakdown."}
          </p>
        )}
      </div>

      {analysisMessage && (
        <div className="rounded-lg border border-accent/20 bg-accent/5 px-4 py-3 text-sm font-medium text-primary">
          {analysisMessage}
        </div>
      )}
      {analysisDocuments.length > 0 && (
        <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <h3 className="font-heading text-base font-bold text-primary">AI document results</h3>
          <p className="mt-1 text-xs text-secondary">Every document sent to the AI is listed here.</p>
          <div className="mt-3 space-y-2">
            {analysisDocuments.map((item) => (
              <div key={item.document_id} className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
                <span className="font-medium text-primary">{item.document_name}</span>
                <span className="ml-2 text-secondary">→ {item.classified_as} ({Math.round(item.confidence * 100)}%)</span>
                {item.issues.length > 0 && <p className="mt-1 text-xs text-destructive">{item.issues.join("; ")}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleAnalyzeAll}
          disabled={actionLoading === "analyze"}
          className="flex cursor-pointer items-center gap-2 rounded-lg border border-accent bg-accent/5 px-5 py-2.5 font-semibold text-accent transition-all duration-150 hover:bg-accent/10 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {actionLoading === "analyze" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
          Run AI Analysis
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-2.5 text-sm text-destructive">{error}</div>
      )}

      {/* 📋 Requirements & Documents (Accordion) */}
      <div className="space-y-2">
        <h3 className="font-heading text-xl font-bold text-primary">Requirements & Documents</h3>
        {requirements.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-white p-8 text-center">
            <FileText className="mx-auto mb-2 h-8 w-8 text-secondary" />
            <p className="text-sm text-secondary">No requirements defined for this visa type</p>
          </div>
        ) : (
          requirements.map((req) => {
            const reqDocs = docsByReq[req.requirement_label] || [];
            const hasDoc = reqDocs.length > 0;
            //const classified = reqDocs.some((d) => d.document_classifications?.length);
            const allValid = reqDocs.every(
              (d) => d.document_classifications?.some((c) => !c.issues?.length)
            );
            const isExpanded = expandedReq === req.requirement_label;

            // Readiness status for this requirement
            const rs = readinessMap[req.requirement_label];
            const readyStatus = rs?.status || (hasDoc ? (allValid ? "matched" : "issues") : "missing");

            return (
              <div key={req.id} className="rounded-xl border border-border bg-white shadow-sm overflow-hidden">
                {/* Accordion Header */}
                <button
                  onClick={() => toggleRequirement(req.requirement_label)}
                  className="flex w-full cursor-pointer items-center justify-between px-5 py-4 text-left transition-colors hover:bg-muted/30"
                >
                  <div className="flex items-center gap-3">
                    <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${
                      readyStatus === "matched" ? "bg-success" :
                      readyStatus === "issues" ? "bg-amber-500" :
                      "bg-secondary"
                    }`}>
                      {readyStatus === "matched" ? <CheckCircle2 className="h-4 w-4" /> :
                       readyStatus === "issues" ? "!" :
                       req.sort_order}
                    </span>
                    <div>
                      <span className="font-medium text-primary">{req.requirement_label}</span>
                    </div>
                    {/* Readiness status badge with matched doc name */}
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                      readyStatus === "matched" ? "bg-emerald-100 text-emerald-800" :
                      readyStatus === "issues" ? "bg-amber-100 text-amber-800" :
                      "bg-rose-100 text-rose-800"
                    }`}>
                      {readyStatus === "matched" && rs?.matched_doc_name
                        ? `✓ ${rs.matched_doc_name}`
                        : readyStatus === "matched"
                          ? "✓ Valid"
                          : ""}
                      {readyStatus === "issues" && rs?.matched_doc_name
                        ? `⚠ ${rs.matched_doc_name}`
                        : readyStatus === "issues"
                          ? "⚠ Issues"
                          : ""}
                      {readyStatus === "missing" && "✗ Missing"}
                    </span>
                    {/* Show first issue inline when there are problems */}
                    {readyStatus === "issues" && rs?.issues && rs.issues.length > 0 && (
                      <span className="max-w-[200px] truncate text-[11px] text-amber-700 shrink-0" title={rs.issues[0]}>
                        {rs.issues[0]}
                      </span>
                    )}
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 shrink-0 text-secondary" />
                  ) : (
                    <ChevronDown className="h-4 w-4 shrink-0 text-secondary" />
                  )}
                </button>

                {/* Accordion Content */}
                {isExpanded && (
                  <div className="border-t border-border px-5 py-4">
                    {reqDocs.length === 0 ? (
                      <div className="rounded-lg bg-muted/50 p-6 text-center">
                        <FileText className="mx-auto mb-2 h-5 w-5 text-secondary" />
                        <p className="text-sm text-secondary">
                          No documents uploaded for this requirement yet.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {reqDocs.map((doc) => (
                          <div key={doc.id} className="rounded-lg border border-border bg-muted/20 p-3">
                            <div className="flex items-start gap-3">
                              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
                              <div className="flex-1 min-w-0">
                                <p className="truncate text-sm font-medium text-primary">{doc.file_name}</p>
                                {doc.document_classifications && doc.document_classifications.length > 0 ? (
                                  <div className="mt-2 space-y-1">
                                    {doc.document_classifications.map((c) => (
                                      <div key={c.id}>
                                        <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                                          c.issues?.length ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
                                        }`}>
                                          {c.classified_as} — {Math.round(c.confidence * 100)}% confident
                                        </span>
                                        {c.issues && c.issues.length > 0 && (
                                          <ul className="mt-1 space-y-0.5 pl-2">
                                            {c.issues.map((issue, i) => (
                                              <li key={i} className="flex items-start gap-1 text-xs text-red-600">
                                                <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                                                <span><strong className="font-medium">{doc.file_name}</strong>: {issue}</span>
                                              </li>
                                            ))}
                                          </ul>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="mt-1 flex items-center gap-1 text-xs text-amber-600">
                                    <Clock className="h-3 w-3" />
                                    Awaiting AI classification
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* 📤 Upload All Files Section */}
      <div className="rounded-xl border border-border bg-white shadow-sm">
        <button
          onClick={() => setShowUploadAll(!showUploadAll)}
          className="flex w-full cursor-pointer items-center justify-between px-6 py-4 transition-colors hover:bg-muted/50"
        >
          <div className="flex items-center gap-2">
            <FolderUp className="h-5 w-5 text-accent" />
            <span className="font-heading text-lg font-bold text-primary">Upload Files</span>
            <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
              {allFiles.length} selected
            </span>
          </div>
          {showUploadAll ? <ChevronUp className="h-4 w-4 text-secondary" /> : <ChevronDown className="h-4 w-4 text-secondary" />}
        </button>
        {showUploadAll && (
          <div className="border-t border-border px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">Select Files</label>
              <input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                onChange={handleAddFiles}
                className="w-full text-sm file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-accent/90"
              />
              <p className="mt-1 text-xs text-secondary">
                The AI will auto-classify and match each file to the right requirement.
              </p>
            </div>
            {allFiles.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-secondary">Files ready to upload:</p>
                {allFiles.map((f, i) => {
                  const ocrResult = ocrResults.get(f.name);
                  return (
                    <div key={i} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="h-3.5 w-3.5 shrink-0 text-secondary" />
                        <span className="truncate text-sm text-primary">{f.name}</span>
                        <span className="shrink-0 text-xs text-secondary">
                          ({(f.size / 1024 / 1024).toFixed(1)} MB)
                        </span>
                        {ocrResult && (
                          <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                            ocrResult.confidence > 80 ? "bg-emerald-100 text-emerald-800" :
                            ocrResult.confidence > 50 ? "bg-amber-100 text-amber-800" :
                            "bg-rose-100 text-rose-800"
                          }`}>
                            OCR: {ocrResult.confidence}%
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => removeFileFromList(i)}
                        className="ml-2 flex cursor-pointer items-center text-secondary hover:text-destructive transition-colors"
                        aria-label={`Remove ${f.name}`}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
            {uploadAllError && <p className="text-sm text-destructive">{uploadAllError}</p>}
            {ocrProgress ? (
              <div className="rounded-lg border border-accent/20 bg-accent/5 p-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="h-5 w-5 animate-spin text-accent" />
                  <div>
                    <p className="text-sm font-medium text-primary">Scanning documents with OCR...</p>
                    <p className="text-xs text-secondary">
                      {ocrProgress.current} of {ocrProgress.total}: {ocrProgress.filename}
                    </p>
                  </div>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-accent transition-all duration-300"
                    style={{ width: `${(ocrProgress.current / ocrProgress.total) * 100}%` }}
                  />
                </div>
              </div>
            ) : (
              <button
                onClick={handleUploadAll}
                disabled={allFiles.length === 0 || actionLoading === "upload-all"}
                className="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2 font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionLoading === "upload-all" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileUp className="h-4 w-4" />
                )}
                Upload {allFiles.length > 0 ? `${allFiles.length} file${allFiles.length !== 1 ? "s" : ""}` : "All Files"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Queries Section */}
      <div className="rounded-xl border border-border bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-border px-6 py-4">
          <MessageCircle className="h-5 w-5 text-accent" />
          <h3 className="font-heading text-lg font-bold text-primary">Queries ({queries.length})</h3>
        </div>
        <div className="px-6 py-4 space-y-4">
          {/* Query List */}
          {queries.length === 0 ? (
            <div className="rounded-lg bg-muted/50 p-6 text-center">
              <MessageCircle className="mx-auto mb-2 h-6 w-6 text-secondary" />
              <p className="text-sm text-secondary">No queries yet. Send a message to an EntryPoint advisor.</p>
            </div>
          ) : (
            queries.map((q) => (
              <div key={q.id} className="space-y-2">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/10">
                    <span className="text-xs font-bold text-accent">U</span>
                  </div>
                  <div className="flex-1 rounded-lg bg-muted px-4 py-3">
                    <p className="text-sm text-foreground">{q.message}</p>
                    <p className="mt-1 text-xs text-secondary">{new Date(q.created_at).toLocaleString()}</p>
                  </div>
                </div>
                {q.reply && (
                  <div className="flex items-start gap-3 pl-10">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <span className="text-xs font-bold text-primary">A</span>
                    </div>
                    <div className="flex-1 rounded-lg bg-primary/5 px-4 py-3">
                      <p className="text-sm text-foreground">{q.reply}</p>
                      {q.replied_at && (
                        <p className="mt-1 text-xs text-secondary">{new Date(q.replied_at).toLocaleString()}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {/* Query Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={queryMsg}
              onChange={(e) => setQueryMsg(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendQuery()}
              placeholder="Ask a question about your application..."
              className="flex-1 rounded-lg border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              onClick={handleSendQuery}
              disabled={!queryMsg.trim() || queryLoading}
              className="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 py-2.5 font-medium text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {queryLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* AI Analysis Mode Modal */}
      {showAIModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowAIModal(false)}>
          <div
            className="mx-4 w-full max-w-md rounded-xl border border-border bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-heading text-xl font-bold text-primary">AI Analysis Options</h3>
            <p className="mt-1 text-sm text-secondary">Choose how you want to run the analysis:</p>
            <div className="mt-4 space-y-3">
              <label className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors ${aiMode === "all" ? "border-accent bg-accent/5" : "border-border hover:bg-muted/30"}`}>
                <input
                  type="radio"
                  name="aiMode"
                  value="all"
                  checked={aiMode === "all"}
                  onChange={() => setAiMode("all")}
                  className="mt-0.5 accent-accent"
                />
                <div>
                  <span className="font-medium text-primary">Analyze all documents</span>
                  <p className="text-xs text-secondary">Re-analyze every uploaded document from scratch</p>
                </div>
              </label>
              <label className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors ${aiMode === "new" ? "border-accent bg-accent/5" : "border-border hover:bg-muted/30"}`}>
                <input
                  type="radio"
                  name="aiMode"
                  value="new"
                  checked={aiMode === "new"}
                  onChange={() => setAiMode("new")}
                  className="mt-0.5 accent-accent"
                />
                <div>
                  <span className="font-medium text-primary">Only unclassified documents</span>
                  <p className="text-xs text-secondary">Skip documents that already have AI classifications</p>
                </div>
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowAIModal(false)}
                className="cursor-pointer rounded-lg border border-border px-4 py-2 text-sm font-medium text-secondary transition-all duration-150 hover:bg-muted/50 active:scale-[0.97]"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAnalyze}
                className="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97]"
              >
                <Brain className="h-4 w-4" />
                {aiMode === "all" ? "Analyze All" : "Analyze New Only"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
