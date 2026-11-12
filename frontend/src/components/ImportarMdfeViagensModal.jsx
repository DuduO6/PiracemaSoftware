import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import api from "../api/api";
import "../styles/importarMdfeViagens.css";

const dinheiro = (value) => Number(value || 0).toLocaleString("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const numero = (value) => String(value ?? "").replace(",", ".");

const mensagemErro = (error) => {
  const data = error?.response?.data;
  if (!data) return "Não foi possível consultar os MDF-e em aberto.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return "Confira os dados informados e tente novamente.";
};

const formularioInicial = (manifest) => ({
  mdfe_chave: manifest.chave_mdfe,
  motorista_id: manifest.sugestao?.motorista_id ? String(manifest.sugestao.motorista_id) : "",
  data: manifest.sugestao?.data || "",
  origem: manifest.sugestao?.origem || "",
  destino: manifest.sugestao?.destino || "",
  cliente: manifest.sugestao?.cliente || "",
  peso: manifest.sugestao?.peso || "",
  valor_tonelada: manifest.sugestao?.valor_tonelada || "",
  teve_cte: Boolean(manifest.sugestao?.teve_cte),
  descontar_cte: Boolean(manifest.sugestao?.descontar_cte),
  chave_cte: manifest.sugestao?.chave_cte || "",
  pago: Boolean(manifest.sugestao?.pago),
  confirmar_divergencia_cpf: false,
  confirmar_xml_informativo: false,
  confirmar_possivel_duplicidade: false,
  confirmar_diferenca_contrato: false,
});

const podeImportar = (manifest) => !["JA_IMPORTADO", "XML_INDISPONIVEL"].includes(manifest.status);

export default function ImportarMdfeViagensModal({ motoristas, onClose, onImported }) {
  const [companies, setCompanies] = useState([]);
  const [companyId, setCompanyId] = useState("");
  const [result, setResult] = useState(null);
  const [forms, setForms] = useState({});
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [ignoredKeys, setIgnoredKeys] = useState([]);
  const [activeKey, setActiveKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const consult = async (selectedCompany) => {
    if (!selectedCompany) return;
    localStorage.setItem("empresa_logistica_id", String(selectedCompany));
    setLoading(true);
    setError("");
    setResult(null);
    setSelectedKeys([]);
    setIgnoredKeys([]);
    setActiveKey("");
    try {
      const { data } = await api.post("/api/viagens/consultar-mdfe-abertos/", {});
      const nextForms = Object.fromEntries(
        data.manifestos.map((manifest) => [manifest.chave_mdfe, formularioInicial(manifest)]),
      );
      setForms(nextForms);
      setResult(data);
      const first = data.manifestos.find(podeImportar);
      if (first) setActiveKey(first.chave_mdfe);
    } catch (requestError) {
      setError(mensagemErro(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    api.get("/api/mdfe/empresas/")
      .then(({ data }) => {
        if (!active) return;
        const available = Array.isArray(data) ? data : [];
        setCompanies(available);
        const stored = localStorage.getItem("empresa_logistica_id");
        const selected = available.some((item) => String(item.id) === String(stored))
          ? String(stored)
          : String(available[0]?.id || "");
        setCompanyId(selected);
        if (selected) consult(selected);
        else {
          setError("Nenhuma empresa autorizada está disponível para consultar MDF-e.");
          setLoading(false);
        }
      })
      .catch((requestError) => {
        if (!active) return;
        setError(mensagemErro(requestError));
        setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const manifests = (result?.manifestos || []).filter((item) => !ignoredKeys.includes(item.chave_mdfe));
  const selectedCompany = companies.find((item) => String(item.id) === String(companyId));
  const canImport = selectedCompany?.papel !== "LEITURA";
  const activeManifest = manifests.find((item) => item.chave_mdfe === activeKey) || null;
  const activeForm = activeManifest ? forms[activeManifest.chave_mdfe] : null;

  const finance = useMemo(() => {
    if (!activeForm) return null;
    const weight = Number(numero(activeForm.peso));
    const rate = Number(numero(activeForm.valor_tonelada));
    if (!Number.isFinite(weight) || !Number.isFinite(rate) || weight <= 0 || rate <= 0) return null;
    const gross = weight * rate;
    const discount = activeForm.teve_cte && activeForm.descontar_cte ? gross * 0.1 : 0;
    const net = gross - discount;
    const contract = Number(activeManifest?.valor_contrato || 0);
    return { gross, discount, net, contract, difference: contract ? net - contract : 0 };
  }, [activeForm, activeManifest]);

  const updateForm = (field, value) => {
    if (!activeManifest) return;
    setForms((current) => ({
      ...current,
      [activeManifest.chave_mdfe]: { ...current[activeManifest.chave_mdfe], [field]: value },
    }));
  };

  const toggleSelection = (key) => {
    setSelectedKeys((current) => (
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    ));
  };

  const ignoreManifest = (key) => {
    setIgnoredKeys((current) => [...current, key]);
    setSelectedKeys((current) => current.filter((item) => item !== key));
    const next = manifests.find((item) => item.chave_mdfe !== key);
    setActiveKey(next?.chave_mdfe || "");
  };

  const buildPayload = (keys) => keys.map((key) => {
    const form = forms[key];
    return {
      ...form,
      motorista_id: Number(form.motorista_id),
      peso: numero(form.peso),
      valor_tonelada: numero(form.valor_tonelada),
    };
  });

  const save = async (keys) => {
    if (!canImport || !keys.length || saving) return;
    setSaving(true);
    setError("");
    try {
      const { data } = await api.post("/api/viagens/importar-mdfe-confirmados/", {
        registros: buildPayload(keys),
      });
      onImported(data.viagens || []);
      onClose();
    } catch (requestError) {
      const index = requestError.response?.data?.indice;
      if (Number.isInteger(index) && keys[index]) setActiveKey(keys[index]);
      setError(mensagemErro(requestError));
    } finally {
      setSaving(false);
    }
  };

  return createPortal((
    <div className="modal-overlay mdfe-trip-overlay" role="presentation">
      <section className="mdfe-trip-modal" role="dialog" aria-modal="true" aria-labelledby="mdfe-trip-title">
        <header className="mdfe-trip-header">
          <div>
            <h2 id="mdfe-trip-title">Importar viagens dos MDF-e em aberto</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar">×</button>
        </header>

        <div className="mdfe-trip-toolbar">
          <div className="mdfe-trip-company">
            <span>Transportadora do manifesto</span>
            <strong>{selectedCompany?.nome || "Identificando…"}</strong>
          </div>
          <button type="button" onClick={() => consult(companyId)} disabled={!companyId || loading || saving}>
            {loading ? "Consultando…" : "Consultar novamente"}
          </button>
        </div>

        {error && <div className="mdfe-trip-error" role="alert">{error}</div>}
        {!canImport && (
          <div className="mdfe-trip-readonly" role="status">
            Seu perfil pode consultar os MDF-e, mas somente ADMIN ou OPERADOR pode cadastrar viagens.
          </div>
        )}

        {result && (
          <div className="mdfe-trip-summary">
            <span><strong>{result.resumo.manifestos_encontrados}</strong> encontrados</span>
            <span><strong>{result.resumo.disponiveis}</strong> disponíveis</span>
            <span><strong>{result.resumo.ja_cadastrados}</strong> cadastrados</span>
            <span><strong>{result.resumo.incompletos}</strong> para revisar</span>
            <span><strong>{result.resumo.xmls_indisponiveis}</strong> sem XML</span>
          </div>
        )}

        {loading && <div className="mdfe-trip-loading">Consultando a SEFAZ e verificando os XMLs armazenados…</div>}

        {!loading && result && (
          <div className="mdfe-trip-content">
            <aside className="mdfe-trip-list" aria-label="Manifestos encontrados">
              {manifests.length === 0 && <p>Nenhum MDF-e em aberto foi encontrado.</p>}
              {manifests.map((manifest) => {
                const importable = podeImportar(manifest);
                return (
                  <article
                    key={manifest.chave_mdfe}
                    className={`mdfe-trip-item ${activeKey === manifest.chave_mdfe ? "active" : ""}`}
                    onClick={() => setActiveKey(manifest.chave_mdfe)}
                  >
                    <label onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedKeys.includes(manifest.chave_mdfe)}
                        disabled={!canImport || !importable}
                        onChange={() => toggleSelection(manifest.chave_mdfe)}
                      />
                      Selecionar
                    </label>
                    <div className="mdfe-trip-item-title">
                      <strong>MDF-e {manifest.numero_mdfe || "—"}</strong>
                      <span className={`mdfe-trip-status status-${manifest.status?.toLowerCase()}`}>{manifest.status_label}</span>
                    </div>
                    <dl>
                      <div><dt>CT-e</dt><dd>{manifest.ctes?.length === 1 ? manifest.ctes[0].numero : `${manifest.ctes?.length || 0} vinculados`}</dd></div>
                      <div><dt>Data</dt><dd>{manifest.sugestao?.data || "—"}</dd></div>
                      <div><dt>Trecho</dt><dd>{manifest.sugestao?.origem || "—"} → {manifest.sugestao?.destino || "—"}</dd></div>
                      <div><dt>Peso</dt><dd>{manifest.peso_toneladas ? `${manifest.peso_toneladas} t` : "—"}</dd></div>
                    </dl>
                  </article>
                );
              })}
            </aside>

            <main className="mdfe-trip-review">
              {!activeManifest && <p>Selecione um manifesto para revisar.</p>}
              {activeManifest && !podeImportar(activeManifest) && (
                <div className="mdfe-trip-notice">
                  <h3>{activeManifest.status_label}</h3>
                  {(activeManifest.pendencias || []).map((item) => <p key={item}>{item}</p>)}
                </div>
              )}
              {activeManifest && activeForm && podeImportar(activeManifest) && (
                <>
                  <div className="mdfe-trip-fiscal">
                    <h3>Dados fiscais</h3>
                    <dl>
                      <div><dt>MDF-e</dt><dd>{activeManifest.numero_mdfe} · série {activeManifest.serie_mdfe}</dd></div>
                      <div><dt>Emissão</dt><dd>{new Date(activeManifest.data_emissao).toLocaleString("pt-BR")}</dd></div>
                      <div><dt>Contrato</dt><dd>{activeManifest.valor_contrato ? dinheiro(activeManifest.valor_contrato) : "Não informado"}</dd></div>
                      <div><dt>Tomador</dt><dd>{activeManifest.cliente_sugerido || "Não informado"}</dd></div>
                      <div><dt>Produto</dt><dd>{activeManifest.produto?.nome || "Não informado"}</dd></div>
                      <div className="mdfe-trip-key-line"><dt>Chave MDF-e</dt><dd title={activeManifest.chave_mdfe}>{activeManifest.chave_mdfe}</dd></div>
                      <div className="mdfe-trip-key-line"><dt>Chave CT-e</dt><dd title={activeForm.chave_cte}>{activeForm.chave_cte || "Não informada"}</dd></div>
                    </dl>
                  </div>

                  {(activeManifest.pendencias || []).length > 0 && (
                    <div className="mdfe-trip-notice">
                      {activeManifest.pendencias.map((item) => <p key={item}>{item}</p>)}
                    </div>
                  )}

                  <div className="mdfe-trip-form">
                    <h3>Dados da viagem</h3>
                    <label>Motorista cadastrado
                      <select value={activeForm.motorista_id} onChange={(event) => updateForm("motorista_id", event.target.value)}>
                        <option value="">Selecione um motorista</option>
                        {motoristas.map((driver) => <option key={driver.id} value={driver.id}>{driver.nome}</option>)}
                      </select>
                    </label>
                    <label>Data da viagem<input type="date" value={activeForm.data} onChange={(event) => updateForm("data", event.target.value)} /></label>
                    <label>Origem<input value={activeForm.origem} onChange={(event) => updateForm("origem", event.target.value)} /></label>
                    <label>Destino<input value={activeForm.destino} onChange={(event) => updateForm("destino", event.target.value)} /></label>
                    <label className="wide">Cliente/tomador<input value={activeForm.cliente} onChange={(event) => updateForm("cliente", event.target.value)} placeholder="Preenchimento obrigatório" /></label>
                    <label>Peso (toneladas)<input inputMode="decimal" value={activeForm.peso} onChange={(event) => updateForm("peso", event.target.value)} /></label>
                    <label>Valor por tonelada<input inputMode="decimal" value={activeForm.valor_tonelada} onChange={(event) => updateForm("valor_tonelada", event.target.value)} /></label>
                    <label>CT-e
                      <select
                        value={activeForm.chave_cte}
                        onChange={(event) => updateForm("chave_cte", event.target.value)}
                        disabled={!activeManifest.ctes?.length}
                      >
                        {!activeManifest.ctes?.length && <option value="">Sem CT-e vinculado</option>}
                        {activeManifest.ctes?.length > 1 && <option value="">Selecione</option>}
                        {(activeManifest.ctes || []).map((cte) => (
                          <option key={cte.chave} value={cte.chave}>CT-e {cte.numero} · série {cte.serie}</option>
                        ))}
                      </select>
                    </label>
                    <label className="mdfe-trip-checkbox">
                      <input
                        type="checkbox"
                        checked={activeForm.descontar_cte}
                        disabled={!activeForm.teve_cte}
                        onChange={(event) => updateForm("descontar_cte", event.target.checked)}
                      />
                      Aplicar desconto de 10% do CT-e
                    </label>
                    <label>Situação de pagamento
                      <select value={activeForm.pago ? "pago" : "pendente"} onChange={(event) => updateForm("pago", event.target.value === "pago")}>
                        <option value="pendente">Pendente</option>
                        <option value="pago">Pago</option>
                      </select>
                    </label>
                  </div>

                  {finance && (
                    <div className="mdfe-trip-finance">
                      <h3>Resumo financeiro</h3>
                      <div><span>Valor bruto</span><strong>{dinheiro(finance.gross)}</strong></div>
                      <div><span>Desconto CT-e (10%)</span><strong>- {dinheiro(finance.discount)}</strong></div>
                      <div><span>Valor líquido</span><strong>{dinheiro(finance.net)}</strong></div>
                      <div><span>Contrato declarado</span><strong>{finance.contract ? dinheiro(finance.contract) : "Não informado"}</strong></div>
                      {finance.contract > 0 && Math.abs(finance.difference) >= 0.01 && (
                        <div className="difference"><span>Diferença líquido × contrato</span><strong>{dinheiro(finance.difference)}</strong></div>
                      )}
                    </div>
                  )}

                  <div className="mdfe-trip-confirmations">
                    {(activeManifest.motorista_sugerido_id !== Number(activeForm.motorista_id) || activeManifest.condutores?.length > 1) && (
                      <label><input type="checkbox" checked={activeForm.confirmar_divergencia_cpf} onChange={(event) => updateForm("confirmar_divergencia_cpf", event.target.checked)} /> Confirmo o motorista responsável e eventual divergência de CPF.</label>
                    )}
                    {activeManifest.xml_informativo && (
                      <label><input type="checkbox" checked={activeForm.confirmar_xml_informativo} onChange={(event) => updateForm("confirmar_xml_informativo", event.target.checked)} /> Confirmo que revisei os dados extraídos.</label>
                    )}
                    {activeManifest.possiveis_duplicidades?.length > 0 && (
                      <label><input type="checkbox" checked={activeForm.confirmar_possivel_duplicidade} onChange={(event) => updateForm("confirmar_possivel_duplicidade", event.target.checked)} /> Revisei a possível duplicidade histórica do CT-e.</label>
                    )}
                    {finance?.contract > 0 && Math.abs(finance.difference) >= 0.01 && (
                      <label><input type="checkbox" checked={activeForm.confirmar_diferenca_contrato} onChange={(event) => updateForm("confirmar_diferenca_contrato", event.target.checked)} /> Confirmo a diferença entre o valor líquido e o contrato declarado.</label>
                    )}
                  </div>

                  <div className="mdfe-trip-record-actions">
                    <button type="button" className="ignore" onClick={() => ignoreManifest(activeManifest.chave_mdfe)} disabled={saving}>Ignorar manifesto</button>
                    <button className="mdfe-trip-save-one" type="button" onClick={() => save([activeManifest.chave_mdfe])} disabled={!canImport || saving}>
                      {saving ? "Salvando…" : "Salvar viagem"}
                    </button>
                  </div>
                </>
              )}
            </main>
          </div>
        )}

        <footer className="mdfe-trip-footer">
          <button type="button" className="cancel" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="button" onClick={() => save(selectedKeys)} disabled={!canImport || !selectedKeys.length || saving}>
            {saving ? "Salvando…" : `Salvar viagens selecionadas (${selectedKeys.length})`}
          </button>
        </footer>
      </section>
    </div>
  ), document.body);
}
