import { FormEvent, useState } from "react";

import { loginAccount, registerAccount, resendVerificationCode, verifyEmailCode } from "../../api/client";
import type { AuthSession } from "../../types/auth";

type AuthScreenProps = {
  onAuthenticated: (session: AuthSession) => void;
  initialError?: string | null;
};

type Mode = "login" | "register";
type View = "credentials" | "verify";

export function AuthScreen({ onAuthenticated, initialError }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [view, setView] = useState<View>("credentials");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
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

      const challenge = await registerAccount({ email, password, full_name: fullName.trim() || undefined });
      setVerificationEmail(challenge.email);
      setVerificationCode("");
      setPassword("");
      setConfirmPassword("");
      setView("verify");
      setSuccess(challenge.message);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Authentication failed.";
      if (message === "Verify your email before signing in.") {
        setVerificationEmail(email);
        setView("verify");
        setSuccess(`Enter the confirmation code sent to ${email}.`);
      }
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setSubmitting(true);
      setError(null);
      const session = await verifyEmailCode({ email: verificationEmail, code: verificationCode });
      onAuthenticated(session);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Email verification failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResendCode() {
    try {
      setSubmitting(true);
      setError(null);
      const challenge = await resendVerificationCode({ email: verificationEmail });
      setSuccess(challenge.message);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not resend the confirmation code.");
    } finally {
      setSubmitting(false);
    }
  }

  function activateMode(nextMode: Mode) {
    setMode(nextMode);
    setView("credentials");
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
            <p>
              Enter through a verified account and move from research to paper execution inside a controlled operating
              surface.
            </p>
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
              <p>Registration and verification are real; default trade routing still remains simulation-only.</p>
            </article>
            <article className="auth-stage-card">
              <span className="metric-label">Identity</span>
              <strong>Email-gated access</strong>
              <p>Each operator account needs confirmation before the dashboard and payout controls unlock.</p>
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

          {view === "credentials" ? (
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
          ) : (
            <form className="auth-form" onSubmit={handleVerifySubmit}>
              <label className="auth-field">
                <span>Email</span>
                <input readOnly type="email" value={verificationEmail} />
              </label>

              <label className="auth-field">
                <span>Confirmation code</span>
                <input
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  onChange={(event) => setVerificationCode(event.target.value)}
                  placeholder="6-digit code"
                  type="text"
                  value={verificationCode}
                />
              </label>

              {error ? <p className="auth-error">{error}</p> : null}
              {success ? <p className="auth-success">{success}</p> : null}

              <button className="auth-submit" disabled={submitting} type="submit">
                {submitting ? "Verifying..." : "Confirm email"}
              </button>

              <div className="action-row">
                <button className="ghost-button" disabled={submitting} onClick={handleResendCode} type="button">
                  Resend code
                </button>
                <button
                  className="ghost-button"
                  disabled={submitting}
                  onClick={() => {
                    setView("credentials");
                    setMode("login");
                    setError(null);
                    setSuccess(null);
                  }}
                  type="button"
                >
                  Back to login
                </button>
              </div>
            </form>
          )}

          <div className="auth-note">
            <strong>Important</strong>
            <p>
              PAPER trading remains the default. Registration now requires email confirmation, and payout flows still
              depend on a completed Stripe Connect onboarding.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
