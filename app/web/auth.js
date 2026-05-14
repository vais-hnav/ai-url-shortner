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
  openGuestCreateLink: document.getElementById("openGuestCreateLink"),
};
initShell();
let authRevealed = false;

if (window.matchMedia("(pointer: coarse)").matches) {
  el.enterAuthBtn.textContent = "Tap to enter";
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
  const loginInput = el.loginForm?.querySelector("input[name='email']");
  window.setTimeout(() => loginInput?.focus(), 260);
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

el.showLoginBtn.addEventListener("click", () => setAuthMode("login"));
el.showRegisterBtn.addEventListener("click", () => setAuthMode("register"));
el.showGuestBtn.addEventListener("click", () => setAuthMode("guest"));
el.enterAuthBtn.addEventListener("click", () => revealAuthPanel());
el.authHero.addEventListener("mousemove", () => revealAuthPanel(), { once: true });
el.authHero.addEventListener("touchstart", () => revealAuthPanel(), { once: true });
el.authHero.addEventListener("wheel", () => revealAuthPanel(), { once: true });
if (el.openGuestCreateLink) {
  el.openGuestCreateLink.addEventListener("click", () => setGuestSession(true));
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
    await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    showToast("Account created", "success");
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
    setFormError(el.loginError, userMessageFromError(err, "Login failed."));
    showToast("Login failed", "error");
  } finally {
    setButtonLoading(submitBtn, false);
  }
});
