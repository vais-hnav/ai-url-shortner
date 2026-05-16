const el = {
  authExperience: document.getElementById("authExperience"),
  authHero: document.getElementById("authHero"),
  authDrawer: document.getElementById("authDrawer"),
  enterAuthBtn: document.getElementById("enterAuthBtn"),
  showLoginBtn: document.getElementById("showLoginBtn"),
  showRegisterBtn: document.getElementById("showRegisterBtn"),
  showGuestBtn: document.getElementById("showGuestBtn"),
  loginSection: document.getElementById("loginSection"),
  registerSection: document.getElementById("registerSection"),
  guestSection: document.getElementById("guestSection"),
  registerForm: document.getElementById("registerForm"),
  loginForm: document.getElementById("loginForm"),
  registerError: document.getElementById("registerError"),
  loginError: document.getElementById("loginError"),
  resendForm: document.getElementById("resendForm"),
  resendEmailInput: document.getElementById("resendEmailInput"),
  resendError: document.getElementById("resendError"),
  authStatusBanner: document.getElementById("authStatusBanner"),
  authActionSlot: document.getElementById("authActionSlot"),
  loginGoogleBtn: document.getElementById("loginGoogleBtn"),
  registerGoogleBtn: document.getElementById("registerGoogleBtn"),
  loginDivider: document.getElementById("loginDivider"),
  registerDivider: document.getElementById("registerDivider"),
  openGuestCreateLink: document.getElementById("openGuestCreateLink"),
};
initShell();
let authRevealed = false;
const isCoarsePointer = window.matchMedia("(pointer: coarse)").matches;

if (isCoarsePointer) {
  el.enterAuthBtn.textContent = "Tap to enter";
} else {
  el.enterAuthBtn.textContent = "Move to bottom";
}

function revealAuthPanel({ focusMode = null } = {}) {
  if (focusMode) {
    setAuthMode(focusMode);
  }
  if (authRevealed) {
    if (focusMode === "login") {
      const loginInput = el.loginForm?.querySelector("input[name='email']");
      loginInput?.focus();
    }
    return;
  }
  authRevealed = true;
  document.body.classList.add("auth-revealed");
  el.enterAuthBtn.textContent = isCoarsePointer ? "Tap to enter" : "Move to top to close";
  const loginInput = el.loginForm?.querySelector("input[name='email']");
  window.setTimeout(() => loginInput?.focus(), 260);
}

function collapseAuthPanel() {
  if (!authRevealed) return;
  authRevealed = false;
  document.body.classList.remove("auth-revealed");
  el.enterAuthBtn.textContent = isCoarsePointer ? "Tap to enter" : "Move to bottom";
}

function setAuthMode(mode) {
  el.loginSection.classList.toggle("hidden", mode !== "login");
  el.registerSection.classList.toggle("hidden", mode !== "register");
  el.guestSection.classList.toggle("hidden", mode !== "guest");
  el.showLoginBtn.classList.toggle("active", mode === "login");
  el.showRegisterBtn.classList.toggle("active", mode === "register");
  el.showGuestBtn.classList.toggle("active", mode === "guest");
  el.showLoginBtn.setAttribute("aria-selected", String(mode === "login"));
  el.showRegisterBtn.setAttribute("aria-selected", String(mode === "register"));
  el.showGuestBtn.setAttribute("aria-selected", String(mode === "guest"));
}

function setAuthStatus(message = "", tone = "info") {
  if (!message) {
    el.authStatusBanner.classList.add("hidden");
    el.authStatusBanner.textContent = "";
    el.authStatusBanner.dataset.tone = "";
    return;
  }
  el.authStatusBanner.textContent = message;
  el.authStatusBanner.dataset.tone = tone;
  el.authStatusBanner.classList.remove("hidden");
}

function setAuthActionLink(label = "", href = "") {
  if (!label || !href) {
    el.authActionSlot.classList.add("hidden");
    el.authActionSlot.innerHTML = "";
    return;
  }
  el.authActionSlot.innerHTML = `<a class="ghost auth-inline-link" href="${escapeHTML(href)}">${escapeHTML(label)}</a>`;
  el.authActionSlot.classList.remove("hidden");
}

function prefillEmail(email) {
  const normalized = String(email || "").trim();
  if (!normalized) return;
  const loginEmail = el.loginForm?.querySelector("input[name='email']");
  const registerEmail = el.registerForm?.querySelector("input[name='email']");
  if (loginEmail) loginEmail.value = normalized;
  if (registerEmail) registerEmail.value = normalized;
  if (el.resendEmailInput) el.resendEmailInput.value = normalized;
}

function startGoogleAuth() {
  window.location.href = "/auth/google/login";
}

async function loadAuthStatus() {
  try {
    const status = await api("/auth/status");
    const enabled = Boolean(status.google_oauth_enabled);
    [el.loginGoogleBtn, el.registerGoogleBtn].forEach((node) => {
      if (!node) return;
      node.disabled = !enabled;
      node.classList.toggle("is-disabled", !enabled);
      node.setAttribute("aria-disabled", String(!enabled));
    });
    [el.loginDivider, el.registerDivider].forEach((node) => {
      if (!node) return;
      node.classList.remove("hidden");
    });
    if (status.debug_mode && !status.mail_enabled) {
      setAuthStatus(
        "Email delivery is not configured in this environment yet. Debug verification links will be shown after signup or resend.",
        "info"
      );
    } else if (!enabled) {
      setAuthStatus("Google sign in is not configured yet.", "info");
    }
  } catch {
    [el.loginGoogleBtn, el.registerGoogleBtn].forEach((node) => {
      if (!node) return;
      node.disabled = true;
      node.classList.add("is-disabled");
    });
  }
}

function handleAuthQueryState() {
  const searchParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = String(hashParams.get("token") || searchParams.get("token") || "").trim();
  const oauthState = String(hashParams.get("oauth") || searchParams.get("oauth") || "").trim();
  const verified = String(searchParams.get("verified") || "").trim();
  const message = String(searchParams.get("message") || "").trim();
  const mode = String(searchParams.get("mode") || "").trim();

  if (token) {
    setToken(token);
    setGuestSession(false);
    showToast("Signed in successfully", "success");
    window.location.href = "/web/index.html";
    return;
  }

  if (mode === "login" || verified === "1" || oauthState === "error") {
    revealAuthPanel({ focusMode: "login" });
  }

  if (verified === "1") {
    setAuthStatus("Email verified. You can sign in now.", "success");
    setAuthActionLink();
  } else if (verified === "0") {
    setAuthStatus(message || "Verification link could not be completed.", "error");
    setAuthActionLink();
  } else if (oauthState === "error") {
    setAuthStatus(message || "Google sign in failed.", "error");
    setAuthActionLink();
  }
}

function handlePointerReveal(event) {
  if (isCoarsePointer || !event || typeof event.clientY !== "number") return;
  const height = window.innerHeight || document.documentElement.clientHeight || 0;
  if (!height) return;
  const openZone = height * 0.95;
  const closeZone = height * 0.3;
  if (!authRevealed && event.clientY >= openZone) {
    revealAuthPanel();
  } else if (authRevealed && event.clientY <= closeZone) {
    collapseAuthPanel();
  }
}

el.showLoginBtn.addEventListener("click", () => setAuthMode("login"));
el.showRegisterBtn.addEventListener("click", () => setAuthMode("register"));
el.showGuestBtn.addEventListener("click", () => setAuthMode("guest"));
el.enterAuthBtn.addEventListener("click", () => revealAuthPanel());
window.addEventListener("pointermove", handlePointerReveal, { passive: true });
if (el.openGuestCreateLink) {
  el.openGuestCreateLink.addEventListener("click", () => setGuestSession(true));
}
if (el.loginGoogleBtn) {
  el.loginGoogleBtn.addEventListener("click", startGoogleAuth);
}
if (el.registerGoogleBtn) {
  el.registerGoogleBtn.addEventListener("click", startGoogleAuth);
}

el.registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.registerForm.querySelector("button[type='submit']");
  setFormError(el.registerError, "");
  const fd = new FormData(el.registerForm);
  const payload = { email: fd.get("email"), password: fd.get("password") };
  if (String(payload.password).length < 8) {
    setFormError(el.registerError, "Password should be at least 8 characters.");
    return;
  }
  try {
    setButtonLoading(submitBtn, true, "Registering...");
    const data = await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    setAuthStatus(data.message || "Account created. Check your email to verify it.", "success");
    setAuthActionLink(
      data.verification_url ? "Open verification link" : "",
      data.verification_url || ""
    );
    prefillEmail(String(payload.email || ""));
    setAuthMode("login");
    revealAuthPanel({ focusMode: "login" });
    showToast("Verification email sent", "success");
    el.registerForm.reset();
  } catch (err) {
    setFormError(el.registerError, userMessageFromError(err, "Registration failed."));
    showToast("Registration failed", "error");
  } finally {
    setButtonLoading(submitBtn, false);
  }
});

el.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.loginForm.querySelector("button[type='submit']");
  setFormError(el.loginError, "");
  const fd = new FormData(el.loginForm);
  const payload = { email: fd.get("email"), password: fd.get("password") };
  try {
    setButtonLoading(submitBtn, true, "Signing in...");
    const data = await api("/auth/login", { method: "POST", body: JSON.stringify(payload) });
    setToken(data.access_token);
    setGuestSession(false);
    showToast("Logged in", "success");
    window.location.href = "/web/index.html";
  } catch (err) {
    const message = userMessageFromError(err, "Login failed.");
    setFormError(el.loginError, message);
    if (/verify your email/i.test(message)) {
      prefillEmail(String(payload.email || ""));
      setAuthStatus("Your account exists, but email verification is still pending.", "info");
    }
    setAuthActionLink();
    showToast("Login failed", "error");
  } finally {
    setButtonLoading(submitBtn, false);
  }
});

el.resendForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.resendForm.querySelector("button[type='submit']");
  setFormError(el.resendError, "");
  const fd = new FormData(el.resendForm);
  const payload = { email: fd.get("email") };
  try {
    setButtonLoading(submitBtn, true, "Sending...");
    const data = await api("/auth/verify/resend", { method: "POST", body: JSON.stringify(payload) });
    setAuthStatus(data.message || "Verification email sent.", "success");
    setAuthActionLink(
      data.verification_url ? "Open verification link" : "",
      data.verification_url || ""
    );
    showToast("Verification email sent", "success");
  } catch (err) {
    setFormError(el.resendError, userMessageFromError(err, "Unable to resend verification email."));
    setAuthActionLink();
    showToast("Resend failed", "error");
  } finally {
    setButtonLoading(submitBtn, false);
  }
});

handleAuthQueryState();
loadAuthStatus();
