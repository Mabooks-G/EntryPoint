import { useEffect, useState, useCallback } from "react";
import {
  adminApi, referenceApi,
  type AdminApplication, type AdminQuery, type AdminUser, type Requirement,
} from "../lib/api";
import { COUNTRIES } from "../lib/countries";
import {
  Loader2, Users, FileText, MessageCircle, ClipboardList, Send,
  CheckCircle2, AlertCircle, Globe, Search, ArrowUpDown, ChevronDown,
} from "lucide-react";

type Tab = "applications" | "queries" | "requirements" | "users";

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>("applications");

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "applications", label: "Applications", icon: <FileText className="h-4 w-4" /> },
    { id: "queries", label: "Queries", icon: <MessageCircle className="h-4 w-4" /> },
    { id: "requirements", label: "Requirements", icon: <ClipboardList className="h-4 w-4" /> },
    { id: "users", label: "Users", icon: <Users className="h-4 w-4" /> },
  ];

  return (
    <div className="animate-fade-in space-y-8">
      <div>
        <h2 className="font-heading text-3xl font-bold text-primary">Admin Panel</h2>
        <p className="mt-1 text-secondary">Manage applications, queries, requirements, and users</p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 rounded-xl border border-border bg-muted p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex cursor-pointer items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150 active:scale-[0.97] ${
              tab === t.id ? "bg-white text-primary shadow-sm" : "text-secondary hover:text-primary"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "applications" && <AdminApplications />}
      {tab === "queries" && <AdminQueries />}
      {tab === "requirements" && <AdminRequirements />}
      {tab === "users" && <AdminUsers />}
    </div>
  );
}

/* ─── Applications Tab ───────────────────────── */
function AdminApplications() {
  const [apps, setApps] = useState<AdminApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    adminApi.applications()
      .then((r) => setApps(r.applications))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = apps.filter((a) =>
    a.visa_type.toLowerCase().includes(search.toLowerCase()) ||
    a.destination_country.toLowerCase().includes(search.toLowerCase()) ||
    a.users?.email.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <CenteredLoader />;

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search applications..."
          className="w-full rounded-lg border border-border bg-white py-2 pl-10 pr-4 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs font-medium text-secondary uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Applicant</th>
              <th className="px-4 py-3">Visa Type</th>
              <th className="px-4 py-3">From → To</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-secondary">No applications found</td></tr>
            ) : filtered.map((a) => (
              <tr key={a.id} className="transition-colors hover:bg-muted/50">
                <td className="px-4 py-3 font-medium text-primary">{a.users?.email || "—"}</td>
                <td className="px-4 py-3 text-secondary">{a.visa_type}</td>
                <td className="px-4 py-3 text-secondary">{a.origin_country} → {a.destination_country}</td>
                <td className="px-4 py-3"><span className="font-semibold">{Math.round(a.overall_score)}%</span></td>
                <td className="px-4 py-3">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                    a.status === "approved" ? "bg-emerald-50 text-emerald-700" :
                    a.status === "rejected" ? "bg-red-50 text-red-700" :
                    a.status === "submitted" ? "bg-blue-50 text-blue-700" :
                    "bg-amber-50 text-amber-700"
                  }`}>
                    {a.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-secondary">{new Date(a.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Queries Tab ────────────────────────────── */
function AdminQueries() {
  const [queries, setQueries] = useState<AdminQuery[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [sending, setSending] = useState<string | null>(null);

  const load = useCallback(() => {
    adminApi.queries()
      .then((r) => setQueries(r.queries))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleReply(queryId: string) {
    const reply = replyText[queryId]?.trim();
    if (!reply) return;
    setSending(queryId);
    try {
      await adminApi.replyToQuery(queryId, reply);
      setReplyText((prev) => ({ ...prev, [queryId]: "" }));
      await load();
    } catch (err) {
      console.error(err);
    } finally {
      setSending(null);
    }
  }

  async function handleResolve(queryId: string, resolved: boolean) {
    setSending(queryId);
    try {
      await adminApi.setQueryResolution(queryId, resolved);
      await load();
    } catch (err) {
      console.error(err);
    } finally {
      setSending(null);
    }
  }

  if (isLoading) return <CenteredLoader />;

  const unanswered = queries.filter((q) => !q.reply);
  const answered = queries.filter((q) => q.reply);

  return (
    <div className="space-y-6">
      {/* Unanswered */}
      <div>
        <h3 className="mb-3 font-heading text-lg font-bold text-primary flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-destructive" />
          Unanswered ({unanswered.length})
        </h3>
        {unanswered.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-white p-8 text-center">
            <CheckCircle2 className="mx-auto mb-2 h-6 w-6 text-success" />
            <p className="text-sm text-secondary">All queries have been answered</p>
          </div>
        ) : unanswered.map((q) => (
          <div key={q.id} className="mb-4 rounded-xl border border-destructive/20 bg-white p-5 shadow-sm">
            <div className="mb-2 flex items-start justify-between">
              <div>
                <span className="font-medium text-primary">{q.users?.email || "Unknown"}</span>
                {q.visa_applications && (
                  <span className="ml-2 text-sm text-secondary">
                    · {q.visa_applications.visa_type} → {q.visa_applications.destination_country}
                  </span>
                )}
              </div>
              <span className="text-xs text-secondary">{new Date(q.created_at).toLocaleString()}</span>
            </div>
            <div className="rounded-lg bg-muted px-4 py-3 text-sm">{q.message}</div>
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                value={replyText[q.id] || ""}
                onChange={(e) => setReplyText((p) => ({ ...p, [q.id]: e.target.value }))}
                onKeyDown={(e) => e.key === "Enter" && handleReply(q.id)}
                placeholder="Type your reply..."
                className="flex-1 rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary"
              />
              <button
                onClick={() => handleReply(q.id)}
                disabled={!replyText[q.id]?.trim() || sending === q.id}
                className="flex cursor-pointer items-center gap-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {sending === q.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Reply
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Answered */}
      {answered.length > 0 && (
        <div>
          <h3 className="mb-3 font-heading text-lg font-bold text-primary flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-success" />
            Answered ({answered.length})
          </h3>
          {answered.map((q) => (
            <div key={q.id} className="mb-3 rounded-xl border border-border bg-white p-5 shadow-sm">
              <div className="mb-2 flex items-start justify-between">
                <span className="font-medium text-primary">{q.users?.email || "Unknown"}</span>
                <span className="text-xs text-secondary">{new Date(q.created_at).toLocaleString()}</span>
              </div>
              <div className="rounded-lg bg-muted px-4 py-3 text-sm mb-2">{q.message}</div>
              <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm border border-emerald-200">
                <span className="text-xs font-medium text-emerald-700">Reply: </span>
                {q.reply}
              </div>
              <button
                onClick={() => handleResolve(q.id, q.status !== "resolved")}
                disabled={sending === q.id}
                className="mt-3 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-secondary hover:bg-muted"
              >
                {q.status === "resolved" ? "Reopen query" : "Mark as resolved"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Requirements Tab ───────────────────────── */
const VISA_TYPES = ["Tourist", "Work", "Study", "Permanent Residence", "Asylum Seeker"];
function AdminRequirements() {
  const [selectedVisa, setSelectedVisa] = useState("Tourist");
  const [selectedCountry, setSelectedCountry] = useState("");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [showEditor, setShowEditor] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [scope, setScope] = useState<"all" | "include" | "exclude">("all");
  const [countries, setCountries] = useState<string[]>([]);

  useEffect(() => {
    setIsLoading(true);
    adminApi.requirements(selectedVisa)
      .then((r) => setRequirements(r.requirements))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [selectedVisa]);

  async function handleSetOverride() {
    if (!selectedCountry) return;
    setSaving(true);
    setSaveMsg("");
    try {
      await adminApi.setRequirementsOverride({
        visa_type: selectedVisa,
        country: selectedCountry,
        requirements: requirements.map((r) => ({
          requirement_label: r.requirement_label,
          sort_order: r.sort_order,
        })),
      });
      setSaveMsg(`Requirements saved as override for ${selectedCountry}`);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function openEditor(requirement?: Requirement) {
    setEditingId(requirement?.id || null);
    setLabel(requirement?.requirement_label || "");
    const excluded = requirement?.excluded_countries || [];
    setScope(requirement?.applies_to_all ? (excluded.length ? "exclude" : "all") : "include");
    setCountries(requirement?.applies_to_all ? excluded : (requirement?.applies_to_countries || []));
    setShowEditor(true);
  }

  async function saveRequirement() {
    if (!label.trim()) { setSaveMsg("Requirement is required"); return; }
    if (scope !== "all" && countries.length === 0) { setSaveMsg("Select at least one country"); return; }
    setSaving(true);
    try {
      const payload = { visa_type: selectedVisa, requirement_label: label.trim(), sort_order: editingId ? (requirements.find((r) => r.id === editingId)?.sort_order || 0) : requirements.length, scope, countries };
      if (editingId) await adminApi.updateRequirement(editingId, payload);
      else await adminApi.createRequirement(payload);
      setShowEditor(false);
      setSaveMsg("Saved");
      const refreshed = await adminApi.requirements(selectedVisa);
      setRequirements(refreshed.requirements);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function deleteRequirement(requirement: Requirement) {
    if (!window.confirm("Delete this requirement?")) return;
    try {
      await adminApi.deleteRequirement(requirement.id);
      const refreshed = await adminApi.requirements(selectedVisa);
      setRequirements(refreshed.requirements);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-4">
        <div>
          <label className="block text-xs font-medium text-secondary mb-1">Visa Type</label>
          <select
            value={selectedVisa}
            onChange={(e) => setSelectedVisa(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none focus:border-primary"
          >
            {VISA_TYPES.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div className="hidden">
          <label className="block text-xs font-medium text-secondary mb-1">Override For Country</label>
          <select
            value={selectedCountry}
            onChange={(e) => setSelectedCountry(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none focus:border-primary"
          >
            <option value="">[ALL] — applies globally</option>
            {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <button
          onClick={() => openEditor()}
          className="self-end rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90"
        >
          Add Requirement
        </button>
      </div>

      {showEditor && (
        <div className="rounded-xl border border-accent/30 bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-secondary">Requirement *</label>
              <input value={label} onChange={(e) => setLabel(e.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-secondary">Applies To</label>
              <select value={scope} onChange={(e) => { setScope(e.target.value as "all" | "include" | "exclude"); setCountries([]); }} className="w-full rounded-lg border border-border px-3 py-2 text-sm">
                <option value="all">ALL</option>
                <option value="exclude">Excluding</option>
                <option value="include">Including</option>
              </select>
            </div>
            {scope !== "all" && (
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">Countries</label>
                <select multiple value={countries} onChange={(e) => setCountries(Array.from(e.target.selectedOptions, (option) => option.value))} className="h-28 w-full rounded-lg border border-border px-3 py-2 text-sm">
                  {COUNTRIES.map((country) => <option key={country} value={country}>{country}</option>)}
                </select>
              </div>
            )}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={saveRequirement} disabled={saving} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white">{saving ? "Saving..." : "Save Requirement"}</button>
            <button onClick={() => setShowEditor(false)} className="rounded-lg border border-border px-4 py-2 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <CenteredLoader /> : (
        <div className="overflow-hidden rounded-xl border border-border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-muted text-left text-xs font-medium text-secondary uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 w-12">#</th>
                <th className="px-4 py-3">Requirement</th>
                <th className="px-4 py-3">Applies To</th>
                <th className="px-4 py-3">Edit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {requirements.map((r) => (
                <tr key={r.id} className="transition-colors hover:bg-muted/50">
                  <td className="px-4 py-3 text-secondary">{r.sort_order}</td>
                  <td className="px-4 py-3 font-medium text-primary">{r.requirement_label}</td>
                  <td className="px-4 py-3 text-xs text-secondary">
                    {r.applies_to_all ? (
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700">
                        {r.excluded_countries?.length ? "[ALLex, " + r.excluded_countries.join(", ") + "]" : "[ALL]"}
                      </span>
                    ) : (
                      r.applies_to_countries?.join(", ") || "—"
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEditor(r)} className="mr-3 text-sm font-medium text-accent hover:underline">Edit</button>
                    <button onClick={() => deleteRequirement(r)} className="text-sm font-medium text-destructive hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedCountry && (
        <div className="flex items-center gap-3">
          <button
            onClick={handleSetOverride}
            disabled={saving}
            className="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Override for {selectedCountry}
          </button>
          {saveMsg && (
            <span className={`text-sm ${saveMsg.includes("saved") ? "text-success" : "text-destructive"}`}>
              {saveMsg}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Users Tab ──────────────────────────────── */
function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    adminApi.users()
      .then((r) => setUsers(r.users))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <CenteredLoader />;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-muted text-left text-xs font-medium text-secondary uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Applications</th>
            <th className="px-4 py-3">Joined</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {users.length === 0 ? (
            <tr><td colSpan={4} className="px-4 py-12 text-center text-secondary">No users found</td></tr>
          ) : users.map((u) => (
            <tr key={u.id} className="transition-colors hover:bg-muted/50">
              <td className="px-4 py-3 font-medium text-primary">{u.email}</td>
              <td className="px-4 py-3">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  u.user_type === "admin" ? "bg-purple-50 text-purple-700" : "bg-blue-50 text-blue-700"
                }`}>{u.user_type}</span>
              </td>
              <td className="px-4 py-3 text-secondary">{u.application_count ?? "—"}</td>
              <td className="px-4 py-3 text-xs text-secondary">{new Date(u.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CenteredLoader() {
  return (
    <div className="flex justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-accent" />
    </div>
  );
}
