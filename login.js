// =====================================================================
// login.js — Auth modal system, JWT handling, nav state
// =====================================================================

const API_BASE = "http://127.0.0.1:5000";

async function apiFetch(url, options = {}) {
  const token = localStorage.getItem("jwt");
  options.headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) options.headers["Authorization"] = `Bearer ${token}`;
  try {
    const res  = await fetch(API_BASE + url, options);
    const json = await res.json();
    if (res.status === 202) return { _status202: true, data: json.data };
    if (!json.success) throw new Error(json.message || "Request failed");
    return json.data;
  } catch (err) {
    if (err instanceof SyntaxError) throw new Error("Connection error. Please try again.");
    throw err;
  }
}

function parseJwt(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch { return null; }
}

function updateNav(fullName, role) {
  const actions = document.querySelector(".actions");
  if (!actions) return;
  let adminLink = role === "admin" ? `<a href="admin.html" class="btn outline" style="margin-right:8px">Admin Dashboard</a>` : "";
  actions.innerHTML = `
    ${adminLink}
    <span style="font-weight:600;margin-right:12px;color:#e2e2f0;">Welcome, ${fullName}</span>
    <button class="btn outline" onclick="logout()">Logout</button>`;
}

function restoreGuestNav() {
  const actions = document.querySelector(".actions");
  if (!actions) return;
  actions.innerHTML = `
    <button class="btn outline" onclick="openLogin()">Login</button>
    <button class="btn primary" onclick="openRegister()">Register</button>`;
}

function restoreAuthState() {
  const token = localStorage.getItem("jwt");
  if (!token) return;
  const payload = parseJwt(token);
  if (!payload) { localStorage.removeItem("jwt"); return; }
  if (payload.exp && payload.exp < Date.now() / 1000) { localStorage.removeItem("jwt"); return; }
  updateNav(payload.full_name, payload.role);
}

function logout() {
  localStorage.removeItem("jwt");
  restoreGuestNav();
  window.dispatchEvent(new Event("auth:logout"));
}

function openLogin() {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  showLogin();
  modal.style.display = "flex";
}

function openRegister() {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  showRegister();
  modal.style.display = "flex";
}

function closeModal() {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  modal.style.display = "none";
  clearAuthForms();
}

function clearAuthForms() {
  ["loginForm", "registerForm"].forEach(id => { const f = document.getElementById(id); if (f) f.reset(); });
  setAuthError("");
}

function showLogin() {
  const loginForm    = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  if (loginForm)    loginForm.style.display    = "block";
  if (registerForm) registerForm.style.display = "none";
  setAuthError("");
  document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
  const loginTab = document.getElementById("tabLogin");
  if (loginTab) loginTab.classList.add("active");
}

function showRegister() {
  const loginForm    = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  if (loginForm)    loginForm.style.display    = "none";
  if (registerForm) registerForm.style.display = "block";
  setAuthError("");
  document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
  const regTab = document.getElementById("tabRegister");
  if (regTab) regTab.classList.add("active");
}

function setAuthError(msg) {
  const el = document.getElementById("authError");
  if (!el) return;
  el.textContent = msg;
  el.style.display = msg ? "block" : "none";
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const form = document.getElementById("loginForm");
  const btn  = form.querySelector("button[type=submit]");
  const email    = form.querySelector("input[type=email]").value.trim();
  const password = form.querySelector("input[type=password]").value;
  setAuthError(""); btn.disabled = true; btn.textContent = "Logging in…";
  try {
    const data = await apiFetch("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    localStorage.setItem("jwt", data.token);
    updateNav(data.full_name, data.role);
    closeModal();
    window.dispatchEvent(new CustomEvent("auth:login", { detail: data }));
  } catch (err) { setAuthError(err.message); }
  finally { btn.disabled = false; btn.textContent = "Login"; }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const form = document.getElementById("registerForm");
  const btn  = form.querySelector("button[type=submit]");
  const inputs   = form.querySelectorAll("input");
  const fullName = inputs[0].value.trim();
  const email    = inputs[1].value.trim();
  const password = inputs[2].value;
  setAuthError(""); btn.disabled = true; btn.textContent = "Creating account…";
  try {
    await apiFetch("/api/auth/register", { method: "POST", body: JSON.stringify({ full_name: fullName, email, password }) });
    const data = await apiFetch("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    localStorage.setItem("jwt", data.token);
    updateNav(data.full_name, data.role);
    closeModal();
    window.dispatchEvent(new CustomEvent("auth:login", { detail: data }));
  } catch (err) { setAuthError(err.message); }
  finally { btn.disabled = false; btn.textContent = "Create Account"; }
}

function toggleMenu() {
  const nav = document.getElementById("navMenu");
  if (nav) nav.classList.toggle("active");
}

document.addEventListener("DOMContentLoaded", () => {
  restoreAuthState();
  const loginForm = document.getElementById("loginForm");
  if (loginForm) loginForm.addEventListener("submit", handleLoginSubmit);
  const registerForm = document.getElementById("registerForm");
  if (registerForm) registerForm.addEventListener("submit", handleRegisterSubmit);
  const authModal = document.getElementById("authModal");
  if (authModal) authModal.addEventListener("click", (e) => { if (e.target === authModal) closeModal(); });
});
