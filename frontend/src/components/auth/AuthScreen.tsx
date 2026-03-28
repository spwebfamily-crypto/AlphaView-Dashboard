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
  const [success, setSuccess] = useState<string | null>(null);

  async function handleCredentialSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "register" && password !== confirmPassword) {
      setError("As passwords do not match.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);

      if (mode === "login") {
        const session = await loginAccount({ email, password });
        onAuthenticated(session);
        return;
      }

      const session = await registerAccount({ email, password, full_name: fullName.trim() || undefined });
      onAuthenticated(session);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Authentication failed.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  function activateMode(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
    setSuccess(null);
  }

  return (
    <div className="auth-shell">
      <section className="auth-card auth-card-shell">
        <div className="auth-stage">
          <div className="auth-copy">
            <span className="eyebrow">Restricted Access</span>
            <h1>AlphaView command grid</h1>
            <p>Enter through your operator account and move from research to paper execution inside a controlled operating surface.</p>
          </div>

          <div className="auth-stage-grid">
            <article className="auth-stage-card">
              <span className="metric-label">Research</span>
              <strong>Provider-backed market context</strong>
              <p>Charts, signals, backtests, and model state stay visible in the same workflow.</p>
            </article>
            <article className="auth-stage-card">
              <span className="metric-label">Safety</span>
              <strong>Paper execution first</strong>
              <p>Registration is immediate; default trade routing still remains simulation-only.</p>
            </article>
            <article className="auth-stage-card">
              <span className="metric-label">Identity</span>
              <strong>Direct account access</strong>
              <p>Each operator account signs in directly before the dashboard and payout controls unlock.</p>
            </article>
          </div>

          <div className="auth-stage-note">
            <span className="metric-label">Protocol</span>
            <p>
              This platform is positioned as a research and paper-trading product. Backtests and signals are decision
              support, not promises of future returns.
            </p>
          </div>
        </div>

        <div className="auth-panel">
          <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
            <button
              className={`auth-mode-button ${mode === "login" ? "active" : ""}`}
              onClick={() => activateMode("login")}
              type="button"
            >
              Login
            </button>
            <button
              className={`auth-mode-button ${mode === "register" ? "active" : ""}`}
              onClick={() => activateMode("register")}
              type="button"
            >
              Create account
            </button>
          </div>

          <form className="auth-form" onSubmit={handleCredentialSubmit}>
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
            {success ? <p className="auth-success">{success}</p> : null}

            <button className="auth-submit" disabled={submitting} type="submit">
              {submitting ? "Please wait..." : mode === "login" ? "Enter dashboard" : "Create secure account"}
            </button>
          </form>

          <div className="auth-note">
            <strong>Important</strong>
            <p>
              PAPER trading remains the default. Registration enters the dashboard immediately, and payout flows still
              depend on a completed Stripe Connect onboarding.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
