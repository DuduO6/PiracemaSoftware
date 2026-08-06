import { useEffect, useMemo, useState } from "react";
import { Circle, CircleMarker, LayersControl, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

import {
  calcularFrete,
  criarEmpresaInicial,
  listarEmpresas,
  listarOportunidades,
  listarPerfis,
  listarPolosNacionais,
  listarProdutosLogisticos,
  listarIndicadoresFrete,
  listarRegioesLogisticas,
  planejarReposicionamento,
  recomendarOportunidades,
  registrarResultadoDecisao,
} from "../services/inteligenciaLogisticaService";
import "../styles/inteligenciaLogistica.css";
import TruckLoader from "../components/TruckLoader";
import { getTileProvider } from "../config/mapProviders";
import municipiosBrasil from "../data/municipiosBrasil.json";

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

const normalizar = (texto) => String(texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function MunicipioInput({ label, value, onSelect, required = false, placeholder = "Digite uma cidade" }) {
  const [aberto, setAberto] = useState(false);
  const opcoes = useMemo(() => {
    const termo = normalizar(value);
    if (termo.length < 2) return [];
    return municipiosBrasil.filter((item) => normalizar(item.label).includes(termo)).slice(0, 10);
  }, [value]);
  return <label className="municipio-field">{label}<input required={required} value={value} placeholder={placeholder} autoComplete="off" onFocus={() => setAberto(true)} onBlur={() => setTimeout(() => setAberto(false), 150)} onChange={(e) => { onSelect({ cidade: e.target.value, estado: null }); setAberto(true); }} />{aberto && opcoes.length > 0 && <div className="municipio-options">{opcoes.map((item) => <button type="button" key={item.id} onMouseDown={() => onSelect(item)}>{item.label}</button>)}</div>}</label>;
}

function mensagemErro(error) {
  return error.response?.data?.detail || "Não foi possível concluir a operação.";
}

function AjustarMapa({ pontos }) {
  const mapa = useMap();
  useEffect(() => {
    if (pontos.length) mapa.fitBounds(L.latLngBounds(pontos), { padding: [35, 35] });
  }, [mapa, pontos]);
  return null;
}

function CamadaCalor({ pontos }) {
  const mapa = useMap();
  useEffect(() => {
    if (!pontos.length || !L.heatLayer) return undefined;
    const camada = L.heatLayer(pontos.map((ponto) => [ponto[0], ponto[1], .7]), { radius: 28, blur: 20, gradient: { .2: "#2ca25f", .55: "#f4c95d", 1: "#d73027" } }).addTo(mapa);
    return () => mapa.removeLayer(camada);
  }, [mapa, pontos]);
  return null;
}

function MapaRotas({ planejamento, indiceAtivo }) {
  const sugestao = planejamento?.sugestoes?.[indiceAtivo];
  const segmentos = useMemo(() => [
    { pontos: sugestao?.geometria_vazio, cor: "#dc8c28", nome: "Trecho vazio", tracejada: true },
    { pontos: sugestao?.geometria_carregada, cor: "#168557", nome: "Corredor histórico" },
    { pontos: sugestao?.geometria_destino_pessoal, cor: "#326db3", nome: "Até destino pessoal", tracejada: true },
  ].filter((item) => item.pontos?.length), [sugestao]);
  if (!sugestao) return <div className="intel-map-empty">Faça uma busca para visualizar as rotas.</div>;
  const tile = getTileProvider();
  const toLatLng = (ponto) => [ponto.lat, ponto.lng];
  const todosPontos = segmentos.flatMap((segmento) => segmento.pontos.map(toLatLng));
  const marcadores = [[sugestao.origem.coordenadas, `Carregamento: ${sugestao.origem.cidade}`, "#dc8c28"], [sugestao.destino_historico.coordenadas, `Destino histórico: ${sugestao.destino_historico.cidade}`, "#168557"]];
  if (planejamento.destino_pessoal) marcadores.push([planejamento.destino_pessoal.coordenadas, `Destino pessoal: ${planejamento.destino_pessoal.cidade}`, "#326db3"]);
  return (
    <div className="intel-map-wrap">
      <MapContainer className="intel-leaflet-map" center={toLatLng(sugestao.origem.coordenadas)} zoom={7} scrollWheelZoom>
        <TileLayer url={tile.url} attribution={tile.attribution} maxZoom={tile.maxZoom} />
        <LayersControl position="topright">
          <LayersControl.Overlay checked name="Rotas">
            <>{segmentos.map((segmento) => <Polyline key={segmento.nome} positions={segmento.pontos.map(toLatLng)} pathOptions={{ color: segmento.cor, weight: 6, opacity: .92, dashArray: segmento.tracejada ? "10 9" : undefined }} />)}</>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Pontos logísticos">
            <>{marcadores.map(([ponto, titulo, cor]) => <CircleMarker key={titulo} center={toLatLng(ponto)} radius={9} pathOptions={{ color: "#fff", weight: 3, fillColor: cor, fillOpacity: 1 }}><Popup>{titulo}</Popup></CircleMarker>)}</>
          </LayersControl.Overlay>
          <LayersControl.Overlay name="Heatmap da rota"><CamadaCalor pontos={todosPontos} /></LayersControl.Overlay>
          <LayersControl.Overlay name={`Geofence ${planejamento.raio_km} km`}><Circle center={toLatLng(planejamento.centro_busca.coordenadas)} radius={planejamento.raio_km * 1000} pathOptions={{ color: "#176b47", fillColor: "#8fd3ad", fillOpacity: .12 }} /></LayersControl.Overlay>
        </LayersControl>
        <AjustarMapa pontos={todosPontos} />
      </MapContainer>
      <div className="intel-map-legend"><span className="empty">Vazio até carga</span><span className="loaded">Rota histórica carregada</span><span className="personal">Caminho até destino pessoal</span></div>
    </div>
  );
}

export default function InteligenciaLogistica() {
  const [empresas, setEmpresas] = useState([]);
  const [empresaId, setEmpresaId] = useState(localStorage.getItem("empresa_logistica_id") || "");
  const [oportunidades, setOportunidades] = useState([]);
  const [perfis, setPerfis] = useState([]);
  const [perfilId, setPerfilId] = useState("");
  const [selecionadas, setSelecionadas] = useState([]);
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [planejamento, setPlanejamento] = useState(null);
  const [sugestaoAtiva, setSugestaoAtiva] = useState(0);
  const [busca, setBusca] = useState({ cidade_atual: "Uberlândia", estado_atual: "MG", destino_pessoal: "Divinópolis", estado_destino_pessoal: "MG", raio_km: 200, modo: "AUTOMATICO", regiao_busca: "", local_busca: "", estado_local_busca: "MG" });
  const [polosNacionais, setPolosNacionais] = useState([]);
  const [produtosNacionais, setProdutosNacionais] = useState([]);
  const [indicadoresNacionais, setIndicadoresNacionais] = useState([]);
  const [filtroPolo, setFiltroPolo] = useState("");
  const [regioesLogisticas, setRegioesLogisticas] = useState([]);
  const [filtrosCarga, setFiltrosCarga] = useState({ origem: "", destino: "", carga: "" });
  const [ordenacaoCarga, setOrdenacaoCarga] = useState("valor_km_com_vazio_desc");
  const [carregandoMaisHistorico, setCarregandoMaisHistorico] = useState(false);
  const [simulacao, setSimulacao] = useState({ origem: "Uberlândia", estado_origem: "MG", destino: "Divinópolis", estado_destino: "MG", valor_frete: 0, valor_pedagios_informado: "", eixos: 6 });
  const [resultadoSimulacao, setResultadoSimulacao] = useState(null);
  const [resultadoReal, setResultadoReal] = useState({ aceitou_sugestao: true, receita: "", custos_totais: "", lucro_liquido: "", km_vazio: "", tempo_espera_horas: "", retorno_vazio: false });
  const [resultadoRealSalvo, setResultadoRealSalvo] = useState(false);

  useEffect(() => {
    listarEmpresas()
      .then(async ({ data }) => {
        if (!data.length) {
          const criada = await criarEmpresaInicial();
          data = [criada.data];
        }
        setEmpresas(data);
        const empresaArmazenada = localStorage.getItem("empresa_logistica_id") || "";
        const atual = data.some((empresa) => String(empresa.id) === String(empresaArmazenada))
          ? empresaArmazenada
          : data[0]?.id || "";
        if (atual) {
          localStorage.setItem("empresa_logistica_id", atual);
          setEmpresaId(String(atual));
        }
      })
      .catch((error) => setErro(mensagemErro(error)))
      .finally(() => setCarregando(false));
  }, []); // A empresa inicial é resolvida uma única vez.

  useEffect(() => {
    if (!empresaId) return;
    localStorage.setItem("empresa_logistica_id", empresaId);
    setCarregando(true);
    setResultado(null);
    Promise.all([listarOportunidades(), listarPerfis()])
      .then(([oportunidadesResponse, perfisResponse]) => {
        setOportunidades(oportunidadesResponse.data);
        setPerfis(perfisResponse.data);
        setSelecionadas(oportunidadesResponse.data.map((item) => item.id));
        setErro("");
      })
      .catch((error) => setErro(mensagemErro(error)))
      .finally(() => setCarregando(false));
  }, [empresaId]);

  useEffect(() => {
    Promise.all([listarPolosNacionais(), listarProdutosLogisticos(), listarIndicadoresFrete(), listarRegioesLogisticas()])
      .then(([polos, produtos, indicadores, regioes]) => {
        setPolosNacionais(polos.data);
        setProdutosNacionais(produtos.data);
        setIndicadoresNacionais(indicadores.data);
        setRegioesLogisticas(regioes.data);
      })
      .catch((error) => setErro(mensagemErro(error)));
  }, []);

  const fretesHistoricosFiltrados = useMemo(() => (planejamento?.fretes_historicos || []).filter((item) => {
    const contem = (valor, filtro) => !filtro || String(valor || "").toLocaleLowerCase("pt-BR").includes(filtro.toLocaleLowerCase("pt-BR"));
    return contem(item.origem, filtrosCarga.origem)
      && contem(item.destino, filtrosCarga.destino)
      && contem(item.cliente, filtrosCarga.carga);
  }).sort((a, b) => {
    if (ordenacaoCarga === "valor_km_carregado_desc") return (b.valor_km_carregado || 0) - (a.valor_km_carregado || 0);
    if (ordenacaoCarga === "menor_km_vazio") return (a.km_vazio_calculado ?? Infinity) - (b.km_vazio_calculado ?? Infinity);
    if (ordenacaoCarga === "maior_receita") return Number(b.valor_total || 0) - Number(a.valor_total || 0);
    return (b.valor_km_com_vazio || 0) - (a.valor_km_com_vazio || 0);
  }), [filtrosCarga, planejamento, ordenacaoCarga]);

  const recomendar = async () => {
    if (!selecionadas.length) {
      setErro("Selecione ao menos uma oportunidade.");
      return;
    }
    setCarregando(true);
    try {
      const payload = { oportunidade_ids: selecionadas, operacao: "MAXIMIZAR_LUCRO" };
      if (perfilId) payload.perfil_id = Number(perfilId);
      const { data } = await recomendarOportunidades(payload);
      setResultado(data);
      setResultadoRealSalvo(false);
      setErro("");
    } catch (error) {
      setErro(mensagemErro(error));
    } finally {
      setCarregando(false);
    }
  };

  const salvarResultadoReal = async (event) => {
    event.preventDefault();
    try {
      const numericos = ["receita", "custos_totais", "lucro_liquido", "km_vazio", "tempo_espera_horas"];
      const valores = Object.fromEntries(numericos.filter((campo) => resultadoReal[campo] !== "").map((campo) => [campo, Number(resultadoReal[campo])]));
      valores.retorno_vazio = resultadoReal.retorno_vazio;
      await registrarResultadoDecisao(resultado.recommendation_id, { aceitou_sugestao: resultadoReal.aceitou_sugestao, avaliacao: "RESULTADO_REGISTRADO", resultado_real: valores });
      setResultadoRealSalvo(true);
      setErro("");
    } catch (error) { setErro(mensagemErro(error)); }
  };

  const atualizarBusca = (campo, valor) => setBusca((atual) => ({ ...atual, [campo]: valor }));
  const selecionarMunicipio = (campoCidade, campoEstado) => (municipio) => setBusca((atual) => ({ ...atual, [campoCidade]: municipio.cidade, ...(municipio.estado ? { [campoEstado]: municipio.estado } : {}) }));
  const selecionarMunicipioSimulacao = (campoCidade, campoEstado) => (municipio) => setSimulacao((atual) => ({ ...atual, [campoCidade]: municipio.cidade, ...(municipio.estado ? { [campoEstado]: municipio.estado } : {}) }));

  const simularFrete = async (event) => {
    event.preventDefault();
    setCarregando(true);
    try {
      const payload = { ...simulacao, valor_frete: Number(simulacao.valor_frete), valor_pedagios_informado: simulacao.valor_pedagios_informado === "" ? null : Number(simulacao.valor_pedagios_informado) };
      const { data } = await calcularFrete(payload);
      setResultadoSimulacao(data);
      setErro("");
    } catch (error) { setErro(mensagemErro(error)); } finally { setCarregando(false); }
  };

  const buscarRotas = async (event) => {
    event.preventDefault();
    setCarregando(true);
    try {
      const { data } = await planejarReposicionamento({ ...busca, pagina_historico: 1, tamanho_pagina_historico: 4 });
      setPlanejamento(data);
      setSugestaoAtiva(0);
      setErro("");
    } catch (error) {
      setErro(mensagemErro(error));
    } finally {
      setCarregando(false);
    }
  };

  const buscarMaisHistorico = async () => {
    if (!planejamento?.fretes_historicos_paginacao?.tem_proxima) return;
    setCarregandoMaisHistorico(true);
    try {
      const proximaPagina = planejamento.fretes_historicos_paginacao.pagina + 1;
      const { data } = await planejarReposicionamento({ ...busca, pagina_historico: proximaPagina, tamanho_pagina_historico: 4 });
      setPlanejamento((atual) => ({ ...data, fretes_historicos: [...atual.fretes_historicos, ...data.fretes_historicos] }));
      setErro("");
    } catch (error) { setErro(mensagemErro(error)); } finally { setCarregandoMaisHistorico(false); }
  };

  return (
    <section className="intel-page">
      {carregando && <TruckLoader mensagem={planejamento ? "Atualizando análise logística..." : "Buscando as melhores rotas..."} />}
      <header className="intel-header">
        <div>
          <h1>Inteligência Logística</h1>
        </div>
        <div className="intel-controls">
          <label>
            Empresa
            <select value={empresaId} onChange={(event) => setEmpresaId(event.target.value)}>
              {empresas.map((empresa) => <option key={empresa.id} value={empresa.id}>{empresa.nome}</option>)}
            </select>
          </label>
          <label>
            Perfil estratégico
            <select value={perfilId} onChange={(event) => setPerfilId(event.target.value)}>
              <option value="">Pesos padrão da empresa</option>
              {perfis.map((perfil) => <option key={perfil.id} value={perfil.id}>{perfil.nome}</option>)}
            </select>
          </label>
          <button onClick={recomendar} disabled={carregando || !empresaId}>
            {carregando ? "Gerando sugestão..." : "Sugestão da IA"}
          </button>
        </div>
      </header>

      {erro && <div className="intel-alert error">{erro}</div>}
      {resultado?.avisos?.map((aviso) => <div className="intel-alert" key={aviso}>{aviso}</div>)}

      <section className="route-planner">
        <div className="planner-title"><div><span className="intel-eyebrow dark">Reposicionamento inteligente</span><h2>Onde está o caminhão?</h2></div>{planejamento && <strong>{planejamento.total_viagens_analisadas} viagens analisadas</strong>}</div>
        <form className="planner-form" onSubmit={buscarRotas}>
          <label>Modo<select value={busca.modo} onChange={(e) => atualizarBusca("modo", e.target.value)}><option value="AUTOMATICO">Automático — meus carregamentos</option><option value="MANUAL">Buscar perto de outro local</option></select></label>
          <label>Região logística<select value={busca.regiao_busca} onChange={(e) => atualizarBusca("regiao_busca", e.target.value)}><option value="">Todas as regiões</option>{regioesLogisticas.map((regiao) => <option value={regiao.codigo} key={regiao.codigo}>{regiao.nome}</option>)}</select></label>
          <MunicipioInput label="Cidade atual" required value={busca.cidade_atual} onSelect={selecionarMunicipio("cidade_atual", "estado_atual")} />
          <label>UF<input required maxLength="2" value={busca.estado_atual} onChange={(e) => atualizarBusca("estado_atual", e.target.value.toUpperCase())} /></label>
          {busca.modo === "MANUAL" && <><MunicipioInput label="Centro da busca" required value={busca.local_busca} onSelect={selecionarMunicipio("local_busca", "estado_local_busca")} placeholder="Ex.: Araguari" /><label>UF da busca<input required maxLength="2" value={busca.estado_local_busca} onChange={(e) => atualizarBusca("estado_local_busca", e.target.value.toUpperCase())} /></label></>}
          <MunicipioInput label="Destino pessoal (opcional)" value={busca.destino_pessoal} onSelect={selecionarMunicipio("destino_pessoal", "estado_destino_pessoal")} placeholder="Ex.: Divinópolis" />
          <label>UF destino<input maxLength="2" value={busca.estado_destino_pessoal} onChange={(e) => atualizarBusca("estado_destino_pessoal", e.target.value.toUpperCase())} /></label>
          <label className="radius-control">Raio: <strong>{busca.raio_km} km</strong><input type="range" min="10" max="500" step="10" value={busca.raio_km} onChange={(e) => atualizarBusca("raio_km", Number(e.target.value))} /></label>
          <button disabled={carregando || !empresaId}>{carregando ? "Consultando rotas..." : "Sugerir menor vazio"}</button>
        </form>

        {planejamento && <div className="planner-results">
          <MapaRotas planejamento={planejamento} indiceAtivo={sugestaoAtiva} />
          <div className="historical-suggestions">
            {planejamento.sugestoes.length ? planejamento.sugestoes.map((item, indice) => <button type="button" key={`${item.origem.cidade}-${item.destino_historico.cidade}`} className={indice === sugestaoAtiva ? "active" : ""} onClick={() => setSugestaoAtiva(indice)}>
              <span className={`confidence ${item.confianca.toLowerCase()}`}>Confiança {item.confianca}</span>
              <strong>{item.origem.cidade} → {item.destino_historico.cidade}</strong>
              <small>{item.cliente_principal} · {item.ocorrencias_corredor} ocorrência(s)</small>
              <div><span><b>{item.km_vazio_ate_carregamento}</b> km vazio</span><span><b>{item.km_rota_historica}</b> km carregado</span></div>
              {item.desvio_estimado_destino_pessoal_km !== null && <em>Desvio estimado até o destino pessoal: {item.desvio_estimado_destino_pessoal_km} km</em>}
              <small>Receita média histórica: {moeda.format(item.receita_media_historica)} · Peso médio: {item.peso_medio_t} t</small>
            </button>) : <div className="intel-empty">Nenhum local histórico ficou dentro do raio escolhido.</div>}
          </div>
        </div>}
      </section>

      {resultado && (
        <div className="intel-summary">
          <div><span>Modo</span><strong>{resultado.modo}</strong></div>
          <div><span>Alternativas válidas</span><strong>{resultado.alternativas.length}</strong></div>
          <div><span>Descartadas por regras</span><strong>{resultado.descartadas.length}</strong></div>
          <div><span>Recomendação</span><strong>#{resultado.recommendation_id}</strong></div>
        </div>
      )}

      {resultado?.recomendada && (() => {
        const oportunidade = oportunidades.find((item) => item.id === resultado.recomendada.oportunidade_id);
        return oportunidade ? <section className="ai-logistics-suggestion"><div><span className="intel-eyebrow dark">Sugestão para maximizar lucro</span><h2>{oportunidade.origem} → {oportunidade.destino}</h2><p>{oportunidade.tipo_carga} · recomendação #{resultado.recommendation_id}</p></div><dl><div><dt>Lucro imediato</dt><dd>{moeda.format(resultado.recomendada.lucro_imediato)}</dd></div><div><dt>Lucro esperado do ciclo</dt><dd>{moeda.format(resultado.recomendada.lucro_esperado_ciclo)}</dd></div><div><dt>Nota logística</dt><dd>{resultado.recomendada.score_final.toFixed(1)}</dd></div><div><dt>R$/km com vazio</dt><dd>{resultado.recomendada.valor_km_com_vazio ? moeda.format(resultado.recomendada.valor_km_com_vazio) : "Indisponível"}</dd></div></dl><form className="real-result-form" onSubmit={salvarResultadoReal}><strong>Registrar resultado real</strong><label><input type="checkbox" checked={resultadoReal.aceitou_sugestao} onChange={(e) => setResultadoReal((r) => ({ ...r, aceitou_sugestao: e.target.checked }))} /> Sugestão aceita</label><input type="number" step="0.01" required placeholder="Receita real" value={resultadoReal.receita} onChange={(e) => setResultadoReal((r) => ({ ...r, receita: e.target.value }))} /><input type="number" step="0.01" required placeholder="Custos totais" value={resultadoReal.custos_totais} onChange={(e) => setResultadoReal((r) => ({ ...r, custos_totais: e.target.value }))} /><input type="number" step="0.01" required placeholder="Lucro líquido real" value={resultadoReal.lucro_liquido} onChange={(e) => setResultadoReal((r) => ({ ...r, lucro_liquido: e.target.value }))} /><input type="number" step="0.01" placeholder="Km vazio real" value={resultadoReal.km_vazio} onChange={(e) => setResultadoReal((r) => ({ ...r, km_vazio: e.target.value }))} /><input type="number" step="0.1" placeholder="Espera em horas" value={resultadoReal.tempo_espera_horas} onChange={(e) => setResultadoReal((r) => ({ ...r, tempo_espera_horas: e.target.value }))} /><label><input type="checkbox" checked={resultadoReal.retorno_vazio} onChange={(e) => setResultadoReal((r) => ({ ...r, retorno_vazio: e.target.checked }))} /> Houve retorno vazio</label><button>{resultadoRealSalvo ? "Resultado salvo" : "Salvar resultado"}</button></form></section> : null;
      })()}

      <section className="load-marketplace">
        <div className="planner-title"><div><span className="intel-eyebrow dark">Histórico vinculado ao reposicionamento</span><h2>Rotas já feitas neste raio</h2></div><strong>{fretesHistoricosFiltrados.length} resultado(s)</strong></div>
        <div className="market-filters"><label>Origem<input value={filtrosCarga.origem} onChange={(e) => setFiltrosCarga((f) => ({ ...f, origem: e.target.value }))} placeholder="Cidade ou estado" /></label><label>Destino<input value={filtrosCarga.destino} onChange={(e) => setFiltrosCarga((f) => ({ ...f, destino: e.target.value }))} placeholder="Cidade ou estado" /></label><label>Cliente<input value={filtrosCarga.carga} onChange={(e) => setFiltrosCarga((f) => ({ ...f, carga: e.target.value }))} placeholder="Nome do cliente" /></label><label>Ordenar por<select value={ordenacaoCarga} onChange={(e) => setOrdenacaoCarga(e.target.value)}><option value="valor_km_com_vazio_desc">Maior R$/km com vazio</option><option value="valor_km_carregado_desc">Maior R$/km carregado</option><option value="menor_km_vazio">Menor trecho vazio</option><option value="maior_receita">Maior valor do frete</option></select></label></div>
      <div className="intel-grid">
        {fretesHistoricosFiltrados.map((item) => {
          const valorKmCarregado = Number(item.valor_km_carregado || 0);
          const valorKmComVazio = Number(item.valor_km_com_vazio || 0);
          return (
            <article key={item.viagem_id} className="intel-card historical-freight">
              <div className="intel-card-top">
                <span className="intel-badge">VIAGEM REALIZADA</span><time>{new Date(`${item.data}T12:00:00`).toLocaleDateString("pt-BR")}</time>
              </div>
              <h2>{item.cliente}</h2>
              <p className="intel-route">{item.origem} <span>→</span> {item.destino}</p>
              <dl>
                <div><dt>Valor realizado</dt><dd>{moeda.format(item.valor_total)}</dd></div>
                <div><dt>Peso</dt><dd>{Number(item.peso_t).toLocaleString("pt-BR")} t</dd></div>
                <div><dt>Valor por tonelada</dt><dd>{moeda.format(item.valor_tonelada)}</dd></div>
                <div><dt>Km vazio até a origem</dt><dd>{Number(item.km_vazio_calculado).toLocaleString("pt-BR")} km</dd></div>
                <div><dt>Km carregado estimado</dt><dd>{Number(item.km_carregado_estimado).toLocaleString("pt-BR")} km</dd></div>
                <div><dt>R$/km sem vazio</dt><dd>{valorKmCarregado ? moeda.format(valorKmCarregado) : "Indisponível"}</dd></div>
                <div><dt>R$/km com vazio</dt><dd className={item.classificacao === "BOM" ? "km-good" : "km-bad"}>{valorKmComVazio ? `${moeda.format(valorKmComVazio)} · ${item.classificacao}` : "Indisponível"}</dd></div>
                <div><dt>CT-e</dt><dd>{item.teve_cte ? item.numero_cte || "Sim" : "Não"}</dd></div><div><dt>Pagamento</dt><dd>{item.pago ? "Pago" : "Pendente"}</dd></div>
              </dl>
              <div className="freight-source"><span>Fonte: viagens registradas pela empresa</span><a href="https://www.fretebras.com.br/fretes" target="_blank" rel="noreferrer">Procurar fretes parecidos no FreteBras ↗</a></div>
            </article>
          );
        })}
      </div>
      {planejamento?.fretes_historicos_paginacao?.tem_proxima && <button type="button" className="historical-load-more" disabled={carregandoMaisHistorico} onClick={buscarMaisHistorico}>{carregandoMaisHistorico ? "Carregando..." : "Ver mais"}</button>}
      {!planejamento && <div className="intel-empty">Informe a localização e o raio para consultar rotas já realizadas pela empresa.</div>}
      {planejamento && !fretesHistoricosFiltrados.length && <div className="intel-empty">Nenhuma viagem realizada corresponde aos corredores encontrados dentro de {planejamento.raio_km} km.</div>}
      </section>

      <section className="freight-calculator">
        <div className="planner-title"><div><span className="intel-eyebrow dark">Simulador de rentabilidade</span><h2>Calculadora de frete e rota</h2><p>Calcule distância rodoviária, tempo, pedágios e o valor efetivo por quilômetro.</p></div></div>
        <form className="calculator-form" onSubmit={simularFrete}>
          <MunicipioInput label="Origem" required value={simulacao.origem} onSelect={selecionarMunicipioSimulacao("origem", "estado_origem")} />
          <label>UF<input required maxLength="2" value={simulacao.estado_origem} onChange={(e) => setSimulacao((s) => ({ ...s, estado_origem: e.target.value.toUpperCase() }))} /></label>
          <MunicipioInput label="Destino" required value={simulacao.destino} onSelect={selecionarMunicipioSimulacao("destino", "estado_destino")} />
          <label>UF<input required maxLength="2" value={simulacao.estado_destino} onChange={(e) => setSimulacao((s) => ({ ...s, estado_destino: e.target.value.toUpperCase() }))} /></label>
          <label>Valor do frete (R$)<input required type="number" min="0" step="0.01" value={simulacao.valor_frete} onChange={(e) => setSimulacao((s) => ({ ...s, valor_frete: e.target.value }))} /></label>
          <label>Eixos do caminhão<input required type="number" min="2" max="10" value={simulacao.eixos} onChange={(e) => setSimulacao((s) => ({ ...s, eixos: Number(e.target.value) }))} /></label>
          <label>Pedágios conhecidos (opcional)<input type="number" min="0" step="0.01" value={simulacao.valor_pedagios_informado} onChange={(e) => setSimulacao((s) => ({ ...s, valor_pedagios_informado: e.target.value }))} placeholder="Preencha para conferir" /></label>
          <button disabled={carregando}>{carregando ? "Calculando..." : "Calcular viagem"}</button>
        </form>
        {resultadoSimulacao && <div className="calculator-results"><div><span>Distância</span><strong>{resultadoSimulacao.distancia_km.toLocaleString("pt-BR")} km</strong></div><div><span>Tempo estimado</span><strong>{resultadoSimulacao.duracao || "—"}</strong></div><div><span>Pedágios</span><strong>{resultadoSimulacao.valor_pedagios === null ? "A confirmar" : moeda.format(resultadoSimulacao.valor_pedagios)}</strong></div><div><span>R$/km bruto</span><strong>{moeda.format(resultadoSimulacao.valor_km_bruto || 0)}</strong></div><div><span>Após pedágios</span><strong>{moeda.format(resultadoSimulacao.valor_liquido_apos_pedagios)}</strong></div><div><span>R$/km após pedágios</span><strong>{moeda.format(resultadoSimulacao.valor_km_apos_pedagios || 0)}</strong></div>{resultadoSimulacao.pedagios?.length > 0 && <section className="toll-breakdown"><strong>Praças encontradas</strong>{resultadoSimulacao.pedagios.map((pedagio) => <div key={`${pedagio.nome}-${pedagio.rodovia}`}><span>{pedagio.nome} · {pedagio.rodovia}{pedagio.localizacao ? ` · ${pedagio.localizacao}` : ""}</span><b>{moeda.format(pedagio.valor)}</b></div>)}</section>}{resultadoSimulacao.aviso_pedagios && <p>{resultadoSimulacao.aviso_pedagios} <a href="https://pedagiometro.webrota.com.br/" target="_blank" rel="noreferrer">Consultar Pedagiômetro ↗</a></p>}</div>}
      </section>

      <section className="national-base">
        <div className="planner-title">
          <div><span className="intel-eyebrow dark">Conhecimento inicial compartilhado</span><h2>Base Nacional de Polos</h2><p>Referência inicial que perde peso conforme o histórico da transportadora cresce.</p></div>
          <div className="national-stats"><strong>{polosNacionais.length}</strong><span>polos</span><strong>{produtosNacionais.length}</strong><span>produtos</span></div>
        </div>
        <div className="national-filter">
          <label>Filtrar mercadoria<select value={filtroPolo} onChange={(e) => setFiltroPolo(e.target.value)}><option value="">Todas as categorias</option><option value="POLO_SOJA">Soja</option><option value="POLO_MILHO">Milho</option><option value="POLO_SORGO">Sorgo</option><option value="POLO_FERTILIZANTE">Fertilizantes</option><option value="POLO_CALCARIO">Calcário</option><option value="POLO_CIMENTO">Cimento</option></select></label>
          <span>Valores nacionais são referências de baixa confiança, não cotações atuais.</span>
        </div>
        <div className="national-grid">
          {polosNacionais.filter((polo) => !filtroPolo || polo.categorias.includes(filtroPolo)).slice(0, 18).map((polo) => <article key={polo.id}><div><strong>{polo.cidade}</strong><span>{polo.estado} · {polo.regiao.replace("_", "-")}</span></div><div className="category-chips">{polo.categorias.map((categoria) => <small key={categoria}>{categoria.replace("POLO_", "").replaceAll("_", " ")}</small>)}</div></article>)}
        </div>
        <details className="national-products"><summary>Compatibilidade de produtos e veículos</summary><div>{produtosNacionais.map((produto) => <article key={produto.id}><strong>{produto.produto}</strong><span>{produto.tipo_carga}</span><ul>{produto.veiculos_permitidos.map((veiculo) => <li key={`${produto.id}-${veiculo.tipo_veiculo}`}>{veiculo.tipo_veiculo}</li>)}</ul></article>)}</div></details>
        <details className="national-products"><summary>Indicadores iniciais de frete</summary><div>{indicadoresNacionais.map((indicador) => <article key={indicador.id}><strong>{indicador.produto_nome} · {indicador.faixa_distancia}</strong><span>R$ {indicador.faixa_minima_tkm}–{indicador.faixa_maxima_tkm} por t.km</span><small>Confiança {indicador.nivel_confianca}</small></article>)}</div></details>
      </section>

      {!carregando && !oportunidades.length && (
        <div className="intel-empty">Não há oportunidades cadastradas para esta empresa.</div>
      )}

    </section>
  );
}
