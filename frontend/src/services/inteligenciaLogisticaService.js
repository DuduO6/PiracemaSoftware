import api from "../api/api";

const raiz = "/api/inteligencia-logistica";

export const listarEmpresas = () => api.get(`${raiz}/minhas-empresas/`);
export const listarRegioesLogisticas = () => api.get(`${raiz}/regioes-logisticas/`);
export const listarOportunidades = () => api.get(`${raiz}/oportunidades/`);
export const listarPerfis = () => api.get(`${raiz}/perfis/`);
export const recomendarOportunidades = (payload) =>
  api.post(`${raiz}/oportunidades/recomendar/`, payload);
export const planejarReposicionamento = (payload) =>
  api.post(`${raiz}/planejar-reposicionamento/`, payload);
export const calcularFrete = (payload) => api.post(`${raiz}/calcular-frete/`, payload);
export const registrarResultadoDecisao = (decisaoId, payload) =>
  api.post(`${raiz}/decisoes/${decisaoId}/feedback/`, payload);
export const listarPolosNacionais = (params = {}) =>
  api.get(`${raiz}/polos-nacionais/`, { params });
export const listarProdutosLogisticos = () =>
  api.get(`${raiz}/produtos-logisticos/`);
export const listarIndicadoresFrete = () =>
  api.get(`${raiz}/indicadores-frete/`);
