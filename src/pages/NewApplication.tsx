import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { applicationsApi } from "../lib/api";
import { COUNTRIES } from "../lib/countries";
import { Loader2, ArrowLeft, ArrowRight, Globe, FileText } from "lucide-react";

const VISA_TYPES = ["Tourist", "Work", "Study", "Permanent Residence", "Asylum Seeker"];

export default function NewApplication() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");

  const [originCountry, setOriginCountry] = useState("");
  const [destinationCountry, setDestinationCountry] = useState("");
  const [visaType, setVisaType] = useState("");
  const [applicantName, setApplicantName] = useState("");

  async function handleCreate() {
    if (!originCountry || !destinationCountry || !visaType) return;
    setError("");
    setIsCreating(true);
    try {
      const result = await applicationsApi.create({
        visa_type: visaType,
        origin_country: originCountry,
        destination_country: destinationCountry,
        applicant_name: applicantName || undefined,
      });
      navigate(`/applications/${result.application.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create application");
    } finally {
      setIsCreating(false);
    }
  }

  function CountrySelect({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
    const [search, setSearch] = useState("");
    const filtered = COUNTRIES.filter((c) => c.toLowerCase().includes(search.toLowerCase()));

    return (
      <div>
        <label className="block text-sm font-medium text-secondary mb-1">{label}</label>
        <input
          type="text"
          placeholder="Search countries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none mb-2 focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <div className="max-h-48 overflow-y-auto rounded-lg border border-border">
          {filtered.length === 0 ? (
            <div className="p-3 text-sm text-secondary">No countries match your search</div>
          ) : (
            filtered.map((country) => (
              <button
                key={country}
                type="button"
                onClick={() => { onChange(country); setSearch(""); }}
                className={`w-full cursor-pointer px-3 py-2 text-left text-sm transition-colors hover:bg-muted ${
                  value === country ? "bg-accent/10 font-medium text-accent" : "text-foreground"
                }`}
              >
                {country}
              </button>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl animate-fade-in">
      {/* Back */}
      <button
        onClick={() => navigate("/dashboard")}
        className="mb-6 flex cursor-pointer items-center gap-1 text-sm text-secondary transition-colors hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Applications
      </button>

      <div className="rounded-xl border border-border bg-white p-8 shadow-md">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <Globe className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold text-primary">New Visa Application</h2>
            <p className="text-sm text-secondary">Tell us about your visa plans</p>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="mb-8 flex items-center gap-2">
          <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
            step >= 1 ? "bg-accent text-white" : "bg-muted text-secondary"
          }`}>1</div>
          <div className={`h-px flex-1 ${step >= 2 ? "bg-accent" : "bg-border"}`} />
          <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
            step >= 2 ? "bg-accent text-white" : "bg-muted text-secondary"
          }`}>2</div>
        </div>

        {step === 1 && (
          <div className="space-y-5">
            <CountrySelect
              label="Origin Country"
              value={originCountry}
              onChange={setOriginCountry}
            />
            <CountrySelect
              label="Destination Country"
              value={destinationCountry}
              onChange={setDestinationCountry}
            />
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">Visa Type</label>
              <div className="grid grid-cols-2 gap-2">
                {VISA_TYPES.map((vt) => (
                  <button
                    key={vt}
                    type="button"
                    onClick={() => setVisaType(vt)}
                    className={`cursor-pointer rounded-lg border px-4 py-3 text-sm font-medium transition-all duration-150 active:scale-[0.97] ${
                      visaType === vt
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border text-secondary hover:border-accent/50 hover:text-accent"
                    }`}
                  >
                    {vt}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-4">
              <button
                type="button"
                disabled={!originCountry || !destinationCountry || !visaType}
                onClick={() => setStep(2)}
                className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent py-2.5 font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            {/* Summary */}
            <div className="rounded-lg bg-muted p-4">
              <h4 className="text-sm font-medium text-secondary mb-2">Application Summary</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-secondary">Origin:</span> <span className="font-medium">{originCountry}</span></div>
                <div><span className="text-secondary">Destination:</span> <span className="font-medium">{destinationCountry}</span></div>
                <div><span className="text-secondary">Visa Type:</span> <span className="font-medium">{visaType}</span></div>
              </div>
            </div>

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-secondary mb-1">
                Applicant Name <span className="text-xs text-border">(optional)</span>
              </label>
              <div className="relative">
                <FileText className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary" />
                <input
                  id="name"
                  type="text"
                  value={applicantName}
                  onChange={(e) => setApplicantName(e.target.value)}
                  placeholder="Full legal name"
                  className="w-full rounded-lg border border-border bg-background py-2.5 pl-10 pr-4 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-destructive/10 px-4 py-2.5 text-sm text-destructive">{error}</div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-border px-5 py-2.5 font-medium text-secondary transition-all duration-150 hover:bg-muted active:scale-[0.97]"
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <button
                type="button"
                disabled={isCreating}
                onClick={handleCreate}
                className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent py-2.5 font-semibold text-white transition-all duration-150 hover:bg-accent/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
                Create Application <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
