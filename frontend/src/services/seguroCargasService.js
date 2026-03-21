import api from "../api/api";

export async function calcularSeguroCargas(payload) {
  const response = await api.post("/api/seguro-cargas/calcular/", payload);
  return response.data;
}
