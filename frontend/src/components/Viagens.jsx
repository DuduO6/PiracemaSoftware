import React, { useEffect, useState } from "react";
import api from "../api/api";
import PaginationControls from "./PaginationControls.jsx";
import "../styles/viagens.css";

const ITENS_POR_PAGINA = 12;
const VALOR_POR_TONELADA = "valor_tonelada";
const VALOR_TOTAL_FRETE = "valor_total_informado";

const normalizarEntradaDecimal = (valor) => {
  if (typeof valor !== "string") return valor;

  const limpo = valor.replace(/[^0-9.,]/g, "");
  const separadorIndex = Math.max(limpo.indexOf(","), limpo.indexOf("."));

  if (separadorIndex === -1) return limpo;

  const parteInteira = limpo.slice(0, separadorIndex).replace(/[.,]/g, "");
  const parteDecimal = limpo.slice(separadorIndex + 1).replace(/[.,]/g, "");
  return `${parteInteira}${limpo[separadorIndex]}${parteDecimal}`;
};

const parseDecimalInput = (valor) => {
  if (valor === "" || valor === null || valor === undefined) return NaN;
  return Number(String(valor).replace(",", "."));
};

const normalizarPayloadDecimal = (valor) => {
  if (valor === "" || valor === null || valor === undefined) return valor;
  return String(valor).replace(",", ".");
};

const formatarCampoCalculado = (valor) => {
  if (valor === "" || valor === null || valor === undefined) return "";
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero.toFixed(2) : "";
};

const Viagens = () => {
  const [viagens, setViagens] = useState([]);
  const [motoristas, setMotoristas] = useState([]);
  const [ultimoAcertoGeral, setUltimoAcertoGeral] = useState(null);
  const [resumoAcertoMotorista, setResumoAcertoMotorista] = useState(null);
  const [resumoAcertoDisponivel, setResumoAcertoDisponivel] = useState(true);

  // Modal de adicionar/editar viagem
  const [showModalViagem, setShowModalViagem] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [viagemData, setViagemData] = useState({
    id: null,
    motorista: "",
    origem: "",
    destino: "",
    cliente: "",
    peso: "",
    valor_tonelada: "",
    valor_total_informado: "",
    modo_valor: "",
    data: "",
    pago: false,
  });

  const [showFiltro, setShowFiltro] = useState(false);
  const [filtro, setFiltro] = useState({
    motorista: "",
    cliente: "",
    localidade: "",
    pago: "",
    inicio: "",
    fim: ""
  });

  const [showAcertoModal, setShowAcertoModal] = useState(false);
  const [acertoData, setAcertoData] = useState({
    motorista: "",
    inicio: "",
    fim: "",
    salvar: false
  });
  const [paginaAtual, setPaginaAtual] = useState(1);

  // Carregar motoristas
  useEffect(() => {
    api.get("/api/motoristas/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || Object.values(res.data);
        setMotoristas(data);
      })
      .catch((err) => console.error("Erro ao carregar motoristas:", err));
  }, []);

  useEffect(() => {
    if (!resumoAcertoDisponivel) return;

    api.get("/api/viagens/resumo_acerto/")
      .then((res) => {
        setUltimoAcertoGeral(res.data && Object.keys(res.data).length ? res.data : null);
      })
      .catch((err) => {
        if (err.response?.status === 404) {
          setResumoAcertoDisponivel(false);
          setUltimoAcertoGeral(null);
          return;
        }
        console.error("Erro ao carregar resumo do último acerto:", err);
        setUltimoAcertoGeral(null);
      });
  }, [resumoAcertoDisponivel]);

  // Carregar viagens
  useEffect(() => {
    api.get("/api/viagens/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || Object.values(res.data);
        setViagens(data);
      })
      .catch((err) => console.error("Erro ao carregar viagens:", err));
  }, []);

  // Geração de acerto (PDF)
  const gerarAcerto = async (motoristaId, inicio, fim, salvar = false) => {
    try {
      const res = await api.get("/api/viagens/gerar_acerto/", {
        params: { 
          motorista_id: motoristaId, 
          inicio, 
          fim,
          salvar: salvar ? "true" : "false"
        },
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `Acerto_${motoristaId}.pdf`;

      // 🔥 ESSENCIAL PARA O ELECTRON
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      window.URL.revokeObjectURL(url);

      if (salvar) {
        alert("Acerto salvo no histórico com sucesso!");
      }
    } catch (err) {
      console.error("Erro ao gerar PDF:", err);
      if (err.response?.data instanceof Blob) {
        try {
          const texto = await err.response.data.text();
          const json = JSON.parse(texto);
          alert(json.detail || "Erro ao gerar o PDF");
          return;
        } catch (_parseErr) {
          // fallback abaixo
        }
      }
      alert(err.response?.data?.detail || "Erro ao gerar o PDF");
    }
  };


  const formatarDataBR = (dataISO) => {
    if (!dataISO) return "";
    const data = new Date(dataISO + "T00:00:00"); // evita bug de timezone
    return data.toLocaleDateString("pt-BR");
  };

  const formatarDataHoraBR = (dataISO) => {
    if (!dataISO) return "";
    const data = new Date(dataISO);
    return data.toLocaleString("pt-BR");
  };

  const carregarResumoAcertoMotorista = async (motoristaId) => {
    if (!resumoAcertoDisponivel || !motoristaId) {
      setResumoAcertoMotorista(null);
      return;
    }

    try {
      const res = await api.get("/api/viagens/resumo_acerto/", {
        params: { motorista_id: motoristaId }
      });
      const resumo = res.data && Object.keys(res.data).length ? res.data : null;
      setResumoAcertoMotorista(resumo);

      if (resumo?.inicio_sugerido) {
        setAcertoData((prev) => ({
          ...prev,
          inicio: resumo.inicio_sugerido,
        }));
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setResumoAcertoDisponivel(false);
        setResumoAcertoMotorista(null);
        return;
      }
      console.error("Erro ao carregar resumo de acerto do motorista:", err);
      setResumoAcertoMotorista(null);
    }
  };


  // Handlers do modal
  const handleViagemInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setViagemData((prev) => {
      if (type === "checkbox") {
        return {
          ...prev,
          [name]: checked,
        };
      }

      const valorTratado = ["peso", VALOR_POR_TONELADA, VALOR_TOTAL_FRETE].includes(name)
        ? normalizarEntradaDecimal(value)
        : value;

      if (name === VALOR_POR_TONELADA) {
        return {
          ...prev,
          valor_tonelada: valorTratado,
          valor_total_informado: "",
          modo_valor: valorTratado ? VALOR_POR_TONELADA : "",
        };
      }

      if (name === VALOR_TOTAL_FRETE) {
        return {
          ...prev,
          valor_total_informado: valorTratado,
          valor_tonelada: "",
          modo_valor: valorTratado ? VALOR_TOTAL_FRETE : "",
        };
      }

      return {
        ...prev,
        [name]: valorTratado,
      };
    });
  };

  const handleModoValorFocus = (campo) => {
    setViagemData((prev) => {
      if (campo === VALOR_POR_TONELADA && prev.valor_total_informado) {
        return {
          ...prev,
          valor_total_informado: "",
          modo_valor: "",
        };
      }

      if (campo === VALOR_TOTAL_FRETE && prev.valor_tonelada) {
        return {
          ...prev,
          valor_tonelada: "",
          modo_valor: "",
        };
      }

      return prev;
    });
  };

  const modoValorAtual = viagemData.modo_valor;

  const valorToneladaCalculado = (() => {
    const peso = parseDecimalInput(viagemData.peso);
    const valorTotal = parseDecimalInput(viagemData.valor_total_informado);

    if (modoValorAtual !== VALOR_TOTAL_FRETE || !peso || !valorTotal) return "";
    return formatarCampoCalculado(valorTotal / peso);
  })();

  const valorTotalCalculado = (() => {
    const peso = parseDecimalInput(viagemData.peso);
    const valorTonelada = parseDecimalInput(viagemData.valor_tonelada);

    if (modoValorAtual !== VALOR_POR_TONELADA || !peso || !valorTonelada) return "";
    return formatarCampoCalculado(peso * valorTonelada);
  })();

  const valorToneladaExibido = modoValorAtual === VALOR_TOTAL_FRETE
    ? valorToneladaCalculado
    : viagemData.valor_tonelada;

  const valorTotalExibido = modoValorAtual === VALOR_POR_TONELADA
    ? valorTotalCalculado
    : viagemData.valor_total_informado;

  const handleRemoverViagem = (id) => {
    if (!window.confirm("Tem certeza que deseja remover esta viagem?")) return;

    api.delete(`/api/viagens/${id}/`)
      .then(() => {
        setViagens((prev) => prev.filter(v => v.id !== id));
      })
      .catch((err) => console.error("Erro ao remover viagem:", err));
  }

  const handleAdicionarViagem = () => {
    const temValorTonelada = modoValorAtual === VALOR_POR_TONELADA && Boolean(viagemData.valor_tonelada);
    const temValorTotal = modoValorAtual === VALOR_TOTAL_FRETE && Boolean(viagemData.valor_total_informado);

    if (!viagemData.motorista || !viagemData.origem || !viagemData.destino || !viagemData.cliente || !viagemData.peso || !viagemData.data) {
      alert("Preencha todos os campos obrigatórios!");
      return;
    }

    if (!temValorTonelada && !temValorTotal) {
      alert("Informe o valor por tonelada ou o valor total do frete.");
      return;
    }

    if (temValorTonelada && temValorTotal) {
      alert("Informe apenas um dos campos: valor por tonelada ou valor total do frete.");
      return;
    }

    const payload = {
      ...viagemData,
      motorista: Number(viagemData.motorista),
      peso: normalizarPayloadDecimal(viagemData.peso),
    };

    delete payload.modo_valor;

    if (modoValorAtual === VALOR_POR_TONELADA) {
      payload.valor_tonelada = normalizarPayloadDecimal(viagemData.valor_tonelada);
      delete payload.valor_total_informado;
    } else if (modoValorAtual === VALOR_TOTAL_FRETE) {
      payload.valor_total_informado = normalizarPayloadDecimal(viagemData.valor_total_informado);
      delete payload.valor_tonelada;
    }

    if (modoEdicao && viagemData.id) {
      // Editar viagem existente
      api.put(`/api/viagens/${viagemData.id}/`, payload)
        .then((res) => {
          setViagens((prev) => prev.map(v => v.id === viagemData.id ? res.data : v));
          fecharModal();
        })
        .catch((err) => {
          console.error("Erro ao editar viagem:", err);
          alert(err.response?.data?.detail || JSON.stringify(err.response?.data) || "Erro ao editar viagem.");
        });
    } else {
      // Adicionar nova viagem
      api.post("/api/viagens/", payload)
        .then((res) => {
          setViagens((prev) => [...prev, res.data]);
          fecharModal();
        })
        .catch((err) => {
          console.error("Erro ao adicionar viagem:", err);
          alert(err.response?.data?.detail || JSON.stringify(err.response?.data) || "Erro ao adicionar viagem.");
        });
    }
  };

  const handleEditarViagem = (viagem) => {
    setModoEdicao(true);
    setViagemData({
      id: viagem.id,
      motorista: viagem.motorista,
      origem: viagem.origem,
      destino: viagem.destino,
      cliente: viagem.cliente,
      peso: viagem.peso,
      valor_tonelada: viagem.valor_tonelada,
      valor_total_informado: "",
      modo_valor: VALOR_POR_TONELADA,
      data: viagem.data,
      pago: viagem.pago,
    });
    setShowModalViagem(true);
  };

  const abrirModalNovo = () => {
    setModoEdicao(false);
    setViagemData({
      id: null,
      motorista: "",
      origem: "",
      destino: "",
      cliente: "",
      peso: "",
      valor_tonelada: "",
      valor_total_informado: "",
      modo_valor: "",
      data: "",
      pago: false,
    });
    setShowModalViagem(true);
  };

  const fecharModal = () => {
    setShowModalViagem(false);
    setModoEdicao(false);
    setViagemData({
      id: null,
      motorista: "",
      origem: "",
      destino: "",
      cliente: "",
      peso: "",
      valor_tonelada: "",
      valor_total_informado: "",
      modo_valor: "",
      data: "",
      pago: false,
    });
  };

  // Aplicar filtros
  const aplicarFiltro = () => {
    setShowFiltro(false);
  };

  const limparFiltros = () => {
    setFiltro({
      motorista: "",
      cliente: "",
      localidade: "",
      pago: "",
      inicio: "",
      fim: ""
    });
  };

  useEffect(() => {
    setPaginaAtual(1);
  }, [filtro.motorista, filtro.cliente, filtro.localidade, filtro.pago, filtro.inicio, filtro.fim]);

  // Filtrar viagens em tempo real
  const viagensFiltradas = viagens
  .filter(v => {
    if (filtro.motorista && String(v.motorista) !== String(filtro.motorista)) return false;
    if (filtro.cliente && !v.cliente.toLowerCase().includes(filtro.cliente.toLowerCase())) return false;
    if (
      filtro.localidade &&
      !v.origem.toLowerCase().includes(filtro.localidade.toLowerCase()) &&
      !v.destino.toLowerCase().includes(filtro.localidade.toLowerCase())
    ) return false;
    if (filtro.pago === "nao_pago" && v.pago === true) return false;
    if (filtro.inicio && new Date(v.data) < new Date(filtro.inicio)) return false;
    if (filtro.fim && new Date(v.data) > new Date(filtro.fim)) return false;
    return true;
  })
  .sort((a, b) => new Date(b.data) - new Date(a.data)); // 🔥 MAIS RECENTE PRIMEIRO


  const valorTotalFiltrado = viagensFiltradas.reduce((acc, v) => acc + Number(v.valor_total || 0), 0);
  const temFiltroAtivo = filtro.motorista || filtro.cliente || filtro.localidade || filtro.pago || filtro.inicio || filtro.fim;
  const totalPaginas = Math.max(1, Math.ceil(viagensFiltradas.length / ITENS_POR_PAGINA));

  useEffect(() => {
    if (paginaAtual > totalPaginas) {
      setPaginaAtual(totalPaginas);
    }
  }, [paginaAtual, totalPaginas]);

  const viagensPaginadas = viagensFiltradas.slice(
    (paginaAtual - 1) * ITENS_POR_PAGINA,
    paginaAtual * ITENS_POR_PAGINA
  );

  return (
    <div className="viagens-container">
      <h1 className="titulo">VIAGENS</h1>

      <div className="btn-row">
        <button className="white-btn" onClick={abrirModalNovo}>
          NOVA VIAGEM
        </button>
        <button className="white-btn" onClick={() => setShowFiltro(true)}>
          FILTRAR
        </button>
        <button className="white-btn" onClick={() => setShowAcertoModal(true)}>
          GERAR ACERTO
        </button>
      </div>

      <div className="info-viagens">
        <p className="total-text">
          TOTAL DE VIAGENS: {viagensFiltradas.length}
        </p>
        <p className="total-valor">
          VALOR TOTAL: R$ {valorTotalFiltrado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
        </p>
      </div>

      {resumoAcertoDisponivel && ultimoAcertoGeral && (
        <div className="filtros-aplicados">
          <span className="filtro-badge">
            Último acerto: {ultimoAcertoGeral.motorista_nome}
          </span>
          <span className="filtro-badge">
            Gerado em: {formatarDataHoraBR(ultimoAcertoGeral.data_geracao)}
          </span>
          <span className="filtro-badge">
            Última viagem englobada: {formatarDataBR(ultimoAcertoGeral.data_ultima_viagem_englobada)}
          </span>
        </div>
      )}

      {temFiltroAtivo && (
        <div className="filtros-aplicados">
          {filtro.motorista && <span className="filtro-badge">Motorista: {motoristas.find(m => String(m.id) === String(filtro.motorista))?.nome}</span>}
          {filtro.cliente && <span className="filtro-badge">Cliente: {filtro.cliente}</span>}
          {filtro.localidade && <span className="filtro-badge">Localidade: {filtro.localidade}</span>}
          {filtro.pago && <span className="filtro-badge">Não pagos</span>}
          {filtro.inicio && <span className="filtro-badge">Desde: {filtro.inicio}</span>}
          {filtro.fim && <span className="filtro-badge">Até: {filtro.fim}</span>}
          <button className="filtro-badge filtro-limpar" onClick={limparFiltros}>✕ Limpar</button>
        </div>
      )}

      <div className="table-wrapper">
        <table className="viagens-table">
          <thead>
            <tr>
              <th>DATA</th>
              <th>ORIGEM</th>
              <th>DESTINO</th>
              <th>CLIENTE</th>
              <th>PESO(TN)</th>
              <th>VALOR P/TN</th>
              <th>VALOR</th>
              <th>PAGO</th>
              <th>MOTORISTA</th>
              <th>AÇÕES</th>
            </tr>
          </thead>
          <tbody>
            {viagensPaginadas.map(v => (
              <tr key={v.id}>
                <td>{formatarDataBR(v.data)}</td>
                <td>{v.origem}</td>
                <td>{v.destino}</td>
                <td>{v.cliente}</td>
                <td>{v.peso}</td>
                <td>R$ {Number(v.valor_tonelada).toFixed(2)}</td>
                <td>R$ {Number(v.valor_total).toFixed(2)}</td>
                <td>
                  <span className={`status-badge ${v.pago ? 'status-pago' : 'status-pendente'}`}>
                    {v.pago ? "PAGO" : "PENDENTE"}
                  </span>
                </td>
                <td>{motoristas.find(m => m.id === v.motorista)?.nome || "—"}</td>
                <td>
                  <div className="acoes-row">
                    <button
                      className="btn-remover"
                      onClick={() => handleRemoverViagem(v.id)}
                    >
                      REMOVER
                    </button>

                    <button
                      className="btn-editar"
                      onClick={() => handleEditarViagem(v)}
                    >
                      EDITAR
                    </button>
                  </div>
                </td>

              </tr>
            ))}
          </tbody>
        </table>
        <PaginationControls
          totalItems={viagensFiltradas.length}
          itemsPerPage={ITENS_POR_PAGINA}
          currentPage={paginaAtual}
          onPageChange={setPaginaAtual}
        />
      </div>

      {/* Modal Filtro */}
      {showFiltro && (
        <div className="modal-overlay" onClick={() => setShowFiltro(false)}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Filtrar Viagens</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                value={filtro.motorista}
                onChange={e => setFiltro({ ...filtro, motorista: e.target.value })}
              >
                <option value="">Todos</option>
                {motoristas.map(m => (
                  <option key={m.id} value={m.id}>{m.nome}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Cliente:</label>
              <input
                type="text"
                value={filtro.cliente}
                onChange={e => setFiltro({ ...filtro, cliente: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Localidade (Origem ou Destino):</label>
              <input
                type="text"
                value={filtro.localidade}
                onChange={e => setFiltro({ ...filtro, localidade: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Pagamento:</label>
              <select
                value={filtro.pago}
                onChange={e => setFiltro({ ...filtro, pago: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="nao_pago">Apenas Não Pagos</option>
              </select>
            </div>

            <div className="form-group">
              <label>Período:</label>
              <div className="date-range">
                <input
                  type="date"
                  value={filtro.inicio}
                  onChange={e => setFiltro({ ...filtro, inicio: e.target.value })}
                />
                <span>até</span>
                <input
                  type="date"
                  value={filtro.fim}
                  onChange={e => setFiltro({ ...filtro, fim: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={aplicarFiltro}>APLICAR</button>
              <button className="btn-cancelar" onClick={() => setShowFiltro(false)}>CANCELAR</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Viagem */}
      {showModalViagem && (
        <div className="modal-overlay" onClick={fecharModal}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>{modoEdicao ? "Editar Viagem" : "Nova Viagem"}</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                name="motorista"
                value={viagemData.motorista}
                onChange={handleViagemInputChange}
              >
                <option value="">Selecione</option>
                {motoristas.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Origem:</label>
              <input
                type="text"
                name="origem"
                value={viagemData.origem}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Destino:</label>
              <input
                type="text"
                name="destino"
                value={viagemData.destino}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Cliente:</label>
              <input
                type="text"
                name="cliente"
                value={viagemData.cliente}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Peso (TN):</label>
              <input
                type="text"
                inputMode="decimal"
                name="peso"
                value={viagemData.peso}
                onChange={handleViagemInputChange}
                placeholder="Ex.: 35,70"
              />
            </div>

            <div className="form-group">
              <label>Valor / TN:</label>
              <input
                type="text"
                inputMode="decimal"
                name="valor_tonelada"
                value={valorToneladaExibido}
                onChange={handleViagemInputChange}
                onFocus={() => handleModoValorFocus(VALOR_POR_TONELADA)}
                readOnly={modoValorAtual === VALOR_TOTAL_FRETE}
                className={modoValorAtual === VALOR_TOTAL_FRETE ? "input-bloqueado" : ""}
                placeholder="Ex.: 180,00"
              />
              <small className={`form-help-text ${modoValorAtual === VALOR_TOTAL_FRETE ? "bloqueado" : ""}`}>
                {modoValorAtual === VALOR_TOTAL_FRETE
                  ? "Campo bloqueado: valor calculado automaticamente a partir do valor total."
                  : "Digite aqui para calcular o valor total automaticamente."}
              </small>
            </div>

            <div className="form-group">
              <label>Valor Total do Frete:</label>
              <input
                type="text"
                inputMode="decimal"
                name="valor_total_informado"
                value={valorTotalExibido}
                onChange={handleViagemInputChange}
                onFocus={() => handleModoValorFocus(VALOR_TOTAL_FRETE)}
                readOnly={modoValorAtual === VALOR_POR_TONELADA}
                className={modoValorAtual === VALOR_POR_TONELADA ? "input-bloqueado" : ""}
                placeholder="Ex.: 6426,00"
              />
              <small className={`form-help-text ${modoValorAtual === VALOR_POR_TONELADA ? "bloqueado" : ""}`}>
                {modoValorAtual === VALOR_POR_TONELADA
                  ? "Campo bloqueado: valor calculado automaticamente a partir do valor por tonelada."
                  : "Digite aqui para calcular o valor por tonelada automaticamente."}
              </small>
            </div>

            <div className="form-group">
              <label>Data:</label>
              <input
                type="date"
                name="data"
                value={viagemData.data}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group-checkbox">
              <input
                type="checkbox"
                name="pago"
                id="pago"
                checked={viagemData.pago}
                onChange={handleViagemInputChange}
              />
              <label htmlFor="pago">Marcar como pago</label>
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={handleAdicionarViagem}>
                {modoEdicao ? "SALVAR" : "ADICIONAR"}
              </button>
              <button className="btn-cancelar" onClick={fecharModal}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Acerto */}
      {showAcertoModal && (
        <div
          className="modal-overlay"
          onClick={() => {
            setShowAcertoModal(false);
            setResumoAcertoMotorista(null);
          }}
        >
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Gerar Acerto</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                value={acertoData.motorista}
                onChange={async (e) => {
                  const motoristaSelecionado = e.target.value;
                  setAcertoData((prev) => ({ ...prev, motorista: motoristaSelecionado }));
                  await carregarResumoAcertoMotorista(motoristaSelecionado);
                }}
              >
                <option value="">Selecione</option>
                {motoristas.map(m => (
                  <option key={m.id} value={m.id}>{m.nome}</option>
                ))}
              </select>
            </div>

            {resumoAcertoDisponivel && resumoAcertoMotorista && (
              <div className="filtros-aplicados">
                <span className="filtro-badge">
                  Último acerto do motorista: {formatarDataHoraBR(resumoAcertoMotorista.data_geracao)}
                </span>
                <span className="filtro-badge">
                  Última viagem englobada: {formatarDataBR(resumoAcertoMotorista.data_ultima_viagem_englobada)}
                </span>
                <span className="filtro-badge">
                  Início sugerido: {formatarDataBR(resumoAcertoMotorista.inicio_sugerido)}
                </span>
              </div>
            )}

            <div className="form-group">
              <label>Período:</label>
              <div className="date-range">
                <input
                  type="date"
                  value={acertoData.inicio}
                  onChange={e => setAcertoData({ ...acertoData, inicio: e.target.value })}
                />
                <span>até</span>
                <input
                  type="date"
                  value={acertoData.fim}
                  onChange={e => setAcertoData({ ...acertoData, fim: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group-checkbox">
              <input
                type="checkbox"
                id="salvar-acerto"
                checked={acertoData.salvar}
                onChange={e => setAcertoData({ ...acertoData, salvar: e.target.checked })}
              />
              <label htmlFor="salvar-acerto">Salvar no histórico de acertos</label>
            </div>

            <div className="modal-buttons">
              <button
                className="btn-salvar"
                onClick={() => {
                  if (!acertoData.motorista || !acertoData.inicio || !acertoData.fim) {
                    alert("Selecione motorista e período!");
                    return;
                  }
                  gerarAcerto(acertoData.motorista, acertoData.inicio, acertoData.fim, acertoData.salvar);
                  setShowAcertoModal(false);
                  setAcertoData({ motorista: "", inicio: "", fim: "", salvar: false });
                  setResumoAcertoMotorista(null);
                }}
              >
                GERAR PDF
              </button>
              <button
                className="btn-cancelar"
                onClick={() => {
                  setShowAcertoModal(false);
                  setResumoAcertoMotorista(null);
                }}
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Viagens;
