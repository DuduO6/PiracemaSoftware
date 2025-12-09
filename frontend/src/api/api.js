import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000", // URL do seu backend
});

// Interceptor para enviar token JWT
api.interceptors.request.use(config => {
  const token = localStorage.getItem("access");

  // Só enviar token para endpoints que realmente precisam de autenticação
  if (
    token &&
    !config.url.includes("/auth/register/") &&
    !config.url.includes("/auth/login/")
  ) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Se for upload (FormData) → não setar content-type (axios cuida)
  if (config.data instanceof FormData) {
    config.headers["Content-Type"] = "multipart/form-data";
  } else {
    config.headers["Content-Type"] = "application/json";
  }

  return config;
}, error => {
  return Promise.reject(error);
});

// Interceptor para tratar respostas de erro
api.interceptors.response.use(
  response => response,
  error => {
    // Exemplo: se token expirar, limpar localStorage e redirecionar
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      // Aqui você pode redirecionar para login se quiser
    }
    return Promise.reject(error);
  }
);

export default api;
