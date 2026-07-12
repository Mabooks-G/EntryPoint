import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Loader2, Mail, Lock, ArrowRight, User } from "lucide-react";
import logo2 from "../assets/logo2.png";

// Replace these with the email and password of the demo applicant in Supabase.
const USER_DEMO_EMAIL = "demo-user@entrypoint.com";
const USER_DEMO_PASSWORD = "123456";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAdminDemo() {
    setError("");
    setIsLoading(true);
    try {
      await login("admin@entrypoint.com", "123456");
      navigate("/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin demo login failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUserDemo() {
    setError("");
    setIsLoading(true);
    try {
      await login(USER_DEMO_EMAIL, USER_DEMO_PASSWORD);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "User demo login failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo / Brand */}
        <div className="mb-8 text-center">
          <img src={logo2} alt="EntryPoint" className="mx-auto mb-4 h-16 w-16 rounded-2xl object-contain shadow-lg" />
          <h1 className="font-heading text-4xl font-bold text-primary">EntryPoint</h1>
          <p className="mt-2 text-secondary">Global Visa AI Assistant</p>
        </div>

        {/* Form Card */}
        <div className="rounded-xl border border-border bg-white p-8 shadow-md">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-secondary">
                Email
              </label>
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-lg border border-border bg-background py-2.5 pl-10 pr-4 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-secondary">
                Password
              </label>
              <div className="relative mt-1">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-border bg-background py-2.5 pl-10 pr-4 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-destructive/10 px-4 py-2.5 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-primary py-2.5 font-semibold text-white shadow-md transition-all duration-150 hover:bg-primary/90 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isRegister ? "Create Account" : "Sign In"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Toggle Register / Login */}
          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="cursor-pointer text-sm text-accent transition-colors hover:text-accent/80"
            >
              {isRegister ? "Already have an account? Sign in" : "Don't have an account? Register"}
            </button>
          </div>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-secondary">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Admin Demo Button */}
          <button
            type="button"
            onClick={handleAdminDemo}
            disabled={isLoading}
            className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-accent bg-accent/5 py-2.5 font-semibold text-accent transition-all duration-150 hover:bg-accent/10 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Lock className="h-4 w-4" />
            Admin Demo
          </button>
          <p className="mt-2 text-center text-xs text-secondary">
            One-click login as admin — view all applications, manage requirements & reply to queries
          </p>
          <button
            type="button"
            onClick={handleUserDemo}
            disabled={isLoading}
            className="mt-4 flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-primary bg-primary/5 py-2.5 font-semibold text-primary transition-all duration-150 hover:bg-primary/10 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <User className="h-4 w-4" />
            User Demo
          </button>
          <p className="mt-2 text-center text-xs text-secondary">
            One-click login as an applicant — create and track visa applications.
          </p>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-secondary">
          EntryPoint processes all documents securely via encrypted channels.
        </p>
      </div>
    </div>
  );
}
