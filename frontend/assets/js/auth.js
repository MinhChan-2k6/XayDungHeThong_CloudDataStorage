/** Shared registration and sign-in UI, with validation and real API calls. */
(() => {
  "use strict";
  const form = document.querySelector("#auth-form");
  const page = document.body.dataset.authPage;
  const year = document.querySelector("#current-year");
  if (year) year.textContent = String(new Date().getFullYear());
  if (!form || !["register", "login"].includes(page)) return;

  const fields = Object.fromEntries([...form.querySelectorAll("input")].map((el) => [el.id, el]));
  const message = document.querySelector("#form-message");
  const submit = document.querySelector("#submit-button");
  const isRegister = page === "register";
  const meter = document.querySelector(".password-meter");
  const strengthText = document.querySelector("#password-strength");
  let submitted = false;
  let pending = false;
  const touched = new Set();

  function showMessage(text) {
    message.textContent = text;
    message.hidden = !text;
  }

  function getError(key) {
    const value = fields[key].value;
    const trimmed = value.trim();
    switch (key) {
      case "name":
        if (!trimmed) return "Vui lòng nhập họ và tên.";
        if (Array.from(trimmed).length < 2 || Array.from(trimmed).length > 80) return "Họ và tên cần từ 2 đến 80 ký tự.";
        return "";
      case "email":
        if (!trimmed) return "Vui lòng nhập email.";
        if (trimmed.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(trimmed)) return "Địa chỉ email không hợp lệ.";
        return "";
      case "password":
        if (!value) return "Vui lòng nhập mật khẩu.";
        if (!isRegister) return "";
        if (Array.from(value).length < 8 || Array.from(value).length > 128) return "Mật khẩu phải từ 8 đến 128 ký tự.";
        if (!/\p{L}/u.test(value) || !/\d/.test(value)) return "Mật khẩu cần có ít nhất một chữ cái và một chữ số.";
        return "";
      case "confirmPassword":
        if (!value) return "Vui lòng nhập lại mật khẩu.";
        if (value !== fields.password.value) return "Mật khẩu xác nhận chưa trùng khớp.";
        return "";
      default: return "";
    }
  }

  function paintField(key, force = false) {
    if (!force && !submitted && !touched.has(key)) return true;
    const error = getError(key);
    fields[key].setAttribute("aria-invalid", String(Boolean(error)));
    fields[key].classList.toggle("is-invalid", Boolean(error));
    fields[key].classList.toggle("is-valid", !error && Boolean(fields[key].value));
    const out = document.querySelector(`#${key}-error`);
    if (out) out.textContent = error;
    return !error;
  }

  function updateStrength() {
    if (!isRegister || !meter) return;
    const value = fields.password.value;
    const checks = {
      length: Array.from(value).length >= 8,
      letter: /\p{L}/u.test(value),
      number: /\d/.test(value),
    };
    Object.entries(checks).forEach(([key, success]) => document.querySelector(`#hint-${key}`)?.classList.toggle("is-met", success));
    let score = Number(checks.length) + Number(checks.letter) + Number(checks.number);
    if (score === 3 && (Array.from(value).length >= 12 || /[^\p{L}\d]/u.test(value))) score = 4;
    if (!value) score = 0;
    meter.dataset.score = String(score);
    meter.setAttribute("aria-valuenow", String(score));
    strengthText.textContent = score === 0 ? "Sử dụng từ 8 ký tự, có chữ và số." : ["", "Mật khẩu còn yếu", "Cần thêm ký tự để bảo vệ tài khoản", "Mật khẩu đạt yêu cầu", "Mật khẩu tốt"][score];
  }

  Object.entries(fields).forEach(([key, input]) => {
    input.addEventListener("blur", () => { touched.add(key); paintField(key); });
    input.addEventListener("input", () => {
      if (!message.hidden) showMessage("");
      paintField(key);
      if (isRegister && key === "password") {
        updateStrength();
        if (touched.has("confirmPassword") || submitted) paintField("confirmPassword", true);
      }
    });
  });

  form.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = fields[button.dataset.togglePassword];
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
      button.setAttribute("aria-pressed", String(show));
      button.querySelector("use")?.setAttribute("href", show ? "#icon-eye-off" : "#icon-eye");
      input.focus();
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (pending) return;
    submitted = true;
    showMessage("");
    let valid = true;
    for (const key of Object.keys(fields)) if (!paintField(key, true)) valid = false;
    if (!valid) {
      Object.values(fields).find((input) => input.getAttribute("aria-invalid") === "true")?.focus();
      return;
    }

    pending = true;
    submit.disabled = true;
    form.setAttribute("aria-busy", "true");
    document.querySelector("#auth-fields").disabled = true;
    submit.classList.add("is-loading");
    submit.querySelector(".submit-label").textContent = isRegister ? "Đang tạo tài khoản…" : "Đang đăng nhập…";
    try {
      const data = isRegister
        ? { full_name: fields.name.value.trim().replace(/\s+/g, " "), email: fields.email.value.trim().toLowerCase(), password: fields.password.value }
        : { email: fields.email.value.trim().toLowerCase(), password: fields.password.value };
      await (isRegister ? window.CloudDS.api.post("/auth/register", data) : window.CloudDS.api.post("/auth/login", data));
      // Only proceed after the real server confirms registration/sign-in.
      if (!isRegister) { window.CloudDS.api.clearCsrf(); await window.CloudDS.api.csrf(true); }
      if (fields.password) fields.password.value = "";
      if (fields.confirmPassword) fields.confirmPassword.value = "";
      document.querySelector("#auth-form-content").hidden = true;
      const success = document.querySelector("#auth-success");
      success.hidden = false;
      success.focus();
      if (!isRegister) {
        const next = new URLSearchParams(location.search).get('next');
        const safeNext = ['dashboard.html','files.html','trash.html','plans.html','checkout.html','billing.html','profile.html','admin.html'].includes(next) ? next : 'dashboard.html';
        window.location.assign(safeNext);
      }
    } catch (error) {
      Object.entries(error.details?.fields || {}).forEach(([key, text]) => {
        if (fields[key] && typeof text === "string") {
          fields[key].setAttribute("aria-invalid", "true");
          fields[key].classList.add("is-invalid");
          document.querySelector(`#${key}-error`).textContent = text;
        }
      });
      showMessage(error.message || "Không thể xử lý yêu cầu. Vui lòng thử lại.");
      message.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
    } finally {
      pending = false;
      submit.disabled = false;
      form.setAttribute("aria-busy", "false");
      document.querySelector("#auth-fields").disabled = false;
      submit.classList.remove("is-loading");
      submit.querySelector(".submit-label").textContent = isRegister ? "Tạo tài khoản miễn phí" : "Đăng nhập";
    }
  });
  document.querySelector("#auth-fields").disabled = false;
  updateStrength();
})();
