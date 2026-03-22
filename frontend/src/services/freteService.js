import api from "../api/api";

export async function calcularFrete(payload) {
  const response = await api.post("/api/fretes/calcular/", payload);
  return response.data;
}
