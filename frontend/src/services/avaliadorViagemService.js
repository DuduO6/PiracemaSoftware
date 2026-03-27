import api from "../api/api";

export async function listarViagens() {
  const response = await api.get("/api/viagens/");
  return Array.isArray(response.data) ? response.data : response.data.results || [];
}

export async function avaliarLucroViagem(payload) {
  const response = await api.post("/api/viagens/avaliar_lucro/", payload);
  return response.data;
}
