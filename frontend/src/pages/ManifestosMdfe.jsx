import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import ThemeControl from "../components/ThemeControl";
import UiIcon from "../components/UiIcon";
import municipiosBrasil from "../data/municipiosBrasil.json";
import {
  atualizarManifestos,
  baixarXmlMdfe,
  confirmarOperacao,
  criarEmpresaMdfe,
  encerrarManifesto,
  importarXmlMdfe,
  listarEmpresasMdfe,
  listarHistoricoMdfe,
  listarManifestos,
  obterConfiguracaoFiscal,
  salvarConfiguracaoFiscal,
} from "../services/mdfeService";
import "../styles/manifestosMdfe.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
const dateOnly = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });
const UF = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO", "EX"];

function errorMessage(error) {
  const data = error.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const first = Object.values(data).flat().find(Boolean);
    if (first) return String(first);
  }
  return "Não foi possível concluir a operação.";
}

function formatDateTime(value) {
  return value ? dateTime.format(new Date(value)) : "Não disponível";
}

function formatDate(value) {
  return value ? dateOnly.format(new Date(value)) : "Não disponível";
}

function shortKey(value) {
  return value ? `${value.slice(0, 8)}…${value.slice(-8)}` : "—";
}

function StatusBadge({ status, label }) {
  const icon = status === "ENCERRADO" ? "check" : status === "ABERTO" ? "document" : "warning";
  return (
    <span className={`mdfe-status status-${String(status || "").toLowerCase()}`}>
      <UiIcon name={icon} size={13} strokeWidth={2.1} />
      {label || status}
    </span>
  );
}

function Modal({ title, children, onClose, wide = false }) {
  const titleId = useId();
  const modalRef = useRef(null);
  const closeRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === "Escape") onCloseRef.current();
      if (event.key !== "Tab" || !modalRef.current) return;
      const focusable = [...modalRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      )];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus?.();
    };
  }, []);

  return (
    <div className="mdfe-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        ref={modalRef}
        className={`mdfe-modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id={titleId}>{title}</h2>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Fechar janela">
            <UiIcon name="close" />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function MunicipalityField({ uf, value, onSelect }) {
  const [query, setQuery] = useState(value?.label || "");
  useEffect(() => setQuery(value?.label || ""), [value]);
  const options = useMemo(() => {
    const normalized = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    if (normalized.length < 2 || !uf || uf === "EX") return [];
    return municipiosBrasil.filter((item) => (
      item.estado === uf
      && item.label.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(normalized)
    )).slice(0, 8);
  }, [query, uf]);

  if (uf === "EX") return <label>Município<input readOnly value="Exterior — 9999999" /></label>;
  return (
    <label className="mdfe-municipality">Município de encerramento
      <input
        value={query}
        onChange={(event) => { setQuery(event.target.value); onSelect(null); }}
        placeholder="Digite ao menos 2 letras"
        autoComplete="off"
      />
      {options.length > 0 && (
        <div className="mdfe-options" role="listbox" aria-label="Municípios encontrados">
          {options.map((item) => (
            <button key={item.id} type="button" onClick={() => { onSelect(item); setQuery(item.label); }}>
              {item.label}<small>{item.id}</small>
            </button>
          ))}
        </div>
      )}
    </label>
  );
}

function MetricCard({ tone, icon, title, value, description, loading }) {
  return (
    <article className={`mdfe-metric metric-${tone}`}>
      <span className="mdfe-metric-icon"><UiIcon name={icon} size={22} /></span>
      <div>
        <span className="mdfe-metric-title">{title}</span>
        {loading ? <span className="mdfe-skeleton metric-value" /> : <strong>{value}</strong>}
        <small>{description}</small>
      </div>
    </article>
  );
}

function KeyValue({ value }) {
  const copy = () => navigator.clipboard?.writeText(value);
  return (
    <span className="mdfe-key">
      <code title={value}>{shortKey(value)}</code>
      <button type="button" className="icon-button" onClick={copy} aria-label="Copiar chave de acesso" title="Copiar chave completa">
        <UiIcon name="copy" size={16} />
      </button>
    </span>
  );
}

function DriverList({ manifest }) {
  if (!manifest.condutores?.length) {
    return <span className="muted" title={manifest.xml_ultimo_erro || ""}>{manifest.xml_status === "ERRO" ? "XML indisponível" : "Aguardando XML"}</span>;
  }
  return (
    <div className="mdfe-drivers">
      {manifest.condutores.map((driver) => (
        <span key={`${manifest.chave}-${driver.cpf_mascarado}`}>
          <strong>{driver.nome}</strong>
          <small>{driver.vinculado ? "Motorista cadastrado" : "Somente no XML"}</small>
        </span>
      ))}
      {manifest.xml_somente_informativo && <small className="mdfe-informational">Dado informativo — conteúdo não verificado</small>}
    </div>
  );
}

function DestinationList({ manifest }) {
  if (!manifest.destinos?.length) return <span className="muted">Não disponível</span>;
  return (
    <div className="mdfe-drivers">
      {manifest.destinos.map((destination) => (
        <span key={`${manifest.chave}-${destination.codigo}`}>
          <strong>{destination.municipio}</strong>
          <small>{destination.uf || "—"} · {destination.codigo}</small>
        </span>
      ))}
      {manifest.xml_somente_informativo && <small className="mdfe-informational">Não será usado no encerramento</small>}
    </div>
  );
}

function EmptyState({ history, search, filter, consultation, lastSuccess }) {
  let description = "Atualize a consulta para buscar documentos na SEFAZ.";
  if (history) description = "Ainda não há encerramentos confirmados pelo sistema.";
  else if (search || filter) description = "Tente remover a pesquisa ou alterar o filtro de situação.";
  else if (consultation?.desatualizado) description = "A consulta mais recente falhou e não há resultados armazenados para exibir.";
  else if (lastSuccess) description = "A última consulta foi concluída com sucesso e não retornou documentos para esta visualização.";
  return (
    <div className="mdfe-empty">
      <span><UiIcon name="document" size={28} /></span>
      <strong>Nenhum manifesto encontrado.</strong>
      <p>{description}</p>
    </div>
  );
}

function ManifestActions({ manifest, history, canDownload, downloading, onDetails, onDownload, onClose }) {
  return (
    <div className="mdfe-row-actions">
      <button type="button" className="mdfe-btn ghost compact" onClick={() => onDetails(manifest)}>
        <UiIcon name="eye" size={16} /> Ver detalhes
      </button>
      {canDownload && manifest.xml_status === "DISPONIVEL" && (
        <button
          type="button"
          className="mdfe-btn ghost compact"
          disabled={downloading}
          onClick={() => onDownload(manifest)}
        >
          <UiIcon name="download" size={16} /> {downloading ? "Baixando…" : "Baixar XML"}
        </button>
      )}
      {manifest.situacao === "ABERTO" && !history && (
        <button type="button" className="mdfe-btn danger compact" onClick={() => onClose(manifest)}>
          Encerrar MDF-e
        </button>
      )}
    </div>
  );
}

function TableSkeleton() {
  return [...Array(4)].map((_, row) => (
    <tr key={row} aria-hidden="true">
      {[...Array(9)].map((__, column) => <td key={column}><span className="mdfe-skeleton table-line" /></td>)}
    </tr>
  ));
}

export default function ManifestosMdfe() {
  const [companies, setCompanies] = useState([]);
  const [companyId, setCompanyId] = useState(localStorage.getItem("empresa_logistica_id") || "");
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({ abertos: 0, encerrados: 0, pendentes: 0 });
  const [consultation, setConsultation] = useState(null);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [history, setHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState("");
  const [importSummary, setImportSummary] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [details, setDetails] = useState(null);
  const [closing, setClosing] = useState({ uf: "", municipality: null, date: "", confirmation: false });
  const [processing, setProcessing] = useState(false);
  const [operation, setOperation] = useState(null);
  const [configurationOpen, setConfigurationOpen] = useState(false);
  const [configuration, setConfiguration] = useState(null);
  const xmlInputRef = useRef(null);
  const refreshInFlightRef = useRef(false);
  const lastLocalLoadRef = useRef("");

  const activeCompany = companies.find((company) => String(company.id) === String(companyId));
  const isAdmin = activeCompany?.papel === "ADMIN";
  const canImport = activeCompany && activeCompany.papel !== "LEITURA";

  const load = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const params = { page, search: search || undefined, situacao: filter || undefined };
      const response = history ? await listarHistoricoMdfe(params) : await listarManifestos(params);
      if (history) {
        setItems(response.data.results || []);
        setSummary((current) => ({ ...current, encerrados: response.data.count || 0 }));
      } else {
        const result = response.data.results || {};
        setItems(result.items || []);
        setSummary(result.resumo || { abertos: 0, encerrados: 0, pendentes: 0 });
        setConsultation(result.consulta || null);
      }
      setCount(response.data.count || 0);
      setError("");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [companyId, filter, history, page, search]);

  const refreshManifestsOnClick = async () => {
    if (!companyId || refreshInFlightRef.current) return;
    refreshInFlightRef.current = true;
    setRefreshing(true);
    try {
      await atualizarManifestos();
      await load();
      setError("");
    } catch (requestError) {
      setError(`${errorMessage(requestError)}${requestError.response?.data?.desatualizado ? " O último resultado salvo continua visível e está desatualizado." : ""}`);
      await load();
    } finally {
      setRefreshing(false);
      refreshInFlightRef.current = false;
    }
  };

  const importXml = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    const form = new FormData();
    files.forEach((file) => form.append("arquivos", file));
    setImporting(true);
    setImportSummary(null);
    setError("");
    try {
      const { data } = await importarXmlMdfe(form);
      setImportSummary(data);
      await load();
    } catch (requestError) {
      const data = requestError.response?.data;
      if (data?.erros) setImportSummary(data);
      else setError(errorMessage(requestError));
    } finally {
      setImporting(false);
    }
  };

  const downloadXml = async (manifest) => {
    if (!manifest?.chave || downloadingKey) return;
    setDownloadingKey(manifest.chave);
    setError("");
    try {
      const response = await baixarXmlMdfe(manifest.chave);
      const blob = response.data instanceof Blob
        ? response.data
        : new Blob([response.data], { type: "application/xml" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const number = Number(manifest.numero);
      link.href = url;
      link.download = `mdfe-${Number.isFinite(number) && number > 0 ? number : "documento"}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      let message = errorMessage(requestError);
      if (requestError.response?.data instanceof Blob) {
        try {
          const payload = JSON.parse(await requestError.response.data.text());
          message = payload.detail || message;
        } catch (_parseError) {
          // Mantém a mensagem genérica sem expor conteúdo inesperado da resposta.
        }
      }
      setError(message);
    } finally {
      setDownloadingKey("");
    }
  };

  useEffect(() => {
    listarEmpresasMdfe().then(async ({ data }) => {
      if (!data.length) data = [(await criarEmpresaMdfe()).data];
      setCompanies(data);
      const stored = localStorage.getItem("empresa_logistica_id");
      const next = data.some((company) => String(company.id) === String(stored)) ? stored : String(data[0].id);
      localStorage.setItem("empresa_logistica_id", next);
      setCompanyId(next);
    }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!companyId) return;
    localStorage.setItem("empresa_logistica_id", companyId);
    const signature = JSON.stringify([companyId, filter, history, page, search]);
    if (lastLocalLoadRef.current === signature) return;
    lastLocalLoadRef.current = signature;
    // Apenas lê o estado já salvo no banco. A consulta à SEFAZ ocorre exclusivamente no botão Atualizar.
    load();
  }, [companyId, filter, history, load, page, search]);

  const openClosing = (manifest) => {
    setSelected(manifest);
    setOperation(null);
    setClosing({ uf: configuration?.uf || "", municipality: null, date: "", confirmation: false });
  };

  const submitClosing = async (event) => {
    event.preventDefault();
    if (!closing.date || !closing.uf || (!closing.municipality && closing.uf !== "EX") || !closing.confirmation) {
      setError("Confirme a UF, o município, a data efetiva e a declaração de conclusão.");
      return;
    }
    setProcessing(true);
    try {
      const municipalityCode = closing.uf === "EX" ? "9999999" : String(closing.municipality.id);
      const idempotency = window.crypto?.randomUUID?.() || `${Date.now()}-${selected.chave}`;
      const { data } = await encerrarManifesto(selected.chave, {
        uf: closing.uf,
        municipio_codigo: municipalityCode,
        data_encerramento: closing.date,
        confirmacao: true,
      }, idempotency);
      setOperation(data);
      if (data.estado === "HOMOLOGADO") await load();
      setError("");
    } catch (requestError) {
      const data = requestError.response?.data;
      if (data?.id && data?.estado) setOperation(data);
      else setError(errorMessage(requestError));
    } finally {
      setProcessing(false);
    }
  };

  const confirmPending = async () => {
    if (!operation?.id) return;
    setProcessing(true);
    try {
      const { data } = await confirmarOperacao(operation.id);
      setOperation(data);
      if (data.estado === "HOMOLOGADO") await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setProcessing(false); }
  };

  const openConfiguration = async () => {
    setConfigurationOpen(true);
    try {
      const { data } = await obterConfiguracaoFiscal();
      setConfiguration(data);
    } catch (requestError) { setError(errorMessage(requestError)); }
  };

  const saveConfiguration = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setProcessing(true);
    try {
      const { data } = await salvarConfiguracaoFiscal(form);
      setConfiguration(data);
      setConfigurationOpen(false);
      await load();
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setProcessing(false); }
  };

  const totalPages = Math.max(1, Math.ceil(count / 15));
  const lastSuccess = consultation?.ultima_consulta_bem_sucedida;
  const initialLoading = loading && !consultation && items.length === 0;
  const consultationDescription = lastSuccess
    ? `${lastSuccess.quantidade} documento(s) · ${lastSuccess.xml_baixados || 0} XML(s) baixado(s) · ${lastSuccess.xml_em_cache || 0} em cache${lastSuccess.xml_erros ? ` · ${lastSuccess.xml_erros} erro(s) de XML` : ""} · ${formatDateTime(lastSuccess.finalizada_em)}`
    : "Nenhuma consulta bem-sucedida registrada.";

  return (
    <main className="mdfe-page" aria-busy={loading || refreshing || processing}>
      <div className="mdfe-page-shell">
        <header className="mdfe-page-header">
          <div className="mdfe-heading">
            <h1>MDF-e</h1>
          </div>
          <div className="mdfe-header-tools">
            <ThemeControl compact />
            <div className="mdfe-header-actions">
              {companies.length > 1 && (
                <select className="mdfe-company-select" aria-label="Transportadora" value={companyId} onChange={(event) => { setPage(1); setCompanyId(event.target.value); }}>
                  {companies.map((company) => <option key={company.id} value={company.id}>{company.nome}</option>)}
                </select>
              )}
              {isAdmin && (
                <button className="mdfe-btn secondary" type="button" onClick={openConfiguration}>
                  <UiIcon name="settings" size={18} /> Configuração fiscal
                </button>
              )}
              {canImport && (
                <>
                  <input ref={xmlInputRef} type="file" accept=".xml,text/xml,application/xml" multiple hidden onChange={importXml} />
                  <button className="mdfe-btn secondary" type="button" disabled={importing} onClick={() => xmlInputRef.current?.click()}>
                    <UiIcon name="upload" size={18} /> {importing ? "Importando XML…" : "Importar XML"}
                  </button>
                </>
              )}
              <button className="mdfe-btn primary" type="button" disabled={refreshing} onClick={refreshManifestsOnClick}>
                <UiIcon name="refresh" size={18} className={refreshing ? "spin" : ""} />
                {refreshing ? "Consultando SEFAZ…" : "Atualizar manifestos"}
              </button>
            </div>
          </div>
        </header>

        <section className="mdfe-notifications" aria-live="polite">
          {error && (
            <div className="mdfe-alert error" role="alert">
              <UiIcon name="warning" size={19} />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")} aria-label="Fechar mensagem"><UiIcon name="close" size={17} /></button>
            </div>
          )}
          {importSummary && (
            <div className={`mdfe-alert ${importSummary.total_erros ? "stale" : "success"}`} role="status">
              <UiIcon name={importSummary.total_erros ? "warning" : "check"} size={19} />
              <div>
                <strong>{importSummary.total_importados || 0} XML(s) importado(s).</strong>
                {importSummary.importados?.map((item) => <span key={`${item.arquivo}-${item.chave}`}>{item.arquivo}: {item.vinculados} motorista(s) vinculado(s), {item.nao_vinculados} não encontrado(s).</span>)}
                {importSummary.erros?.map((item) => <span key={`${item.arquivo}-${item.code}`}>{item.arquivo}: {item.detail}</span>)}
              </div>
              <button type="button" onClick={() => setImportSummary(null)} aria-label="Fechar mensagem"><UiIcon name="close" size={17} /></button>
            </div>
          )}
          {consultation?.desatualizado && (
            <div className="mdfe-alert stale" role="status">
              <UiIcon name="warning" size={19} />
              <span><strong>Dados desatualizados.</strong> A tentativa mais recente falhou. Última consulta válida: {formatDateTime(lastSuccess?.finalizada_em)}.</span>
            </div>
          )}
        </section>

        <section className="mdfe-cards" aria-label="Resumo dos manifestos">
          <MetricCard tone="open" icon="document" title="Em aberto" value={summary.abertos} description="Retornados pela consulta atual" loading={initialLoading} />
          <MetricCard tone="closed" icon="check" title="Encerrados pelo sistema" value={summary.encerrados} description="Histórico disponível nesta aplicação" loading={initialLoading} />
          <MetricCard tone="attention" icon="warning" title="Erros ou a confirmar" value={summary.pendentes} description="Exigem verificação antes de retransmitir" loading={initialLoading} />
        </section>

        <section className="mdfe-panel" aria-labelledby="mdfe-list-title">
          <div className="mdfe-toolbar">
            <div>
              <h2 id="mdfe-list-title">{history ? "Histórico de encerramentos" : "Manifestos consultados"}</h2>
              <p>{consultationDescription}</p>
            </div>
            <div className="mdfe-filters">
              <label className="mdfe-search">
                <span className="sr-only">Pesquisar manifestos</span>
                <UiIcon name="search" size={18} />
                <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Pesquisar chave, número ou motorista" />
              </label>
              {!history && (
                <select aria-label="Filtrar por situação" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1); }}>
                  <option value="">Todas as situações</option>
                  <option value="ABERTO">Abertos</option>
                  <option value="A_CONFIRMAR">A confirmar</option>
                  <option value="DESCONHECIDO">Não confirmados</option>
                  <option value="CANCELADO">Cancelados</option>
                </select>
              )}
              <button type="button" className="mdfe-btn secondary" onClick={() => { setHistory((value) => !value); setPage(1); }}>
                <UiIcon name="history" size={18} /> {history ? "Ver manifestos" : "Ver histórico"}
              </button>
            </div>
          </div>

          {(loading || items.length > 0) && (
            <div className="mdfe-table-wrap">
              <table>
                <thead><tr><th>Número</th><th>Chave de acesso</th><th>Motorista</th><th>Destino</th><th>Emissão</th><th>Situação</th><th>Última consulta</th><th>Protocolo</th><th>Ações</th></tr></thead>
                <tbody>
                  {loading ? <TableSkeleton /> : items.map((manifest) => (
                    <tr key={manifest.chave}>
                      <td><strong>{manifest.numero ? Number(manifest.numero) : "Não disponível"}</strong></td>
                      <td><KeyValue value={manifest.chave} /></td>
                      <td><DriverList manifest={manifest} /></td>
                      <td><DestinationList manifest={manifest} /></td>
                      <td>{manifest.data_emissao ? formatDateTime(manifest.data_emissao) : "Não disponível"}</td>
                      <td><StatusBadge status={manifest.situacao} label={manifest.situacao_display} />{manifest.xml_somente_informativo && <span className="mdfe-xml-badge">XML informativo</span>}</td>
                      <td>{formatDateTime(manifest.ultima_consulta_em)}</td>
                      <td><span className="mdfe-protocol">{manifest.protocolo_encerramento || manifest.protocolo_autorizacao || "—"}</span></td>
                      <td><ManifestActions manifest={manifest} history={history} canDownload={canImport} downloading={downloadingKey === manifest.chave} onDetails={setDetails} onDownload={downloadXml} onClose={openClosing} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mdfe-mobile-list">
            {loading ? [...Array(3)].map((_, index) => <div className="mdfe-manifest-card skeleton-card" key={index}><span className="mdfe-skeleton card-title" /><span className="mdfe-skeleton card-line" /><span className="mdfe-skeleton card-line" /></div>) : items.map((manifest) => (
              <article className="mdfe-manifest-card" key={manifest.chave}>
                <header><div><span>MDF-e</span><strong>{manifest.numero ? Number(manifest.numero) : "Número não disponível"}</strong></div><StatusBadge status={manifest.situacao} label={manifest.situacao_display} /></header>
                <dl>
                  <div><dt>Motorista</dt><dd>{manifest.condutores?.map((driver) => driver.nome).join(", ") || (manifest.xml_status === "ERRO" ? "XML indisponível" : "Aguardando XML")}</dd></div>
                  <div><dt>Destino</dt><dd>{manifest.destinos?.map((destination) => `${destination.municipio}/${destination.uf}`).join(", ") || "Não disponível"}</dd></div>
                  <div><dt>Emissão</dt><dd>{formatDate(manifest.data_emissao)}</dd></div>
                  <div><dt>Última consulta</dt><dd>{formatDateTime(manifest.ultima_consulta_em)}</dd></div>
                </dl>
                {manifest.xml_somente_informativo && <span className="mdfe-card-note"><UiIcon name="info" size={15} /> Motorista e destino são apenas informativos.</span>}
                <div className="mdfe-card-key"><span>Chave de acesso</span><KeyValue value={manifest.chave} /></div>
                <ManifestActions manifest={manifest} history={history} canDownload={canImport} downloading={downloadingKey === manifest.chave} onDetails={setDetails} onDownload={downloadXml} onClose={openClosing} />
              </article>
            ))}
          </div>

          {!loading && items.length === 0 && <EmptyState history={history} search={search} filter={filter} consultation={consultation} lastSuccess={lastSuccess} />}

          <footer className="mdfe-pagination">
            <span>{count} registro(s)</span>
            <div>
              <button type="button" aria-label="Página anterior" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}><UiIcon name="chevronLeft" size={17} /> Anterior</button>
              <span>Página {page} de {totalPages}</span>
              <button type="button" aria-label="Próxima página" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)}>Próxima <UiIcon name="chevronRight" size={17} /></button>
            </div>
          </footer>
        </section>
      </div>

      {details && (
        <Modal title={`Detalhes do MDF-e ${details.numero ? Number(details.numero) : ""}`} onClose={() => setDetails(null)}>
          <div className="mdfe-details">
            <div className="mdfe-details-heading"><StatusBadge status={details.situacao} label={details.situacao_display} />{details.xml_somente_informativo && <span className="mdfe-xml-badge">XML informativo</span>}</div>
            <dl>
              <div><dt>Chave de acesso</dt><dd><code>{details.chave}</code><button type="button" className="icon-button" onClick={() => navigator.clipboard?.writeText(details.chave)} aria-label="Copiar chave"><UiIcon name="copy" size={16} /></button></dd></div>
              <div><dt>Motorista</dt><dd>{details.condutores?.map((driver) => driver.nome).join(", ") || "Não disponível"}</dd></div>
              <div><dt>Destino</dt><dd>{details.destinos?.map((destination) => `${destination.municipio}/${destination.uf} (${destination.codigo})`).join(", ") || "Não disponível"}</dd></div>
              <div><dt>Emissão</dt><dd>{formatDateTime(details.data_emissao)}</dd></div>
              <div><dt>Última consulta</dt><dd>{formatDateTime(details.ultima_consulta_em)}</dd></div>
              <div><dt>Protocolo</dt><dd>{details.protocolo_encerramento || details.protocolo_autorizacao || "Não disponível"}</dd></div>
              <div><dt>XML</dt><dd>{details.xml_status_display || "Não disponível"}{details.xml_classificacao_display ? ` · ${details.xml_classificacao_display}` : ""}</dd></div>
            </dl>
            <div className="mdfe-modal-actions">
              <button type="button" className="mdfe-btn secondary" onClick={() => setDetails(null)}>Fechar</button>
              {details.situacao === "ABERTO" && !history && <button type="button" className="mdfe-btn danger" onClick={() => { setDetails(null); openClosing(details); }}>Encerrar MDF-e</button>}
            </div>
          </div>
        </Modal>
      )}

      {selected && (
        <Modal title="Confirmar encerramento do MDF-e" onClose={() => { if (!processing) { setSelected(null); setOperation(null); } }}>
          {operation ? (
            <div className="mdfe-result">
              <div className={`mdfe-result-icon ${operation.estado.toLowerCase()}`}><UiIcon name={operation.estado === "HOMOLOGADO" ? "check" : "warning"} size={28} /></div>
              <h3>{operation.estado === "HOMOLOGADO" ? "MDF-e encerrado com sucesso" : operation.estado_display}</h3>
              <dl><div><dt>Número</dt><dd>{operation.manifesto_numero ? Number(operation.manifesto_numero) : "Não disponível"}</dd></div><div><dt>Chave</dt><dd>{operation.manifesto_chave}</dd></div><div><dt>Código / resultado</dt><dd>{operation.codigo_sefaz || "—"} — {operation.descricao_sefaz}</dd></div><div><dt>Protocolo oficial</dt><dd>{operation.protocolo || "Ainda não disponível"}</dd></div><div><dt>Registro</dt><dd>{formatDateTime(operation.registrado_em)}</dd></div><div><dt>Município</dt><dd>{operation.municipio_nome} / {operation.uf}</dd></div></dl>
              <div className="mdfe-modal-actions">{operation.protocolo && <button type="button" className="mdfe-btn secondary" onClick={() => navigator.clipboard?.writeText(operation.protocolo)}><UiIcon name="copy" size={17} /> Copiar protocolo</button>}{operation.estado === "A_CONFIRMAR" && <button type="button" className="mdfe-btn primary" disabled={processing} onClick={confirmPending}>Consultar situação oficial</button>}<button type="button" className="mdfe-btn primary" onClick={() => { setSelected(null); setOperation(null); }}>Fechar</button></div>
            </div>
          ) : (
            <form onSubmit={submitClosing} className="mdfe-form">
              <div className="mdfe-document"><span>MDF-e {selected.numero ? Number(selected.numero) : "sem número disponível"}</span><code>{selected.chave}</code><small>Protocolo de autorização: {selected.protocolo_autorizacao}</small></div>
              {selected.xml_somente_informativo && <p className="mdfe-informational-note"><UiIcon name="warning" size={18} /><span><strong>Atenção:</strong> motorista e destino vieram de um XML informativo. O sistema não usa esses dados neste encerramento; confirme manualmente o município abaixo.</span></p>}
              <div className="mdfe-form-grid"><label>UF do encerramento<select required value={closing.uf} onChange={(event) => setClosing((value) => ({ ...value, uf: event.target.value, municipality: null }))}><option value="">Selecione</option>{UF.map((value) => <option key={value}>{value}</option>)}</select></label><MunicipalityField uf={closing.uf} value={closing.municipality} onSelect={(municipality) => setClosing((value) => ({ ...value, municipality }))} /><label>Data efetiva do encerramento<input type="date" required value={closing.date} onChange={(event) => setClosing((value) => ({ ...value, date: event.target.value }))} /></label></div>
              <label className="mdfe-confirm"><input type="checkbox" checked={closing.confirmation} onChange={(event) => setClosing((value) => ({ ...value, confirmation: event.target.checked }))} />Confirmo que a viagem foi concluída no local e na data informados.</label>
              <div className="mdfe-modal-actions"><button type="button" className="mdfe-btn secondary" disabled={processing} onClick={() => setSelected(null)}>Cancelar</button><button className="mdfe-btn danger" disabled={processing}>{processing ? "Transmitindo à SEFAZ…" : "Confirmar encerramento"}</button></div>
            </form>
          )}
        </Modal>
      )}

      {configurationOpen && (
        <Modal title="Configuração fiscal da transportadora" onClose={() => !processing && setConfigurationOpen(false)} wide>
          <form className="mdfe-form" onSubmit={saveConfiguration}>
            <p className="mdfe-security-note"><UiIcon name="shield" size={19} /><span>O certificado e a senha são criptografados no backend e nunca retornam para esta tela. Deixe o arquivo em branco para manter o certificado atual.</span></p>
            <div className="mdfe-form-grid"><label>Razão social<input name="razao_social" required defaultValue={configuration?.razao_social || activeCompany?.nome || ""} /></label><label>CNPJ<input name="cnpj" required maxLength="18" defaultValue={configuration?.cnpj || ""} /></label><label>UF do estabelecimento<select name="uf" required defaultValue={configuration?.uf || ""}><option value="">Selecione</option>{UF.filter((value) => value !== "EX").map((value) => <option key={value}>{value}</option>)}</select></label><label>Ambiente fiscal<select name="ambiente" defaultValue={configuration?.ambiente || "HOMOLOGACAO"}><option value="HOMOLOGACAO">Homologação</option><option value="PRODUCAO">Produção</option></select></label><label>Certificado A1 (.pfx ou .p12)<input name="certificado" type="file" accept=".pfx,.p12" /></label><label>Senha do novo certificado<input name="senha_certificado" type="password" autoComplete="new-password" /></label></div>
            {configuration?.certificado_configurado && <div className="mdfe-certificate"><strong><UiIcon name="check" size={17} /> Certificado configurado</strong><span>Válido até {formatDateTime(configuration.certificado_valido_ate)}</span><span>Fingerprint SHA-256: {configuration.certificado_fingerprint}</span></div>}
            <label className="mdfe-confirm production"><input name="confirmar_producao" value="true" type="checkbox" />Confirmo a liberação administrativa para produção. Esta opção só funciona quando o servidor também estiver explicitamente habilitado.</label>
            <div className="mdfe-modal-actions"><button type="button" className="mdfe-btn secondary" onClick={() => setConfigurationOpen(false)}>Cancelar</button><button className="mdfe-btn primary" disabled={processing}>{processing ? "Validando certificado…" : "Salvar configuração"}</button></div>
          </form>
        </Modal>
      )}
    </main>
  );
}
