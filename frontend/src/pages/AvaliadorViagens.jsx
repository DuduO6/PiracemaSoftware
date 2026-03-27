import { useEffect, useMemo, useState } from "react";

import municipiosBrasil from "../data/municipiosBrasil.json";
import { avaliarLucroViagem, listarViagens } from "../services/avaliadorViagemService";
import "../styles/avaliadorViagens.css";

const ESTADOS = [
  "", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
  "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE",
  "SP", "TO",
];

const initialForm = {
  viagem_id: "",
  media_km_por_litro: "2.50",
  preco_combustivel: "6.00",
  cidade_origem: "",
  estado_origem: "",
  cidade_destino: "",
  estado_destino: "",
};

const formatarMoeda = valor =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor || 0));

const formatarNumero = valor =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(Number(valor || 0));

const normalizarTexto = valor =>
  (valor || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

const localizarMunicipio = texto => {
  const target = normalizarTexto(texto);
  if (!target) return null;
  return municipiosBrasil.find(item => normalizarTexto(item.cidade) === target || normalizarTexto(item.label) === target) || null;
};

function AvaliadorViagens() {
  const [viagens, setViagens] = useState([]);
  const [formData, setFormData] = useState(initialForm);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [carregandoViagens, setCarregandoViagens] = useState(true);
  const [municipiosOrigem, setMunicipiosOrigem] = useState([]);
  const [municipiosDestino, setMunicipiosDestino] = useState([]);
  const [ajusteManual, setAjusteManual] = useState(false);

  useEffect(() => {
    listarViagens()
      .then(data => setViagens(data.sort((a, b) => new Date(b.data) - new Date(a.data))))
      .catch(() => setErro("Não foi possível carregar as viagens cadastradas."))
      .finally(() => setCarregandoViagens(false));
  }, []);

  const viagemSelecionada = useMemo(
    () => viagens.find(item => String(item.id) === String(formData.viagem_id)) || null,
    [viagens, formData.viagem_id]
  );

  useEffect(() => {
    if (!viagemSelecionada) return;
    const origem = localizarMunicipio(viagemSelecionada.origem);
    const destino = localizarMunicipio(viagemSelecionada.destino);
    setFormData(prev => ({
      ...prev,
      cidade_origem: origem?.cidade || viagemSelecionada.origem || "",
      estado_origem: origem?.estado || "",
      cidade_destino: destino?.cidade || viagemSelecionada.destino || "",
      estado_destino: destino?.estado || "",
    }));
    setAjusteManual(!origem || !destino);
  }, [viagemSelecionada]);

  useEffect(() => {
    const query = formData.cidade_origem.trim();
    if (query.length < 2) {
      setMunicipiosOrigem([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      const term = normalizarTexto(query);
      setMunicipiosOrigem(municipiosBrasil.filter(item => normalizarTexto(item.label).includes(term)).slice(0, 10));
    }, 180);
    return () => clearTimeout(timer);
  }, [formData.cidade_origem]);

  useEffect(() => {
    const query = formData.cidade_destino.trim();
    if (query.length < 2) {
      setMunicipiosDestino([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      const term = normalizarTexto(query);
      setMunicipiosDestino(municipiosBrasil.filter(item => normalizarTexto(item.label).includes(term)).slice(0, 10));
    }, 180);
    return () => clearTimeout(timer);
  }, [formData.cidade_destino]);

  const handleChange = event => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const selecionarMunicipio = (tipo, municipio) => {
    if (tipo === "origem") {
      setFormData(prev => ({ ...prev, cidade_origem: municipio.cidade, estado_origem: municipio.estado }));
      setMunicipiosOrigem([]);
      return;
    }
    setFormData(prev => ({ ...prev, cidade_destino: municipio.cidade, estado_destino: municipio.estado }));
    setMunicipiosDestino([]);
  };

  const handleSubmit = async event => {
    event.preventDefault();
    setErro("");
    setResultado(null);
    setLoading(true);
    try {
      const response = await avaliarLucroViagem({
        ...formData,
        viagem_id: Number(formData.viagem_id),
        media_km_por_litro: Number(formData.media_km_por_litro),
        preco_combustivel: Number(formData.preco_combustivel),
      });
      setResultado(response);
    } catch (requestError) {
      setErro(requestError.response?.data?.detail || "Não foi possível avaliar a viagem selecionada.");
      setAjusteManual(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="avaliador-page">
      <section className="avaliador-hero">
        <div className="avaliador-hero-top">
          <p className="avaliador-kicker">Avaliador de Viagens</p>
          <span className="avaliador-badge">Em breve</span>
        </div>
        <h1>Veja quanto sobrou de lucro em uma viagem já lançada</h1>
        <p className="avaliador-description">
          Selecione a viagem, informe a média de consumo e o valor do combustível. O sistema calcula a rota, o custo estimado de combustível, a comissão de 13% do motorista e o lucro remanescente.
        </p>
        <div className="avaliador-coming-soon">
          <span>Esta tela está em breve e pode sofrer ajustes antes da versão final.</span>
        </div>
      </section>

      <section className="avaliador-layout">
        <form className="avaliador-card" onSubmit={handleSubmit}>
          <div className="avaliador-card-header">
            <h2>Dados da análise</h2>
            <span>O faturamento da viagem vem do lançamento já cadastrado.</span>
          </div>

          <div className="avaliador-grid">
            <label>
              Viagem lançada
              <small>Escolha a viagem que deseja analisar.</small>
              <select name="viagem_id" value={formData.viagem_id} onChange={handleChange} disabled={carregandoViagens}>
                <option value="">{carregandoViagens ? "Carregando..." : "Selecione uma viagem"}</option>
                {viagens.map(viagem => (
                  <option key={viagem.id} value={viagem.id}>
                    #{viagem.id} | {viagem.data} | {viagem.origem} x {viagem.destino} | R$ {Number(viagem.valor_total).toFixed(2)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Média da viagem (km/l)
              <small>Consumo médio do veículo nesta viagem.</small>
              <input type="number" min="0.01" step="0.01" name="media_km_por_litro" value={formData.media_km_por_litro} onChange={handleChange} />
            </label>

            <label>
              Valor do combustível
              <small>Preço por litro utilizado na viagem.</small>
              <input type="number" min="0.01" step="0.01" name="preco_combustivel" value={formData.preco_combustivel} onChange={handleChange} />
            </label>
          </div>

          {viagemSelecionada ? (
            <div className="avaliador-trip-summary">
              <span>Cliente: {viagemSelecionada.cliente}</span>
              <span>Peso: {formatarNumero(viagemSelecionada.peso)} t</span>
              <span>Faturamento: {formatarMoeda(viagemSelecionada.valor_total)}</span>
            </div>
          ) : null}

          <div className="avaliador-location-head">
            <h3>Local de carga e descarga</h3>
            <button type="button" className="avaliador-link-button" onClick={() => setAjusteManual(prev => !prev)}>
              {ajusteManual ? "Ocultar ajuste manual" : "Ajustar cidades"}
            </button>
          </div>

          {ajusteManual ? (
            <div className="avaliador-grid">
              <label>
                Cidade de origem
                <small>Use este campo se a cidade lançada não for reconhecida automaticamente.</small>
                <div className="avaliador-autocomplete">
                  <input name="cidade_origem" value={formData.cidade_origem} onChange={handleChange} autoComplete="off" />
                  {municipiosOrigem.length ? (
                    <div className="avaliador-autocomplete-list">
                      {municipiosOrigem.map(municipio => (
                        <button type="button" key={`origem-${municipio.id}`} className="avaliador-autocomplete-item" onClick={() => selecionarMunicipio("origem", municipio)}>
                          {municipio.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </label>
              <label>
                UF origem
                <small>Estado da cidade de carga.</small>
                <select name="estado_origem" value={formData.estado_origem} onChange={handleChange}>
                  {ESTADOS.map(estado => <option key={`uf-origem-${estado || "vazio"}`} value={estado}>{estado || "Selecione"}</option>)}
                </select>
              </label>
              <label>
                Cidade de destino
                <small>Use este campo se a cidade lançada não for reconhecida automaticamente.</small>
                <div className="avaliador-autocomplete">
                  <input name="cidade_destino" value={formData.cidade_destino} onChange={handleChange} autoComplete="off" />
                  {municipiosDestino.length ? (
                    <div className="avaliador-autocomplete-list">
                      {municipiosDestino.map(municipio => (
                        <button type="button" key={`destino-${municipio.id}`} className="avaliador-autocomplete-item" onClick={() => selecionarMunicipio("destino", municipio)}>
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
                  {ESTADOS.map(estado => <option key={`uf-destino-${estado || "vazio"}`} value={estado}>{estado || "Selecione"}</option>)}
                </select>
              </label>
            </div>
          ) : (
            <div className="avaliador-hint">
              <span>As cidades da viagem foram casadas automaticamente com a base local de municípios.</span>
            </div>
          )}

          {erro ? <div className="avaliador-alert erro">{erro}</div> : null}

          <div className="avaliador-actions">
            <button type="submit" className="avaliador-button" disabled={loading || !formData.viagem_id}>
              {loading ? "Calculando..." : "Avaliar Viagem"}
            </button>
          </div>
        </form>

        <div className="avaliador-card">
          <div className="avaliador-card-header">
            <h2>Resultado</h2>
            <span>Lucro remanescente após comissão e combustível.</span>
          </div>

          {resultado ? (
            <>
              <div className="avaliador-highlights">
                <article><span>Faturamento</span><strong>{formatarMoeda(resultado.viagem.faturamento_total)}</strong></article>
                <article><span>Comissão 13%</span><strong>{formatarMoeda(resultado.motorista.comissao_valor)}</strong></article>
                <article><span>Custo combustível</span><strong>{formatarMoeda(resultado.custos.custo_combustivel)}</strong></article>
                <article><span>Lucro remanescente</span><strong>{formatarMoeda(resultado.resultado.lucro_liquido)}</strong></article>
              </div>

              <div className="avaliador-detail-grid">
                <section>
                  <h3>Rota</h3>
                  <dl>
                    <div><dt>Origem</dt><dd>{resultado.origem.cidade}{resultado.origem.estado ? ` - ${resultado.origem.estado}` : ""}</dd></div>
                    <div><dt>Destino</dt><dd>{resultado.destino.cidade}{resultado.destino.estado ? ` - ${resultado.destino.estado}` : ""}</dd></div>
                    <div><dt>Distância</dt><dd>{formatarNumero(resultado.rota.distancia_km)} km</dd></div>
                    <div><dt>Tempo estimado</dt><dd>{resultado.rota.duracao_formatada}</dd></div>
                  </dl>
                </section>

                <section>
                  <h3>Combustível e lucro</h3>
                  <dl>
                    <div><dt>Média</dt><dd>{formatarNumero(resultado.custos.media_km_por_litro)} km/l</dd></div>
                    <div><dt>Litros estimados</dt><dd>{formatarNumero(resultado.custos.litros_estimados)} l</dd></div>
                    <div><dt>Preço do combustível</dt><dd>{formatarMoeda(resultado.custos.preco_combustivel)}</dd></div>
                    <div><dt>Margem restante</dt><dd>{formatarNumero(resultado.resultado.margem_percentual)}%</dd></div>
                  </dl>
                </section>
              </div>
            </>
          ) : (
            <div className="avaliador-empty-state">
              <p>Selecione uma viagem e informe os dados de consumo para ver o lucro remanescente.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default AvaliadorViagens;
