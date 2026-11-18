if (!localStorage.getItem("algo_token")) {
  window.location.replace("/login");
}

async function fetchJSON(url, options = {}) {
  const token = localStorage.getItem("algo_token") || "";
  const headers = {
    ...(options.headers || {}),
    "Authorization": `Bearer ${token}`
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("algo_token");
    window.location.replace("/login");
    throw new Error("Session expired");
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function logoutUser() {
  localStorage.removeItem("algo_token");
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.replace("/login");
}