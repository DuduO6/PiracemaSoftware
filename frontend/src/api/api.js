import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

// Interceptor para enviar token JWT
api.interceptors.request.use(config => {
  const token = localStorage.getItem("access");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Se for upload (FormData) → não setar content-type (axios cuida)
  if (config.data instanceof FormData) {
    config.headers["Content-Type"] = "multipart/form-data";
  } else {
    config.headers["Content-Type"] = "application/json";
  }

  return config;
});

export default api;
