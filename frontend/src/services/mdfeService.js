import api from "../api/api";

const raiz = "/api/mdfe";

export const listarEmpresasMdfe = () => api.get(`${raiz}/empresas/`);
export const criarEmpresaMdfe = () => api.post(`${raiz}/empresas/`);
export const listarManifestos = (params = {}) => api.get(`${raiz}/pendentes/`, { params });
export const atualizarManifestos = () => api.post(`${raiz}/atualizar/`);
export const importarXmlMdfe = (formData) => api.post(`${raiz}/importar-xml/`, formData);
export const listarHistoricoMdfe = (params = {}) => api.get(`${raiz}/historico/`, { params });
export const consultarManifesto = (chave) => api.get(`${raiz}/${chave}/`);
export const encerrarManifesto = (chave, payload, idempotencyKey) => api.post(
  `${raiz}/${chave}/encerrar/`,
  payload,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
export const consultarOperacao = (id) => api.get(`${raiz}/operacoes/${id}/`);
export const confirmarOperacao = (id) => api.post(`${raiz}/operacoes/${id}/confirmar/`);
export const obterConfiguracaoFiscal = () => api.get(`${raiz}/configuracao/`);
export const salvarConfiguracaoFiscal = (formData) => api.put(`${raiz}/configuracao/`, formData);
