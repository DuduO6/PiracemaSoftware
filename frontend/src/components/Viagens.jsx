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

const formatarMoeda = (valor) => `R$ ${Number(valor || 0).toLocaleString("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})}`;

const calcularDescontoCte = (viagem) => {
  if (!viagem?.teve_cte) return 0;
  return Number(viagem.valor_desconto_cte ?? (Number(viagem.peso || 0) * Number(viagem.valor_tonelada || 0) * 0.1));
};

const calcularValorBruto = (viagem) => {
  return Number(viagem.valor_bruto ?? (Number(viagem.peso || 0) * Number(viagem.valor_tonelada || 0)));
};

const getInitialViagemData = () => ({
  id: null,
  motorista: "",
  origem: "",
  destino: "",
  cliente: "",
  teve_cte: false,
  numero_cte: "",
  peso: "",
  valor_tonelada: "",
  valor_total_informado: "",
  modo_valor: "",
  data: "",
  pago: false,
});

const Viagens = () => {
  const [viagens, setViagens] = useState([]);
  const [motoristas, setMotoristas] = useState([]);
  const [ultimoAcertoGeral, setUltimoAcertoGeral] = useState(null);
  const [resumoAcertoMotorista, setResumoAcertoMotorista] = useState(null);
  const [resumoAcertoDisponivel, setResumoAcertoDisponivel] = useState(true);

  // Modal de adicionar/editar viagem
  const [showModalViagem, setShowModalViagem] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [viagemData, setViagemData] = useState(getInitialViagemData);
  const [observacoesImportacao, setObservacoesImportacao] = useState([]);
  const [importandoXml, setImportandoXml] = useState(false);
  const [showConfirmacaoModal, setShowConfirmacaoModal] = useState(false);
  const [showDuplicidadeModal, setShowDuplicidadeModal] = useState(false);
  const [payloadPendente, setPayloadPendente] = useState(null);
  const [alertaDuplicidade, setAlertaDuplicidade] = useState(null);

  const [showFiltro, setShowFiltro] = useState(false);
  const [filtro, setFiltro] = useState({
    motorista: "",
    cliente: "",
    localidade: "",
    teve_cte: "",
    pago: "",
    inicio: "",
    fim: ""
  });

  const [showAcertoModal, setShowAcertoModal] = useState(false);
  const [acertoData, setAcertoData] = useState({
    motorista: "",
    inicio: "",
    fim: "",
    salvar: false,
    descontar_vales: false,
  });
  const [valesAcerto, setValesAcerto] = useState([]);
  const [carregandoValesAcerto, setCarregandoValesAcerto] = useState(false);
  const [valesSelecionadosAcerto, setValesSelecionadosAcerto] = useState({});
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
  const gerarAcerto = async (motoristaId, inicio, fim, salvar = false, descontarVales = false, valesSelecionados = []) => {
    try {
      const res = await api.get("/api/viagens/gerar_acerto/", {
        params: { 
          motorista_id: motoristaId, 
          inicio, 
          fim,
          salvar: salvar ? "true" : "false",
          descontar_vales: descontarVales ? "true" : "false",
          vales: JSON.stringify(valesSelecionados),
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

  const carregarValesAcerto = async (motoristaId) => {
    if (!motoristaId) {
      setValesAcerto([]);
      setValesSelecionadosAcerto({});
      return;
    }

    setCarregandoValesAcerto(true);
    try {
      const res = await api.get("/api/vales/", {
        params: { motorista: motoristaId }
      });
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];
      setValesAcerto(data.filter((vale) => !vale.pago && Number(vale.valor || 0) > 0));
      setValesSelecionadosAcerto({});
    } catch (err) {
      console.error("Erro ao carregar vales para acerto:", err);
      setValesAcerto([]);
      setValesSelecionadosAcerto({});
    } finally {
      setCarregandoValesAcerto(false);
    }
  };

  const atualizarValeSelecionado = (vale, selecionado, valor = null) => {
    setValesSelecionadosAcerto((prev) => {
      const proximo = { ...prev };
      if (!selecionado) {
        delete proximo[vale.id];
        return proximo;
      }
      proximo[vale.id] = {
        id: vale.id,
        valor_desconto: valor ?? proximo[vale.id]?.valor_desconto ?? String(vale.valor),
      };
      return proximo;
    });
  };

  const montarValesSelecionadosAcerto = () => (
    Object.values(valesSelecionadosAcerto)
      .map((vale) => ({
        id: vale.id,
        valor_desconto: normalizarPayloadDecimal(vale.valor_desconto),
      }))
  );


  // Handlers do modal
  const handleViagemInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setViagemData((prev) => {
      if (type === "checkbox") {
        if (name === "teve_cte" && !checked) {
          return {
            ...prev,
            teve_cte: false,
            numero_cte: "",
          };
        }
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

  const importarXmlCte = async (arquivo) => {
    if (!arquivo) return;

    const formData = new FormData();
    formData.append("arquivo", arquivo);
    setImportandoXml(true);

    try {
      const res = await api.post("/api/viagens/importar_cte/", formData);
      const dados = res.data;

      setViagemData((prev) => ({
        ...prev,
        motorista: dados.motorista ? String(dados.motorista) : "",
        origem: dados.origem || "",
        destino: dados.destino || "",
        cliente: dados.cliente || "",
        teve_cte: Boolean(dados.teve_cte),
        numero_cte: dados.numero_cte || "",
        peso: dados.peso || "",
        valor_tonelada: "",
        valor_total_informado: dados.valor_total_informado || "",
        modo_valor: dados.valor_total_informado ? VALOR_TOTAL_FRETE : "",
        data: dados.data || "",
        pago: false,
      }));
      setObservacoesImportacao(Array.isArray(dados.observacoes) ? dados.observacoes : []);
    } catch (err) {
      console.error("Erro ao importar XML do CT-e:", err);
      alert(err.response?.data?.detail || "Erro ao importar XML do CT-e.");
    } finally {
      setImportandoXml(false);
    }
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

  const previewValorBruto = parseDecimalInput(valorTotalExibido);
  const previewDescontoCte = viagemData.teve_cte && Number.isFinite(previewValorBruto)
    ? previewValorBruto * 0.1
    : 0;
  const previewValorLiquido = Number.isFinite(previewValorBruto)
    ? previewValorBruto - previewDescontoCte
    : 0;

  const handleRemoverViagem = (id) => {
    if (!window.confirm("Tem certeza que deseja remover esta viagem?")) return;

    api.delete(`/api/viagens/${id}/`)
      .then(() => {
        setViagens((prev) => prev.filter(v => v.id !== id));
      })
      .catch((err) => console.error("Erro ao remover viagem:", err));
  }

  const prepararSalvarViagem = async () => {
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

    if (viagemData.teve_cte && !viagemData.numero_cte) {
      alert("Informe o número do CT-e.");
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

    try {
      const res = await api.post("/api/viagens/verificar_duplicidade/", payload);
      const duplicidade = res.data?.duplicada ? res.data : null;
      setAlertaDuplicidade(duplicidade);
      setPayloadPendente(payload);

      if (duplicidade) {
        setShowDuplicidadeModal(true);
        return;
      }
    } catch (err) {
      console.error("Erro ao verificar duplicidade:", err);
      setAlertaDuplicidade(null);
    }

    setShowConfirmacaoModal(true);
  };

  const confirmarSalvarViagem = () => {
    if (!payloadPendente) return;

    if (modoEdicao && viagemData.id) {
      api.put(`/api/viagens/${viagemData.id}/`, payloadPendente)
        .then((res) => {
          setViagens((prev) => prev.map(v => v.id === viagemData.id ? res.data : v));
          fecharModal();
        })
        .catch((err) => {
          console.error("Erro ao editar viagem:", err);
          alert(err.response?.data?.detail || JSON.stringify(err.response?.data) || "Erro ao editar viagem.");
        });
    } else {
      api.post("/api/viagens/", payloadPendente)
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
      teve_cte: Boolean(viagem.teve_cte),
      numero_cte: viagem.numero_cte || "",
      peso: viagem.peso,
      valor_tonelada: viagem.valor_tonelada,
      valor_total_informado: "",
      modo_valor: VALOR_POR_TONELADA,
      data: viagem.data,
      pago: viagem.pago,
    });
    setObservacoesImportacao([]);
    setShowModalViagem(true);
  };

  const abrirModalNovo = () => {
    setModoEdicao(false);
    setViagemData(getInitialViagemData());
    setObservacoesImportacao([]);
    setShowModalViagem(true);
  };

  const fecharModal = () => {
    setShowModalViagem(false);
    setModoEdicao(false);
    setShowDuplicidadeModal(false);
    setShowConfirmacaoModal(false);
    setPayloadPendente(null);
    setObservacoesImportacao([]);
    setAlertaDuplicidade(null);
    setViagemData(getInitialViagemData());
  };

  const abrirConfirmacaoAposDuplicidade = () => {
    setShowDuplicidadeModal(false);
    setShowConfirmacaoModal(true);
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
      teve_cte: "",
      pago: "",
      inicio: "",
      fim: ""
    });
  };

  useEffect(() => {
    setPaginaAtual(1);
  }, [filtro.motorista, filtro.cliente, filtro.localidade, filtro.teve_cte, filtro.pago, filtro.inicio, filtro.fim]);

  const exportarPlanilha = async () => {
    try {
      const res = await api.get("/api/viagens/exportar_planilha/", {
        params: filtro,
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "viagens_filtradas.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Erro ao exportar planilha de viagens:", err);
      alert("Erro ao exportar planilha de viagens.");
    }
  };

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
    if (filtro.teve_cte === "com_cte" && !v.teve_cte) return false;
    if (filtro.teve_cte === "sem_cte" && v.teve_cte) return false;
    if (filtro.pago === "nao_pago" && v.pago === true) return false;
    if (filtro.pago === "pago" && v.pago === false) return false;
    if (filtro.inicio && new Date(v.data) < new Date(filtro.inicio)) return false;
    if (filtro.fim && new Date(v.data) > new Date(filtro.fim)) return false;
    return true;
  })
  .sort((a, b) => new Date(b.data) - new Date(a.data)); // 🔥 MAIS RECENTE PRIMEIRO


  const valorTotalFiltrado = viagensFiltradas.reduce((acc, v) => acc + Number(v.valor_total || 0), 0);
  const descontoCteFiltrado = viagensFiltradas.reduce((acc, v) => acc + calcularDescontoCte(v), 0);
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
        <button className="white-btn" onClick={exportarPlanilha}>
          EXPORTAR PLANILHA
        </button>
      </div>

      <div className="info-viagens">
        <p className="total-text">
          TOTAL DE VIAGENS: {viagensFiltradas.length}
        </p>
        <p className="total-valor">
          VALOR TOTAL LÍQUIDO: {formatarMoeda(valorTotalFiltrado)}
        </p>
        <p className="total-desconto-cte">
          DESCONTO CT-e: - {formatarMoeda(descontoCteFiltrado)}
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
          {filtro.teve_cte === "com_cte" && <span className="filtro-badge">Apenas com CT-e</span>}
          {filtro.teve_cte === "sem_cte" && <span className="filtro-badge">Apenas sem CT-e</span>}
          {filtro.pago === "nao_pago" && <span className="filtro-badge">Não pagos</span>}
          {filtro.pago === "pago" && <span className="filtro-badge">Pagos</span>}
          {filtro.inicio && <span className="filtro-badge">Desde: {filtro.inicio}</span>}
          {filtro.fim && <span className="filtro-badge">Até: {filtro.fim}</span>}
          <button className="filtro-badge filtro-limpar" onClick={limparFiltros}>✕ Limpar</button>
        </div>
      )}

      <div className="table-section">
        <div className="table-wrapper">
          <table className="viagens-table">
            <thead>
              <tr>
                <th>DATA</th>
                <th>ORIGEM</th>
                <th>DESTINO</th>
                <th>CLIENTE</th>
                <th>PESO</th>
                <th>R$/TN</th>
              <th>BRUTO</th>
              <th>DESC. CT-E</th>
              <th>LÍQUIDO</th>
              <th>CT-E</th>
                <th>PAGO</th>
                <th>MOTORISTA</th>
                <th>AÇÕES</th>
              </tr>
            </thead>
            <tbody>
              {viagensPaginadas.map(v => (
                <tr key={v.id}>
                  <td className="nowrap-cell">{formatarDataBR(v.data)}</td>
                  <td>{v.origem}</td>
                  <td>{v.destino}</td>
                  <td>{v.cliente}</td>
                  <td className="numeric-cell">{v.peso}</td>
                  <td className="numeric-cell">R$ {Number(v.valor_tonelada).toFixed(2)}</td>
                  <td className="numeric-cell">R$ {calcularValorBruto(v).toFixed(2)}</td>
                  <td className={`numeric-cell ${v.teve_cte ? "valor-desconto-cte" : ""}`}>
                    {v.teve_cte ? `- R$ ${calcularDescontoCte(v).toFixed(2)}` : "R$ 0.00"}
                  </td>
                  <td className="numeric-cell">R$ {Number(v.valor_total).toFixed(2)}</td>
                  <td className="nowrap-cell">{v.teve_cte ? `Sim${v.numero_cte ? ` - ${v.numero_cte}` : ""}` : "Não"}</td>
                  <td className="status-cell">
                    <span className={`status-badge ${v.pago ? 'status-pago' : 'status-pendente'}`}>
                      {v.pago ? "PAGO" : "PENDENTE"}
                    </span>
                  </td>
                  <td>{motoristas.find(m => m.id === v.motorista)?.nome || "—"}</td>
                  <td className="actions-cell">
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
        </div>
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
              <label>CT-e:</label>
              <select
                value={filtro.teve_cte}
                onChange={e => setFiltro({ ...filtro, teve_cte: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="com_cte">Apenas com CT-e</option>
                <option value="sem_cte">Apenas sem CT-e</option>
              </select>
            </div>

            <div className="form-group">
              <label>Pagamento:</label>
              <select
                value={filtro.pago}
                onChange={e => setFiltro({ ...filtro, pago: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="pago">Apenas Pagos</option>
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

            {!modoEdicao && (
              <div className="importacao-cte-box">
                <label className="importacao-cte-label" htmlFor="arquivo-cte">
                  Importar XML do CT-e
                </label>
                <input
                  id="arquivo-cte"
                  type="file"
                  accept=".xml,text/xml,application/xml"
                  onChange={(e) => {
                    const arquivo = e.target.files?.[0];
                    importarXmlCte(arquivo);
                    e.target.value = "";
                  }}
                />
                <small className="form-help-text">
                  {importandoXml
                    ? "Lendo XML e preenchendo os campos..."
                    : "Use o XML para preencher motorista, data, origem, destino, cliente, peso, CT-e e frete."}
                </small>
              </div>
            )}

            {observacoesImportacao.length > 0 && (
              <div className="importacao-cte-alerta">
                {observacoesImportacao.map((observacao) => (
                  <p key={observacao}>{observacao}</p>
                ))}
              </div>
            )}

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

            <div className="form-group-checkbox">
              <input
                type="checkbox"
                name="teve_cte"
                id="teve_cte"
                checked={viagemData.teve_cte}
                onChange={handleViagemInputChange}
              />
              <label htmlFor="teve_cte">Viagem com CT-e</label>
            </div>

            <div className="form-group">
              <label>Número do CT-e:</label>
              <input
                type="text"
                name="numero_cte"
                value={viagemData.numero_cte}
                onChange={handleViagemInputChange}
                disabled={!viagemData.teve_cte}
                className={!viagemData.teve_cte ? "input-bloqueado" : ""}
                placeholder="Ex.: 266"
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

            {Number.isFinite(previewValorBruto) && previewValorBruto > 0 && (
              <div className="cte-preview-box">
                <div>
                  <span>Valor bruto da viagem</span>
                  <strong>{formatarMoeda(previewValorBruto)}</strong>
                </div>
                <div className={viagemData.teve_cte ? "cte-preview-desconto" : ""}>
                  <span>Desconto CT-e (10%)</span>
                  <strong>{viagemData.teve_cte ? `- ${formatarMoeda(previewDescontoCte)}` : formatarMoeda(0)}</strong>
                </div>
                <div className="cte-preview-liquido">
                  <span>Valor líquido lançado</span>
                  <strong>{formatarMoeda(previewValorLiquido)}</strong>
                </div>
              </div>
            )}

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
              <button className="btn-salvar" onClick={prepararSalvarViagem}>
                {modoEdicao ? "SALVAR" : "ADICIONAR"}
              </button>
              <button className="btn-cancelar" onClick={fecharModal}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      {showDuplicidadeModal && alertaDuplicidade && payloadPendente && (
        <div
          className="modal-overlay"
          onClick={() => {
            setShowDuplicidadeModal(false);
            setPayloadPendente(null);
            setAlertaDuplicidade(null);
          }}
        >
          <div className="modal-edicao modal-alerta" onClick={(e) => e.stopPropagation()}>
            <h2>Possível Duplicidade</h2>
            <div className="importacao-cte-alerta importacao-cte-alerta-erro sem-margem">
              <p>{alertaDuplicidade.detail}</p>
              <p>
                Viagem encontrada: #{alertaDuplicidade.viagem_id}
              </p>
              <p>
                {formatarDataBR(alertaDuplicidade.data)} | {alertaDuplicidade.origem} → {alertaDuplicidade.destino}
              </p>
              <p>
                Cliente: {alertaDuplicidade.cliente}
              </p>
            </div>

            <p className="confirmacao-texto">
              Deseja continuar mesmo assim e revisar a prévia antes de salvar?
            </p>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={abrirConfirmacaoAposDuplicidade}>
                CONTINUAR
              </button>
              <button
                className="btn-cancelar"
                onClick={() => {
                  setShowDuplicidadeModal(false);
                  setPayloadPendente(null);
                  setAlertaDuplicidade(null);
                }}
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      {showConfirmacaoModal && payloadPendente && (
        <div
          className="modal-overlay"
          onClick={() => {
            setShowConfirmacaoModal(false);
            setPayloadPendente(null);
            setAlertaDuplicidade(null);
          }}
        >
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Confirmar Viagem</h2>
            <div className="preview-grid">
              <div><strong>Motorista:</strong> {motoristas.find((m) => m.id === Number(payloadPendente.motorista))?.nome || "—"}</div>
              <div><strong>Data:</strong> {formatarDataBR(payloadPendente.data)}</div>
              <div><strong>Origem:</strong> {payloadPendente.origem}</div>
              <div><strong>Destino:</strong> {payloadPendente.destino}</div>
              <div><strong>Cliente:</strong> {payloadPendente.cliente}</div>
              <div><strong>Peso:</strong> {Number(payloadPendente.peso).toFixed(2)} TN</div>
              <div><strong>Valor / TN:</strong> {formatarMoeda(modoValorAtual === VALOR_TOTAL_FRETE ? valorToneladaCalculado : payloadPendente.valor_tonelada)}</div>
              <div><strong>Valor bruto:</strong> {formatarMoeda(modoValorAtual === VALOR_POR_TONELADA ? valorTotalCalculado : payloadPendente.valor_total_informado)}</div>
              <div><strong>Desconto CT-e:</strong> {payloadPendente.teve_cte ? `- ${formatarMoeda(previewDescontoCte)}` : formatarMoeda(0)}</div>
              <div><strong>Valor líquido:</strong> {formatarMoeda(previewValorLiquido)}</div>
              <div><strong>CT-e:</strong> {payloadPendente.teve_cte ? `Sim - ${payloadPendente.numero_cte}` : "Não"}</div>
              <div><strong>Pago:</strong> {payloadPendente.pago ? "Sim" : "Não"}</div>
            </div>

            {observacoesImportacao.length > 0 && (
              <div className="importacao-cte-alerta">
                {observacoesImportacao.map((observacao) => (
                  <p key={`confirmacao-${observacao}`}>{observacao}</p>
                ))}
              </div>
            )}

            {alertaDuplicidade && (
              <div className="importacao-cte-alerta importacao-cte-alerta-erro">
                <p>{alertaDuplicidade.detail}</p>
                <p>
                  Viagem encontrada: #{alertaDuplicidade.viagem_id} | {formatarDataBR(alertaDuplicidade.data)} | {alertaDuplicidade.origem} → {alertaDuplicidade.destino}
                </p>
              </div>
            )}

            <p className="confirmacao-texto">As informações acima estão corretas?</p>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={confirmarSalvarViagem}>
                CONFIRMAR E SALVAR
              </button>
              <button
                className="btn-cancelar"
                onClick={() => {
                  setShowConfirmacaoModal(false);
                  setPayloadPendente(null);
                  setAlertaDuplicidade(null);
                }}
              >
                VOLTAR
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
            setValesAcerto([]);
            setValesSelecionadosAcerto({});
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
                  setAcertoData((prev) => ({ ...prev, motorista: motoristaSelecionado, descontar_vales: false }));
                  await carregarResumoAcertoMotorista(motoristaSelecionado);
                  await carregarValesAcerto(motoristaSelecionado);
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

            <div className="form-group-checkbox">
              <input
                type="checkbox"
                id="descontar-vales"
                checked={acertoData.descontar_vales}
                disabled={!acertoData.motorista}
                onChange={e => setAcertoData({ ...acertoData, descontar_vales: e.target.checked })}
              />
              <label htmlFor="descontar-vales">Descontar vales neste acerto</label>
            </div>

            {acertoData.descontar_vales && (
              <div className="vales-acerto-box">
                <h3>Vales pendentes do motorista</h3>
                {carregandoValesAcerto ? (
                  <p className="form-help-text">Carregando vales...</p>
                ) : valesAcerto.length > 0 ? (
                  <div className="vales-acerto-list">
                    {valesAcerto.map((vale) => {
                      const selecionado = Boolean(valesSelecionadosAcerto[vale.id]);
                      const valorSelecionado = valesSelecionadosAcerto[vale.id]?.valor_desconto ?? String(vale.valor);
                      return (
                        <div className="vale-acerto-item" key={vale.id}>
                          <label className="vale-acerto-check">
                            <input
                              type="checkbox"
                              checked={selecionado}
                              onChange={(e) => atualizarValeSelecionado(vale, e.target.checked)}
                            />
                            <span>
                              {formatarDataBR(vale.data)} - Saldo: {formatarMoeda(vale.valor)}
                            </span>
                          </label>
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            max={vale.valor}
                            value={valorSelecionado}
                            disabled={!selecionado}
                            onChange={(e) => atualizarValeSelecionado(vale, true, e.target.value)}
                          />
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="form-help-text">Nenhum vale pendente para este motorista.</p>
                )}
              </div>
            )}

            <div className="modal-buttons">
              <button
                className="btn-salvar"
                onClick={() => {
                  if (!acertoData.motorista || !acertoData.inicio || !acertoData.fim) {
                    alert("Selecione motorista e período!");
                    return;
                  }
                  const valesSelecionados = acertoData.descontar_vales ? montarValesSelecionadosAcerto() : [];
                  if (acertoData.descontar_vales && valesSelecionados.length === 0) {
                    alert("Selecione ao menos um vale para desconto.");
                    return;
                  }
                  for (const valeSelecionado of valesSelecionados) {
                    const vale = valesAcerto.find((item) => item.id === valeSelecionado.id);
                    const valorDesconto = parseDecimalInput(valeSelecionado.valor_desconto);
                    if (!vale || !valorDesconto || valorDesconto <= 0 || valorDesconto > Number(vale.valor)) {
                      alert("Confira os valores de desconto dos vales selecionados.");
                      return;
                    }
                  }
                  gerarAcerto(
                    acertoData.motorista,
                    acertoData.inicio,
                    acertoData.fim,
                    acertoData.salvar,
                    acertoData.descontar_vales,
                    valesSelecionados
                  );
                  setShowAcertoModal(false);
                  setAcertoData({ motorista: "", inicio: "", fim: "", salvar: false, descontar_vales: false });
                  setResumoAcertoMotorista(null);
                  setValesAcerto([]);
                  setValesSelecionadosAcerto({});
                }}
              >
                GERAR PDF
              </button>
              <button
                className="btn-cancelar"
                onClick={() => {
                  setShowAcertoModal(false);
                  setResumoAcertoMotorista(null);
                  setValesAcerto([]);
                  setValesSelecionadosAcerto({});
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
