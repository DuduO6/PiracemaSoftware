import axios from "axios";

// Usa variável de ambiente ou fallback para desenvolvimento local
const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_URL,
});

// Interceptor para enviar token JWT
api.interceptors.request.use(config => {
  const token = localStorage.getItem("access");

  // Só enviar token para endpoints que realmente precisam de autenticação
  if (
    token &&
    !config.url.includes("/auth/register/") &&
    !config.url.includes("/auth/token/")
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

// Interceptor para tratar respostas de erro com refresh token
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    // Se receber 401 e não for tentativa de refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refresh = localStorage.getItem("refresh");
        
        if (refresh) {
          const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
            refresh: refresh
          });

          const newAccessToken = response.data.access;
          localStorage.setItem("access", newAccessToken);

          // Atualizar o token na requisição original
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Se refresh falhar, limpar tudo e redirecionar
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    // Se não conseguir renovar ou outro erro
    if (error.response?.status === 401) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default api;