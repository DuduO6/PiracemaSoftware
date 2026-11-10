import api from "../api/api";

export async function calcularSeguroCargas(payload) {
  const response = await api.post("/api/seguro-cargas/calcular/", payload);
  return response.data;
}

export async function importarDocumentoFiscal(arquivo) {
  const formData = new FormData();
  formData.append("arquivo", arquivo);
  const response = await api.post("/api/seguro-cargas/importar-xml/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
