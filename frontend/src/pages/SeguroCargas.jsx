import { useEffect, useState } from "react";

import { calcularSeguroCargas, importarDocumentoFiscal } from "../services/seguroCargasService";
import { calcularFrete } from "../services/freteService";
import "../styles/seguroCargas.css";

const LOCALIDADES = [
  ["AC", "Acre"], ["AL", "Alagoas"], ["AP", "Amapá"], ["AM", "Amazonas"],
  ["BA", "Bahia"], ["CE", "Ceará"], ["DF", "Distrito Federal"], ["ES", "Espírito Santo"],
  ["GO", "Goiás"], ["MA", "Maranhão"], ["MT", "Mato Grosso"], ["MS", "Mato Grosso do Sul"],
  ["MG", "Minas Gerais"], ["PA", "Pará"], ["PB", "Paraíba"], ["PR", "Paraná"],
  ["PE", "Pernambuco"], ["PI", "Piauí"], ["RJ", "Rio de Janeiro"], ["RN", "Rio Grande do Norte"],
  ["RS", "Rio Grande do Sul"], ["RO", "Rondônia"], ["RR", "Roraima"], ["SC", "Santa Catarina"],
  ["SP", "São Paulo"], ["SE", "Sergipe"], ["TO", "Tocantins"], ["Urbano", "Urbano"],
];

const CONFIG_KEY = "piracema.seguro.configuracao";
const DOCUMENT_KEY = "piracema.documentoFiscal";
const DECIMAL_PATTERN = /^\d+(?:[.,]\d+)?$/;

const initialForm = {
  origem: "", destino: "", cidade_origem: "", cidade_destino: "", valor_carga: "", peso_estimado_toneladas: "0",
  quantidade_eixos: "6", tipo_carga: "carga_geral", composicao_veicular: true, alto_desempenho: false, retorno_vazio: false,
  multiplicador: "2", acrescimo_fixo: "6.00",
  piso_comercial: "30.00", proporcao_rctrc: "50", precisao_percentual: "6",
  percentual_rctrc_manual: "", percentual_rcdc_manual: "", taxa_real_rctrc: "",
  taxa_real_rcdc: "", margem_adicional: "200.00", pedagio: "0.00", outras_despesas: "0.00",
};

const formatarMoeda = valor => new Intl.NumberFormat("pt-BR", {
  style: "currency", currency: "BRL",
}).format(valor === null || valor === undefined || valor === "" ? 0 : valor);

function SeguroCargas() {
  const [formData, setFormData] = useState(initialForm);
  const [usarPercentuaisManuais, setUsarPercentuaisManuais] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [resultadoAntt, setResultadoAntt] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [importando, setImportando] = useState(false);
  const [mensagem, setMensagem] = useState("");

  useEffect(() => {
    try {
      const config = JSON.parse(localStorage.getItem(CONFIG_KEY));
      const documento = JSON.parse(localStorage.getItem(DOCUMENT_KEY));
      setFormData(prev => ({
        ...prev,
        ...(config || {}),
        ...(documento ? {
          origem: documento.uf_origem || prev.origem,
          destino: documento.uf_destino || prev.destino,
          cidade_origem: documento.cidade_origem || prev.cidade_origem,
          cidade_destino: documento.cidade_destino || prev.cidade_destino,
          valor_carga: documento.valor_carga || prev.valor_carga,
          peso_estimado_toneladas: documento.peso_toneladas || prev.peso_estimado_toneladas,
        } : {}),
      }));
    } catch {
      // Mantém os padrões quando a configuração local não é válida.
    }
  }, []);

  const handleChange = event => {
    const { name, value, type, checked } = event.target;
    setFormData(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const validar = () => {
    if (!formData.origem || !formData.destino) return "Origem e destino são obrigatórios.";
    if (!formData.cidade_origem.trim() || !formData.cidade_destino.trim()) return "Os municípios de origem e destino são obrigatórios para calcular a quilometragem e o piso ANTT.";
    if (!DECIMAL_PATTERN.test(formData.valor_carga) || /^0+(?:[.,]0+)?$/.test(formData.valor_carga)) return "Informe um valor de carga maior que zero.";
    if (usarPercentuaisManuais && (!DECIMAL_PATTERN.test(formData.percentual_rctrc_manual) || !DECIMAL_PATTERN.test(formData.percentual_rcdc_manual))) return "Informe os dois percentuais manuais.";
    return "";
  };

  const payload = () => ({
    ...formData,
    valor_carga: formData.valor_carga.replace(",", "."),
    percentual_rctrc_manual: usarPercentuaisManuais ? formData.percentual_rctrc_manual.replace(",", ".") : null,
    percentual_rcdc_manual: usarPercentuaisManuais ? formData.percentual_rcdc_manual.replace(",", ".") : null,
    taxa_real_rctrc: formData.taxa_real_rctrc ? formData.taxa_real_rctrc.replace(",", ".") : null,
    taxa_real_rcdc: formData.taxa_real_rcdc ? formData.taxa_real_rcdc.replace(",", ".") : null,
  });

  const handleSubmit = async event => {
    event.preventDefault();
    setErro(""); setMensagem("");
    setResultado(null); setResultadoAntt(null);
    const erroValidacao = validar();
    if (erroValidacao) { setErro(erroValidacao); return; }
    setLoading(true);
    try {
      const antt = await calcularFrete({
        cidade_origem: formData.cidade_origem.trim(),
        estado_origem: formData.origem,
        cidade_destino: formData.cidade_destino.trim(),
        estado_destino: formData.destino,
        quantidade_eixos: formData.quantidade_eixos,
        tipo_carga: formData.tipo_carga,
        composicao_veicular: formData.composicao_veicular,
        alto_desempenho: formData.alto_desempenho,
        retorno_vazio: formData.retorno_vazio,
        peso_estimado_toneladas: formData.peso_estimado_toneladas || "0",
      });
      setResultadoAntt(antt);
      setResultado(await calcularSeguroCargas({
        ...payload(),
        piso_minimo_antt: antt.calculo.valor_total_tabela_antt,
      }));
    } catch (requestError) {
      const data = requestError.response?.data;
      const primeiroErroCampo = data && typeof data === "object"
        ? Object.values(data).flat().find(Boolean)
        : null;
      setErro(data?.detail || data?.non_field_errors?.[0] || primeiroErroCampo || "Não foi possível calcular a rota ANTT e o seguro.");
    } finally { setLoading(false); }
  };

  const handleImport = async event => {
    const arquivo = event.target.files?.[0];
    if (!arquivo) return;
    setImportando(true); setErro(""); setMensagem("");
    try {
      const documento = await importarDocumentoFiscal(arquivo);
      localStorage.setItem(DOCUMENT_KEY, JSON.stringify(documento));
      setFormData(prev => ({
        ...prev,
        origem: documento.uf_origem,
        destino: documento.uf_destino,
        cidade_origem: documento.cidade_origem || "",
        cidade_destino: documento.cidade_destino || "",
        valor_carga: documento.valor_carga,
        peso_estimado_toneladas: documento.peso_toneladas || "0",
      }));
      setMensagem(`${documento.tipo_documento} importado. Municípios, UFs, carga e peso foram preenchidos; confirme e calcule.`);
    } catch (requestError) {
      setErro(requestError.response?.data?.detail || "Não foi possível ler o XML.");
    } finally { setImportando(false); event.target.value = ""; }
  };

  const salvarConfiguracao = () => {
    const campos = ["multiplicador", "acrescimo_fixo", "piso_comercial", "proporcao_rctrc", "precisao_percentual", "margem_adicional"];
    localStorage.setItem(CONFIG_KEY, JSON.stringify(Object.fromEntries(campos.map(campo => [campo, formData[campo]]))));
    setMensagem("Configuração padrão salva neste navegador.");
  };

  const copiar = async (valor, rotulo) => {
    await navigator.clipboard.writeText(valor);
    setMensagem(`${rotulo} copiado.`);
  };

  return (
    <div className="seguro-cargas-page">
      <section className="seguro-cargas-hero"><div><p className="seguro-cargas-kicker">Seguro de Cargas</p><h1>Calcule o seguro e os percentuais para informar no emissor</h1><p className="seguro-cargas-description">A matriz existente fornece o valor original. A regra comercial, a distribuição e o arredondamento são demonstrados separadamente, sem representar taxas oficiais da apólice.</p></div></section>

      <section className="seguro-cargas-grid">
        <form className="seguro-cargas-card seguro-cargas-form" onSubmit={handleSubmit}>
          <div className="seguro-cargas-card-header"><h2>Dados da operação</h2><span>Importe uma NF-e/CT-e ou preencha manualmente</span></div>
          <label className="seguro-upload">{importando ? "Lendo XML..." : "Importar XML de NF-e ou CT-e"}<input type="file" accept=".xml,text/xml,application/xml" onChange={handleImport} disabled={importando} /></label>
          <div className="seguro-cargas-fields seguro-fields-two">
            <label>Município de origem<input name="cidade_origem" value={formData.cidade_origem} onChange={handleChange} placeholder="Ex.: São Paulo" /></label>
            <label>UF de origem<select name="origem" value={formData.origem} onChange={handleChange}><option value="">Selecione</option>{LOCALIDADES.map(([value, label]) => <option key={`o-${value}`} value={value}>{label}</option>)}</select></label>
            <label>Município de destino<input name="cidade_destino" value={formData.cidade_destino} onChange={handleChange} placeholder="Ex.: Belo Horizonte" /></label>
            <label>UF de destino<select name="destino" value={formData.destino} onChange={handleChange}><option value="">Selecione</option>{LOCALIDADES.map(([value, label]) => <option key={`d-${value}`} value={value}>{label}</option>)}</select></label>
            <label>Valor total da carga<input name="valor_carga" inputMode="decimal" value={formData.valor_carga} onChange={handleChange} placeholder="100000.00" /></label>
            <label>Peso (toneladas)<input name="peso_estimado_toneladas" inputMode="decimal" value={formData.peso_estimado_toneladas} onChange={handleChange} /></label>
          </div>

          <details className="seguro-config" open><summary>Dados para o piso mínimo ANTT</summary><div className="seguro-cargas-fields seguro-fields-two">
            <label>Número de eixos<input type="number" min="1" name="quantidade_eixos" value={formData.quantidade_eixos} onChange={handleChange} /></label>
            <label>Tipo de carga<select name="tipo_carga" value={formData.tipo_carga} onChange={handleChange}><option value="carga_geral">Carga geral</option><option value="granel_solido">Granel sólido</option><option value="granel_liquido">Granel líquido</option><option value="frigorificada_aquecida">Frigorificada ou aquecida</option><option value="conteinerizada">Conteinerizada</option><option value="neogranel">Neogranel</option><option value="perigosa_carga_geral">Perigosa — carga geral</option><option value="perigosa_granel_solido">Perigosa — granel sólido</option><option value="perigosa_granel_liquido">Perigosa — granel líquido</option><option value="perigosa_frigorificada_aquecida">Perigosa — frigorificada/aquecida</option><option value="perigosa_conteinerizada">Perigosa — conteinerizada</option><option value="granel_pressurizada">Granel pressurizada</option></select></label>
          </div><div className="seguro-antt-checks"><label><input type="checkbox" name="composicao_veicular" checked={formData.composicao_veicular} onChange={handleChange} /> Composição veicular</label><label><input type="checkbox" name="alto_desempenho" checked={formData.alto_desempenho} onChange={handleChange} /> Alto desempenho</label><label><input type="checkbox" name="retorno_vazio" checked={formData.retorno_vazio} onChange={handleChange} /> Retorno vazio</label></div></details>

          <details className="seguro-config" open><summary>Parâmetros configuráveis</summary><div className="seguro-cargas-fields seguro-fields-two">
            <label>Multiplicador<input name="multiplicador" inputMode="decimal" value={formData.multiplicador} onChange={handleChange} /></label>
            <label>Acréscimo fixo (R$)<input name="acrescimo_fixo" inputMode="decimal" value={formData.acrescimo_fixo} onChange={handleChange} /></label>
            <label>Piso comercial (R$)<input name="piso_comercial" inputMode="decimal" value={formData.piso_comercial} onChange={handleChange} /></label>
            <label>Proporção RCTR-C (%)<input name="proporcao_rctrc" inputMode="decimal" value={formData.proporcao_rctrc} onChange={handleChange} /></label>
            <label>Casas decimais do emissor<input name="precisao_percentual" type="number" min="1" max="10" value={formData.precisao_percentual} onChange={handleChange} /></label>
            <label>Margem adicional (R$)<input name="margem_adicional" inputMode="decimal" value={formData.margem_adicional} onChange={handleChange} /></label>
            <label>Pedágio (R$)<input name="pedagio" inputMode="decimal" value={formData.pedagio} onChange={handleChange} /></label>
            <label>Outras despesas (R$)<input name="outras_despesas" inputMode="decimal" value={formData.outras_despesas} onChange={handleChange} /></label>
          </div><button type="button" className="seguro-link-button" onClick={salvarConfiguracao}>Salvar como padrão</button></details>

          <label className="seguro-toggle"><input type="checkbox" checked={usarPercentuaisManuais} onChange={event => setUsarPercentuaisManuais(event.target.checked)} />Modificar os percentuais manualmente</label>
          {usarPercentuaisManuais ? <div className="seguro-cargas-fields seguro-fields-two"><label>RCTR-C (%)<input name="percentual_rctrc_manual" inputMode="decimal" value={formData.percentual_rctrc_manual} onChange={handleChange} /></label><label>RC-DC (%)<input name="percentual_rcdc_manual" inputMode="decimal" value={formData.percentual_rcdc_manual} onChange={handleChange} /></label></div> : null}
          <details className="seguro-config"><summary>Taxas reais contratadas (referência opcional)</summary><p>Essas taxas ficam identificadas como referência e não alteram a distribuição comercial.</p><div className="seguro-cargas-fields seguro-fields-two"><label>RCTR-C real (%)<input name="taxa_real_rctrc" inputMode="decimal" value={formData.taxa_real_rctrc} onChange={handleChange} /></label><label>RC-DC real (%)<input name="taxa_real_rcdc" inputMode="decimal" value={formData.taxa_real_rcdc} onChange={handleChange} /></label></div></details>
          {erro ? <div className="seguro-cargas-alert erro">{erro}</div> : null}{mensagem ? <div className="seguro-cargas-alert sucesso">{mensagem}</div> : null}
          <div className="seguro-cargas-actions"><button type="submit" className="seguro-cargas-button" disabled={loading}>{loading ? "Calculando rota, ANTT e seguro..." : "Calcular ANTT + seguro"}</button><button type="button" className="seguro-cargas-button secondary" onClick={() => { setFormData(initialForm); setResultado(null); setResultadoAntt(null); setErro(""); }}>Limpar</button></div>
        </form>

        <div className="seguro-results-stack">
          {resultado ? <>
            {resultadoAntt ? <section className="seguro-cargas-card"><div className="seguro-cargas-card-header"><h2>Frete ANTT</h2><span>{resultadoAntt.origem.cidade} - {resultadoAntt.origem.estado} → {resultadoAntt.destino.cidade} - {resultadoAntt.destino.estado}</span></div><div className="seguro-cargas-summary"><div><strong>Quilometragem</strong><span>{resultadoAntt.calculo.distancia_km} km</span></div><div><strong>Piso mínimo ANTT</strong><span>{formatarMoeda(resultadoAntt.calculo.valor_total_tabela_antt)}</span></div><div><strong>Tipo de carga</strong><span>{resultadoAntt.antt.tipo_carga_label}</span></div><div><strong>Eixos aplicados</strong><span>{resultadoAntt.antt.quantidade_eixos_aplicada}</span></div><div><strong>Tabela utilizada</strong><span>{resultadoAntt.antt.tabela_label}</span></div><div><strong>CCD / CC</strong><span>{resultadoAntt.antt.ccd} / {formatarMoeda(resultadoAntt.antt.cc)}</span></div><div><strong>Peso</strong><span>{resultadoAntt.rentabilidade.peso_estimado_toneladas} t</span></div><div><strong>Valor por tonelada</strong><span>{resultadoAntt.rentabilidade.valor_por_tonelada === null ? "Não disponível" : formatarMoeda(resultadoAntt.rentabilidade.valor_por_tonelada)}</span></div></div></section> : null}
            <section className="seguro-cargas-card"><div className="seguro-cargas-card-header"><h2>Seguro de cargas</h2><span>{resultado.origem} → {resultado.destino}</span></div><div className="seguro-cargas-summary"><div><strong>Valor da carga</strong><span>{formatarMoeda(resultado.valor_carga)}</span></div><div><strong>Valor original da planilha</strong><span>{formatarMoeda(resultado.planilha.valor_original)}</span></div><div><strong>Seguro pela fórmula</strong><span>{formatarMoeda(resultado.seguro.valor_final)}</span></div><div><strong>Piso de R$ 30,00</strong><span>{resultado.seguro.piso_aplicado ? "Aplicado" : "Não aplicado"}</span></div></div><p className="seguro-formula">máx.({formatarMoeda(resultado.seguro.parametros.piso_comercial)}, valor da planilha × {resultado.seguro.parametros.multiplicador} + {formatarMoeda(resultado.seguro.parametros.acrescimo_fixo)})</p></section>
            <section className="seguro-cargas-card percentuais-card"><div className="seguro-cargas-card-header"><h2>Percentuais para informar no emissor de CT-e</h2><span>{resultado.percentuais.descricao}. Não são taxas oficiais da apólice.</span></div><div className="percentual-copy"><div><span>RCTR-C</span><strong>{resultado.percentuais.rctrc}%</strong></div><button type="button" onClick={() => copiar(resultado.percentuais.rctrc, "RCTR-C")}>Copiar</button></div><div className="percentual-copy"><div><span>RC-DC</span><strong>{resultado.percentuais.rcdc}%</strong></div><button type="button" onClick={() => copiar(resultado.percentuais.rcdc, "RC-DC")}>Copiar</button></div><dl className="seguro-breakdown"><div><dt>Valor efetivo RCTR-C</dt><dd>{formatarMoeda(resultado.percentuais.valor_efetivo_rctrc)}</dd></div><div><dt>Valor efetivo RC-DC</dt><dd>{formatarMoeda(resultado.percentuais.valor_efetivo_rcdc)}</dd></div><div><dt>Soma dos dois</dt><dd>{formatarMoeda(resultado.percentuais.seguro_reconstituido)}</dd></div><div><dt>Seguro esperado</dt><dd>{formatarMoeda(resultado.percentuais.seguro_esperado)}</dd></div><div><dt>Diferença de arredondamento</dt><dd>{formatarMoeda(resultado.percentuais.diferenca_arredondamento)}</dd></div></dl>{!resultado.percentuais.reproduz_exatamente ? <div className="seguro-cargas-alert aviso">Com {resultado.percentuais.precisao} casas decimais, os percentuais não reproduzem exatamente o seguro esperado.</div> : <div className="seguro-cargas-alert sucesso">Os percentuais arredondados reproduzem o seguro esperado em reais.</div>}</section>
            <section className="seguro-cargas-card valor-final-card"><span>VALOR FINAL SUGERIDO DO FRETE</span><strong>{formatarMoeda(resultado.valor_final.total)}</strong><dl className="seguro-breakdown"><div><dt>Piso mínimo ANTT</dt><dd>{formatarMoeda(resultado.valor_final.piso_minimo_antt)}</dd></div><div><dt>Seguro final</dt><dd>{formatarMoeda(resultado.valor_final.seguro_final)}</dd></div><div><dt>Margem comercial adicional</dt><dd>{formatarMoeda(resultado.valor_final.margem_adicional)}</dd></div><div><dt>Pedágio (se aplicável)</dt><dd>{formatarMoeda(resultado.valor_final.pedagio)}</dd></div><div><dt>Outras despesas</dt><dd>{formatarMoeda(resultado.valor_final.outras_despesas)}</dd></div></dl><p>Seguro e margem são componentes comerciais adicionais, não coeficientes da tabela ANTT. A conformidade depende da operação, da regulamentação vigente e do tratamento correto de pedágios e demais obrigações.</p></section>
          </> : <section className="seguro-cargas-card seguro-cargas-empty"><p>O seguro, os percentuais copiáveis e o valor final aparecerão após o cálculo.</p></section>}
        </div>
      </section>
    </div>
  );
}

export default SeguroCargas;
