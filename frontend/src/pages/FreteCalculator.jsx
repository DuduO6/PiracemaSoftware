import { useEffect, useMemo, useState } from "react";

import { calcularFrete } from "../services/freteService";
import { importarDocumentoFiscal } from "../services/seguroCargasService";
import municipiosBrasil from "../data/municipiosBrasil.json";
import "../styles/freteCalculator.css";

const ESTADOS = [
  "", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
  "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE",
  "SP", "TO",
];

const TIPOS_CARGA = [
  { value: "granel_solido", label: "Granel sólido", descricao: "Carga sólida a granel, como grãos, farelo, areia ou minério." },
  { value: "granel_liquido", label: "Granel líquido", descricao: "Carga líquida a granel, como combustíveis, leite ou químicos." },
  { value: "frigorificada_aquecida", label: "Frigorificada ou Aquecida", descricao: "Carga que depende de controle térmico." },
  { value: "conteinerizada", label: "Conteinerizada", descricao: "Carga movimentada em contêiner." },
  { value: "carga_geral", label: "Carga Geral", descricao: "Carga geral paletizada, ensacada ou embalada." },
  { value: "neogranel", label: "Neogranel", descricao: "Carga unitizada ou agrupada, sem embalagem final ao consumidor." },
  { value: "perigosa_granel_solido", label: "Perigosa (granel sólido)", descricao: "Produto perigoso sólido transportado a granel." },
  { value: "perigosa_granel_liquido", label: "Perigosa (granel líquido)", descricao: "Produto perigoso líquido transportado a granel." },
  { value: "perigosa_frigorificada_aquecida", label: "Perigosa (frigorificada ou aquecida)", descricao: "Produto perigoso com controle térmico." },
  { value: "perigosa_conteinerizada", label: "Perigosa (conteinerizada)", descricao: "Produto perigoso transportado em contêiner." },
  { value: "perigosa_carga_geral", label: "Perigosa (carga geral)", descricao: "Produto perigoso tratado como carga geral." },
  { value: "granel_pressurizada", label: "Carga Granel Pressurizada", descricao: "Carga a granel transportada sob pressão." },
];

const initialForm = {
  cidade_origem: "",
  estado_origem: "",
  cidade_destino: "",
  estado_destino: "",
  quantidade_eixos: "6",
  tipo_carga: "carga_geral",
  composicao_veicular: true,
  alto_desempenho: false,
  retorno_vazio: false,
  adicionar_lucro_adicional: false,
  percentual_lucro_adicional: "0",
  peso_estimado_toneladas: "0",
  valor_carga: "",
  multiplicador_seguro: "2",
  acrescimo_fixo_seguro: "6.00",
  piso_seguro: "30.00",
  proporcao_rctrc: "50",
  precisao_percentual: "6",
  margem_adicional: "200.00",
  pedagio: "0.00",
  outras_despesas: "0.00",
};

const formatarMoeda = valor =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor || 0));

const formatarNumero = valor =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(Number(valor || 0));

const normalizarTexto = valor =>
  valor.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

function RoutePreview({ pontos }) {
  const viewBox = useMemo(() => {
    if (!pontos?.length) {
      return { path: "", box: "0 0 100 100", start: null, end: null };
    }
    const lngs = pontos.map(ponto => ponto.lng);
    const lats = pontos.map(ponto => ponto.lat);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const width = Math.max(maxLng - minLng, 0.01);
    const height = Math.max(maxLat - minLat, 0.01);
    const project = ponto => {
      const x = ((ponto.lng - minLng) / width) * 100;
      const y = 100 - (((ponto.lat - minLat) / height) * 100);
      return { x: x.toFixed(2), y: y.toFixed(2) };
    };
    const path = pontos.map((ponto, index) => {
      const projected = project(ponto);
      return `${index === 0 ? "M" : "L"} ${projected.x} ${projected.y}`;
    }).join(" ");
    return { path, box: "0 0 100 100", start: project(pontos[0]), end: project(pontos[pontos.length - 1]) };
  }, [pontos]);

  if (!pontos?.length) {
    return <div className="frete-route-empty">Sem geometria disponível para visualização.</div>;
  }

  return (
    <svg className="frete-route-map" viewBox={viewBox.box} preserveAspectRatio="none" role="img" aria-label="Prévia do percurso da rota">
      <defs>
        <linearGradient id="route-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="100" height="100" rx="10" fill="#f8fafc" />
      <path d={viewBox.path} fill="none" stroke="url(#route-gradient)" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={viewBox.start?.x} cy={viewBox.start?.y} r="4" fill="#1d4ed8" />
      <circle cx={viewBox.end?.x} cy={viewBox.end?.y} r="4" fill="#0f766e" />
    </svg>
  );
}

function FreteCalculator() {
  const [formData, setFormData] = useState(initialForm);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [municipiosOrigem, setMunicipiosOrigem] = useState([]);
  const [municipiosDestino, setMunicipiosDestino] = useState([]);
  const [mostrarRota, setMostrarRota] = useState(false);
  const [importandoXml, setImportandoXml] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const queryOrigem = formData.cidade_origem.trim();
  const queryDestino = formData.cidade_destino.trim();
  const tipoCargaAtual = TIPOS_CARGA.find(item => item.value === formData.tipo_carga);

  useEffect(() => {
    try {
      const documento = JSON.parse(localStorage.getItem("piracema.documentoFiscal"));
      const config = JSON.parse(localStorage.getItem("piracema.seguro.configuracao"));
      setFormData(prev => ({
        ...prev,
        ...(config ? {
          multiplicador_seguro: config.multiplicador || prev.multiplicador_seguro,
          acrescimo_fixo_seguro: config.acrescimo_fixo || prev.acrescimo_fixo_seguro,
          piso_seguro: config.piso_comercial || prev.piso_seguro,
          proporcao_rctrc: config.proporcao_rctrc || prev.proporcao_rctrc,
          precisao_percentual: config.precisao_percentual || prev.precisao_percentual,
          margem_adicional: config.margem_adicional || prev.margem_adicional,
        } : {}),
        ...(documento ? {
          cidade_origem: documento.cidade_origem || prev.cidade_origem,
          estado_origem: documento.uf_origem || prev.estado_origem,
          cidade_destino: documento.cidade_destino || prev.cidade_destino,
          estado_destino: documento.uf_destino || prev.estado_destino,
          valor_carga: documento.valor_carga || prev.valor_carga,
          peso_estimado_toneladas: documento.peso_toneladas || prev.peso_estimado_toneladas,
        } : {}),
      }));
    } catch {
      // Mantém o formulário padrão se não houver dados compartilhados válidos.
    }
  }, []);

  const handleChange = event => {
    const { name, value, type, checked } = event.target;
    setFormData(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  useEffect(() => {
    if (queryOrigem.length < 2) {
      setMunicipiosOrigem([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      const term = normalizarTexto(queryOrigem);
      setMunicipiosOrigem(
        municipiosBrasil.filter(item => normalizarTexto(item.label).includes(term)).slice(0, 12)
      );
    }, 200);
    return () => clearTimeout(timer);
  }, [queryOrigem]);

  useEffect(() => {
    if (queryDestino.length < 2) {
      setMunicipiosDestino([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      const term = normalizarTexto(queryDestino);
      setMunicipiosDestino(
        municipiosBrasil.filter(item => normalizarTexto(item.label).includes(term)).slice(0, 12)
      );
    }, 200);
    return () => clearTimeout(timer);
  }, [queryDestino]);

  const selecionarMunicipio = (tipo, municipio) => {
    if (tipo === "origem") {
      setFormData(prev => ({ ...prev, cidade_origem: municipio.cidade, estado_origem: municipio.estado }));
      setMunicipiosOrigem([]);
      return;
    }
    setFormData(prev => ({ ...prev, cidade_destino: municipio.cidade, estado_destino: municipio.estado }));
    setMunicipiosDestino([]);
  };

  const handleImportXml = async event => {
    const arquivo = event.target.files?.[0];
    if (!arquivo) return;
    setImportandoXml(true); setErro(""); setMensagem("");
    try {
      const documento = await importarDocumentoFiscal(arquivo);
      localStorage.setItem("piracema.documentoFiscal", JSON.stringify(documento));
      setFormData(prev => ({
        ...prev,
        cidade_origem: documento.cidade_origem || prev.cidade_origem,
        estado_origem: documento.uf_origem,
        cidade_destino: documento.cidade_destino || prev.cidade_destino,
        estado_destino: documento.uf_destino,
        valor_carga: documento.valor_carga,
        peso_estimado_toneladas: documento.peso_toneladas || prev.peso_estimado_toneladas,
      }));
      setMensagem(`${documento.tipo_documento} importado. Revise os dados antes de calcular.`);
    } catch (requestError) {
      setErro(requestError.response?.data?.detail || "Não foi possível ler o XML.");
    } finally {
      setImportandoXml(false);
      event.target.value = "";
    }
  };

  const copiarPercentual = async (valor, rotulo) => {
    await navigator.clipboard.writeText(valor);
    setMensagem(`${rotulo} copiado.`);
  };

  const handleSubmit = async event => {
    event.preventDefault();
    setErro("");
    setMensagem("");
    setResultado(null);
    setMostrarRota(false);
    setLoading(true);
    try {
      const response = await calcularFrete({
        ...formData,
        quantidade_eixos: Number(formData.quantidade_eixos),
        percentual_lucro_adicional: Number(formData.percentual_lucro_adicional),
        peso_estimado_toneladas: Number(formData.peso_estimado_toneladas),
        valor_carga: formData.valor_carga || null,
        precisao_percentual: formData.precisao_percentual,
      });
      setResultado(response);
    } catch (requestError) {
      setErro(requestError.response?.data?.detail || "Não foi possível calcular o frete com os dados informados.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="frete-page">
      <section className="frete-hero">
        <div>
          <p className="frete-kicker">Calculadora de Frete</p>
          <h1>Calcule o piso mínimo pela metodologia oficial da ANTT</h1>
          <p className="frete-description">
            Informe local de carga, descarga, tipo de carga e a configuração do veículo. O sistema calcula a rota, aplica a tabela ANTT correta e mostra o valor oficial.
          </p>
        </div>
      </section>

      <section className="frete-layout">
        <form className="frete-card frete-form" onSubmit={handleSubmit}>
          <div className="frete-card-header">
            <h2>Parâmetros do cálculo</h2>
            <span>Campos alinhados à lógica da calculadora oficial da ANTT.</span>
          </div>

          <label className="frete-xml-upload">
            {importandoXml ? "Lendo XML..." : "Importar XML de NF-e ou CT-e"}
            <input type="file" accept=".xml,text/xml,application/xml" onChange={handleImportXml} disabled={importandoXml} />
          </label>

          <div className="frete-grid">
            <label>
              Município de carregamento
              <small>Cidade onde a carga será embarcada.</small>
              <div className="frete-autocomplete">
                <input name="cidade_origem" value={formData.cidade_origem} onChange={handleChange} placeholder="Digite o município de origem" autoComplete="off" />
                {municipiosOrigem.length ? (
                  <div className="frete-autocomplete-list">
                    {municipiosOrigem.map(municipio => (
                      <button type="button" key={`origem-${municipio.id}`} className="frete-autocomplete-item" onClick={() => selecionarMunicipio("origem", municipio)}>
                        {municipio.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </label>
            <label>
              UF origem
              <small>Estado da cidade de carregamento.</small>
              <select name="estado_origem" value={formData.estado_origem} onChange={handleChange}>
                {ESTADOS.map(estado => <option key={`origem-${estado || "vazio"}`} value={estado}>{estado || "Selecione"}</option>)}
              </select>
            </label>
            <label>
              Município de descarga
              <small>Cidade onde a carga será entregue.</small>
              <div className="frete-autocomplete">
                <input name="cidade_destino" value={formData.cidade_destino} onChange={handleChange} placeholder="Digite o município de destino" autoComplete="off" />
                {municipiosDestino.length ? (
                  <div className="frete-autocomplete-list">
                    {municipiosDestino.map(municipio => (
                      <button type="button" key={`destino-${municipio.id}`} className="frete-autocomplete-item" onClick={() => selecionarMunicipio("destino", municipio)}>
                        {municipio.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </label>
            <label>
              UF destino
              <small>Estado da cidade de descarga.</small>
              <select name="estado_destino" value={formData.estado_destino} onChange={handleChange}>
                {ESTADOS.map(estado => <option key={`destino-${estado || "vazio"}`} value={estado}>{estado || "Selecione"}</option>)}
              </select>
            </label>
            <label>
              Tipo de carga
              <small>{tipoCargaAtual?.descricao}</small>
              <select name="tipo_carga" value={formData.tipo_carga} onChange={handleChange}>
                {TIPOS_CARGA.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              Número de eixos
              <small>Total de eixos da operação informada.</small>
              <input type="number" min="1" name="quantidade_eixos" value={formData.quantidade_eixos} onChange={handleChange} />
            </label>
            <label>
              Peso estimado (toneladas)
              <small>Opcional. Serve para sugerir valor por tonelada.</small>
              <input type="number" step="0.01" min="0" name="peso_estimado_toneladas" value={formData.peso_estimado_toneladas} onChange={handleChange} />
            </label>
            <label>
              Valor total da carga
              <small>Usado na planilha de seguro e nos percentuais.</small>
              <input inputMode="decimal" name="valor_carga" value={formData.valor_carga} onChange={handleChange} placeholder="100000.00" />
            </label>
            <label>
              Margem comercial (R$)
              <small>Componente adicional, padrão R$ 200,00.</small>
              <input inputMode="decimal" name="margem_adicional" value={formData.margem_adicional} onChange={handleChange} />
            </label>
            <label>
              Pedágio (R$)
              <small>Somado separadamente quando aplicável.</small>
              <input inputMode="decimal" name="pedagio" value={formData.pedagio} onChange={handleChange} />
            </label>
            <label>
              Outras despesas (R$)
              <small>Custos adicionais informados para a operação.</small>
              <input inputMode="decimal" name="outras_despesas" value={formData.outras_despesas} onChange={handleChange} />
            </label>
            <label>
              Lucro adicional (%)
              <small>Opcional. Acrescenta margem sobre o valor da tabela.</small>
              <input
                type="number"
                step="0.01"
                min="0"
                name="percentual_lucro_adicional"
                value={formData.percentual_lucro_adicional}
                onChange={handleChange}
                disabled={!formData.adicionar_lucro_adicional}
              />
            </label>
          </div>

          <details className="frete-insurance-config">
            <summary>Configuração do seguro e dos percentuais</summary>
            <div className="frete-grid">
              <label>Multiplicador<input inputMode="decimal" name="multiplicador_seguro" value={formData.multiplicador_seguro} onChange={handleChange} /></label>
              <label>Acréscimo fixo (R$)<input inputMode="decimal" name="acrescimo_fixo_seguro" value={formData.acrescimo_fixo_seguro} onChange={handleChange} /></label>
              <label>Piso do seguro (R$)<input inputMode="decimal" name="piso_seguro" value={formData.piso_seguro} onChange={handleChange} /></label>
              <label>Proporção RCTR-C (%)<input inputMode="decimal" name="proporcao_rctrc" value={formData.proporcao_rctrc} onChange={handleChange} /></label>
              <label>Casas decimais do emissor<input type="number" min="1" max="10" name="precisao_percentual" value={formData.precisao_percentual} onChange={handleChange} /></label>
            </div>
            <p>A divisão inicial 50/50 é apenas ilustrativa e não corresponde às taxas efetivas de uma apólice.</p>
          </details>

          <div className="frete-checks">
            <label className="frete-check">
              <input type="checkbox" name="composicao_veicular" checked={formData.composicao_veicular} onChange={handleChange} />
              <span>É composição veicular?</span>
              <small>Marque para usar a tabela de composição veicular ou caminhão simples.</small>
            </label>
            <label className="frete-check">
              <input type="checkbox" name="alto_desempenho" checked={formData.alto_desempenho} onChange={handleChange} />
              <span>É alto desempenho?</span>
              <small>Use quando a operação se enquadrar como alto desempenho na regra da ANTT.</small>
            </label>
            <label className="frete-check">
              <input type="checkbox" name="retorno_vazio" checked={formData.retorno_vazio} onChange={handleChange} />
              <span>Retorno vazio?</span>
              <small>Aplica o adicional de retorno vazio quando for devido na operação.</small>
            </label>
            <label className="frete-check">
              <input type="checkbox" name="adicionar_lucro_adicional" checked={formData.adicionar_lucro_adicional} onChange={handleChange} />
              <span>Adicionar lucro adicional</span>
              <small>Inclui uma margem comercial sobre o piso mínimo calculado.</small>
            </label>
          </div>

          {erro ? <div className="frete-alert erro">{erro}</div> : null}
          {mensagem ? <div className="frete-alert sucesso">{mensagem}</div> : null}

          <div className="frete-actions">
            <button type="submit" className="frete-button" disabled={loading}>
              {loading ? "Calculando..." : "Calcular Frete ANTT"}
            </button>
          </div>
        </form>

        <div className="frete-card frete-results">
          <div className="frete-card-header">
            <h2>Resultado</h2>
            <span>Resumo oficial do cálculo com rota automática e coeficientes ANTT.</span>
          </div>

          {resultado ? (
            <>
              {resultado.avisos?.length ? (
                <div className="frete-alert aviso">
                  {resultado.avisos.map(aviso => <p key={aviso}>{aviso}</p>)}
                </div>
              ) : null}

              <div className="frete-highlights">
                <article><span>Distância</span><strong>{formatarNumero(resultado.rota.distancia_km)} km</strong></article>
                <article><span>Tempo estimado</span><strong>{resultado.rota.duracao_formatada}</strong></article>
                <article><span>Valor da ida</span><strong>{formatarMoeda(resultado.calculo.valor_ida)}</strong></article>
                <article><span>Valor tabela ANTT</span><strong>{formatarMoeda(resultado.calculo.valor_total_tabela_antt)}</strong></article>
              </div>

              <div className="frete-detail-grid">
                <section>
                  <h3>Cálculo ANTT</h3>
                  <dl>
                    <div><dt>Operação</dt><dd>{resultado.antt.tabela_label}</dd></div>
                    <div><dt>Descrição da operação</dt><dd>{resultado.antt.tabela_descricao}</dd></div>
                    <div><dt>Tipo de carga</dt><dd>{resultado.antt.tipo_carga_label}</dd></div>
                    <div><dt>CCD</dt><dd>{formatarNumero(resultado.antt.ccd)}</dd></div>
                    <div><dt>CC</dt><dd>{formatarMoeda(resultado.antt.cc)}</dd></div>
                    <div><dt>Retorno vazio</dt><dd>{formatarMoeda(resultado.calculo.valor_retorno_vazio)}</dd></div>
                  </dl>
                </section>

                <section>
                  <h3>Referência</h3>
                  <dl>
                    <div><dt>Origem</dt><dd>{resultado.origem.cidade}{resultado.origem.estado ? ` - ${resultado.origem.estado}` : ""}</dd></div>
                    <div><dt>Destino</dt><dd>{resultado.destino.cidade}{resultado.destino.estado ? ` - ${resultado.destino.estado}` : ""}</dd></div>
                    <div><dt>Eixos informados</dt><dd>{formatarNumero(resultado.antt.quantidade_eixos_informada)}</dd></div>
                    <div><dt>Eixos aplicados</dt><dd>{formatarNumero(resultado.antt.quantidade_eixos_aplicada)}</dd></div>
                    <div><dt>Fonte</dt><dd>{resultado.antt.referencia}</dd></div>
                    <div><dt>Valor final</dt><dd>{formatarMoeda(resultado.frete.valor_total)}</dd></div>
                  </dl>
                </section>
              </div>

              {resultado.seguro_cargas ? (
                <>
                  <section className="frete-commercial-panel">
                    <h3>Seguro de cargas</h3>
                    <div className="frete-commercial-grid">
                      <article><span>UF origem / destino</span><strong>{resultado.seguro_cargas.origem} → {resultado.seguro_cargas.destino}</strong></article>
                      <article><span>Valor total da carga</span><strong>{formatarMoeda(resultado.seguro_cargas.valor_carga)}</strong></article>
                      <article><span>Valor original da planilha</span><strong>{formatarMoeda(resultado.seguro_cargas.planilha.valor_original)}</strong></article>
                      <article><span>Seguro calculado</span><strong>{formatarMoeda(resultado.seguro_cargas.seguro.valor_final)}</strong></article>
                    </div>
                    <p>Piso comercial de {formatarMoeda(resultado.seguro_cargas.seguro.parametros.piso_comercial)}: {resultado.seguro_cargas.seguro.piso_aplicado ? "aplicado" : "não aplicado"}.</p>
                  </section>

                  <section className="frete-commercial-panel">
                    <h3>Percentuais para informar no emissor de CT-e</h3>
                    <p>{resultado.seguro_cargas.percentuais.descricao}; não são taxas oficiais da apólice.</p>
                    <div className="frete-percentual-row"><div><span>RCTR-C</span><strong>{resultado.seguro_cargas.percentuais.rctrc}%</strong><small>{formatarMoeda(resultado.seguro_cargas.percentuais.valor_efetivo_rctrc)}</small></div><button type="button" onClick={() => copiarPercentual(resultado.seguro_cargas.percentuais.rctrc, "RCTR-C")}>Copiar</button></div>
                    <div className="frete-percentual-row"><div><span>RC-DC</span><strong>{resultado.seguro_cargas.percentuais.rcdc}%</strong><small>{formatarMoeda(resultado.seguro_cargas.percentuais.valor_efetivo_rcdc)}</small></div><button type="button" onClick={() => copiarPercentual(resultado.seguro_cargas.percentuais.rcdc, "RC-DC")}>Copiar</button></div>
                    <dl className="frete-commercial-breakdown"><div><dt>Soma efetiva</dt><dd>{formatarMoeda(resultado.seguro_cargas.percentuais.seguro_reconstituido)}</dd></div><div><dt>Seguro esperado</dt><dd>{formatarMoeda(resultado.seguro_cargas.percentuais.seguro_esperado)}</dd></div><div><dt>Diferença de arredondamento</dt><dd>{formatarMoeda(resultado.seguro_cargas.percentuais.diferenca_arredondamento)}</dd></div></dl>
                    {!resultado.seguro_cargas.percentuais.reproduz_exatamente ? <div className="frete-alert aviso">A precisão configurada não reproduz exatamente o seguro esperado.</div> : null}
                  </section>

                  <section className="frete-final-card">
                    <span>VALOR FINAL SUGERIDO DO FRETE</span>
                    <strong>{formatarMoeda(resultado.valor_final_sugerido.total)}</strong>
                    <dl className="frete-commercial-breakdown"><div><dt>Piso mínimo ANTT</dt><dd>{formatarMoeda(resultado.valor_final_sugerido.piso_minimo_antt)}</dd></div><div><dt>Seguro final</dt><dd>{formatarMoeda(resultado.valor_final_sugerido.seguro_final)}</dd></div><div><dt>Margem adicional</dt><dd>{formatarMoeda(resultado.valor_final_sugerido.margem_adicional)}</dd></div><div><dt>Pedágio</dt><dd>{formatarMoeda(resultado.valor_final_sugerido.pedagio)}</dd></div><div><dt>Outras despesas</dt><dd>{formatarMoeda(resultado.valor_final_sugerido.outras_despesas)}</dd></div></dl>
                    <p>Seguro e margem são componentes comerciais adicionais, não coeficientes da tabela ANTT. O pedágio permanece discriminado separadamente.</p>
                  </section>
                </>
              ) : (
                <div className="frete-alert aviso">Informe o valor da carga para incluir seguro, percentuais RCTR-C/RC-DC e o valor final sugerido.</div>
              )}

              <div className="frete-route-actions">
                <button type="button" className="frete-secondary-button" onClick={() => setMostrarRota(prev => !prev)}>
                  {mostrarRota ? "Ocultar informações da rota" : "Informações da rota"}
                </button>
              </div>

              {mostrarRota ? (
                <section className="frete-route-panel">
                  <div className="frete-route-panel-header">
                    <div>
                      <h3>Percurso estimado</h3>
                      <p>Prévia visual da rota e cidades de referência ao longo do caminho.</p>
                    </div>
                  </div>
                  <RoutePreview pontos={resultado.rota.geometria_preview} />
                  {resultado.rota.rodovias_referencia?.length ? (
                    <div className="frete-route-roads">
                      {resultado.rota.rodovias_referencia.map(rodovia => <span key={rodovia}>{rodovia}</span>)}
                    </div>
                  ) : null}
                  <div className="frete-route-cities">
                    {resultado.rota.cidades_referencia?.map(cidade => <span key={cidade}>{cidade}</span>)}
                  </div>
                </section>
              ) : null}

              {resultado.rentabilidade.sugestoes_valor_por_tonelada && Object.keys(resultado.rentabilidade.sugestoes_valor_por_tonelada).length ? (
                <section className="frete-sugestoes">
                  <h3>Sugestão de valor por tonelada</h3>
                  <div className="frete-sugestoes-grid">
                    <article><span>Base</span><strong>{formatarMoeda(resultado.rentabilidade.valor_por_tonelada)}</strong></article>
                    <article><span>Lucro de 10%</span><strong>{formatarMoeda(resultado.rentabilidade.sugestoes_valor_por_tonelada.lucro_10)}</strong></article>
                    <article><span>Lucro de 20%</span><strong>{formatarMoeda(resultado.rentabilidade.sugestoes_valor_por_tonelada.lucro_20)}</strong></article>
                    <article><span>Lucro de 30%</span><strong>{formatarMoeda(resultado.rentabilidade.sugestoes_valor_por_tonelada.lucro_30)}</strong></article>
                  </div>
                </section>
              ) : null}
            </>
          ) : (
            <div className="frete-empty-state">
              <p>Os coeficientes ANTT, a rota e o valor oficial do frete aparecerão aqui.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default FreteCalculator;
