import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { applicationsApi, type VisaApplication } from "../lib/api";
import { Plus, FileText, Loader2, ArrowRight, AlertCircle, CheckCircle2, Clock } from "lucide-react";

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string; classes: string }> = {
  in_progress: { icon: <Clock className="h-3.5 w-3.5" />, label: "In Progress", classes: "bg-amber-50 text-amber-700 border-amber-200" },
  submitted: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, label: "Submitted", classes: "bg-blue-50 text-blue-700 border-blue-200" },
  approved: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, label: "Approved", classes: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  rejected: { icon: <AlertCircle className="h-3.5 w-3.5" />, label: "Rejected", classes: "bg-red-50 text-red-700 border-red-200" },
};

export default function Dashboard() {
  const [applications, setApplications] = useState<VisaApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    applicationsApi
      .list()
      .then((res) => setApplications(res.applications))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-primary">My Applications</h2>
          <p className="mt-1 text-secondary">
            {applications.length === 0
              ? "Start your visa journey — create your first application"
              : `You have ${applications.length} visa application${applications.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <Link
          to="/applications/new"
          className="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-semibold text-white shadow-md transition-all duration-150 hover:bg-accent/90 active:scale-[0.97]"
        >
          <Plus className="h-4 w-4" />
          New Application
        </Link>
      </div>

      {/* Empty State */}
      {applications.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-white py-20">
          <FileText className="mb-4 h-12 w-12 text-secondary" />
          <h3 className="text-lg font-semibold text-primary">No applications yet</h3>
          <p className="mt-1 text-sm text-secondary">
            Create your first visa application to get started with EntryPoint
          </p>
          <Link
            to="/applications/new"
            className="mt-6 flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97]"
          >
            <Plus className="h-4 w-4" />
            Create Application
          </Link>
        </div>
      )}

      {/* Application Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {applications.map((app) => {
          const status = STATUS_CONFIG[app.status] || STATUS_CONFIG.in_progress;
          return (
            <Link
              key={app.id}
              to={`/applications/${app.id}`}
              className="group cursor-pointer rounded-xl border border-border bg-white p-6 shadow-sm transition-all duration-150 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-heading text-xl font-bold text-primary">
                    {app.visa_type} Visa
                  </h3>
                  <p className="mt-1 text-sm text-secondary">
                    {app.origin_country} → {app.destination_country}
                  </p>
                </div>
                <div className={`flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${status.classes}`}>
                  {status.icon}
                  {status.label}
                </div>
              </div>

              {/* Score Bar */}
              <div className="mt-4">
                <div className="flex items-center justify-between text-xs text-secondary">
                  <span>Readiness Score</span>
                  <span className="font-semibold">{Math.round(app.overall_score)}%</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-accent transition-all duration-500"
                    style={{ width: `${app.overall_score}%` }}
                  />
                </div>
              </div>

              <div className="mt-4 flex items-center gap-1 text-xs text-accent opacity-0 transition-opacity group-hover:opacity-100">
                View Details <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}