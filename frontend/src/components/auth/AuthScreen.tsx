import { FormEvent, useState } from "react";

import { loginAccount, registerAccount } from "../../api/client";
import type { AuthSession } from "../../types/auth";

type AuthScreenProps = {
  onAuthenticated: (session: AuthSession) => void;
  initialError?: string | null;
};

type Mode = "login" | "register";

export function AuthScreen({ onAuthenticated, initialError }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(initialError ?? null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "register" && password !== confirmPassword) {
      setError("As passwords do not match.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const session =
        mode === "login"
          ? await loginAccount({ email, password })
          : await registerAccount({ email, password, full_name: fullName.trim() || undefined });

      onAuthenticated(session);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-card">
        <div className="auth-copy">
          <span className="eyebrow">Restricted Access</span>
          <h1>AlphaView research desk</h1>
          <p>
            Sign in with a real database-backed account before using the dashboard, strategy tooling, or withdrawal
            controls.
          </p>
        </div>

        <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
          <button
            className={`auth-mode-button ${mode === "login" ? "active" : ""}`}
            onClick={() => setMode("login")}
            type="button"
          >
            Login
          </button>
          <button
            className={`auth-mode-button ${mode === "register" ? "active" : ""}`}
            onClick={() => setMode("register")}
            type="button"
          >
            Create account
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <label className="auth-field">
              <span>Full name</span>
              <input
                autoComplete="name"
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Rodrigo Silva"
                type="text"
                value={fullName}
              />
            </label>
          ) : null}

          <label className="auth-field">
            <span>Email</span>
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@alphaview.com"
              type="email"
              value={email}
            />
          </label>

          <label className="auth-field">
            <span>Password</span>
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 10 chars, upper/lower/number/symbol"
              type="password"
              value={password}
            />
          </label>

          {mode === "register" ? (
            <label className="auth-field">
              <span>Confirm password</span>
              <input
                autoComplete="new-password"
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Repeat your password"
                type="password"
                value={confirmPassword}
              />
            </label>
          ) : null}

          {error ? <p className="auth-error">{error}</p> : null}

          <button className="auth-submit" disabled={submitting} type="submit">
            {submitting ? "Please wait..." : mode === "login" ? "Enter dashboard" : "Create secure account"}
          </button>
        </form>

        <div className="auth-note">
          <strong>Important</strong>
          <p>
            PAPER trading remains the default. Any withdrawal flow depends on withdrawable cash being reconciled into
            the platform and on a completed Stripe Connect onboarding.
          </p>
        </div>
      </section>
    </div>
  );
}
