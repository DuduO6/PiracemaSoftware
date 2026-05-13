import React, { useEffect, useState } from "react";
import api from "../api/api";
import PaginationControls from "./PaginationControls.jsx";
import "../styles/acertos.css";

const ITENS_POR_PAGINA = 10;
const ITENS_MODAL_POR_PAGINA = 12;

const Acertos = () => {
  const [acertos, setAcertos] = useState([]);
  const [acertoSelecionado, setAcertoSelecionado] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [paginaItensModal, setPaginaItensModal] = useState(1);
  const [paginaValesModal, setPaginaValesModal] = useState(1);
  const [paginaValesAtivosModal, setPaginaValesAtivosModal] = useState(1);

  useEffect(() => {
    carregarAcertos();
  }, []);

  const carregarAcertos = () => {
    api.get("/api/acertos/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || [];
        setAcertos(data);
      })
      .catch((err) => console.error("Erro ao carregar acertos:", err));
  };

  const visualizarAcerto = (id) => {
    api.get(`/api/acertos/${id}/`)
      .then((res) => {
        setAcertoSelecionado(res.data);
        setPaginaItensModal(1);
        setPaginaValesModal(1);
        setPaginaValesAtivosModal(1);
        setShowModal(true);
      })
      .catch((err) => console.error("Erro ao carregar detalhes:", err));
  };

  const fecharModal = () => {
    setShowModal(false);
    setAcertoSelecionado(null);
    setPaginaItensModal(1);
    setPaginaValesModal(1);
    setPaginaValesAtivosModal(1);
  };

  const formatarData = (dataStr) => {
    const [ano, mes, dia] = dataStr.split('-');
    return `${dia}/${mes}/${ano}`;
  };

  const formatarDataHora = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleString('pt-BR');
  };

  const totalPaginas = Math.max(1, Math.ceil(acertos.length / ITENS_POR_PAGINA));
  useEffect(() => {
    if (paginaAtual > totalPaginas) {
      setPaginaAtual(totalPaginas);
    }
  }, [paginaAtual, totalPaginas]);

  const acertosPaginados = acertos.slice(
    (paginaAtual - 1) * ITENS_POR_PAGINA,
    paginaAtual * ITENS_POR_PAGINA
  );

  const itensModal = acertoSelecionado?.itens || [];
  const valesModal = acertoSelecionado?.vales || [];
  const valesAtivosModal = acertoSelecionado?.vales_ativos || [];
  const itensPaginados = itensModal.slice(
    (paginaItensModal - 1) * ITENS_MODAL_POR_PAGINA,
    paginaItensModal * ITENS_MODAL_POR_PAGINA
  );
  const valesPaginados = valesModal.slice(
    (paginaValesModal - 1) * ITENS_MODAL_POR_PAGINA,
    paginaValesModal * ITENS_MODAL_POR_PAGINA
  );
  const valesAtivosPaginados = valesAtivosModal.slice(
    (paginaValesAtivosModal - 1) * ITENS_MODAL_POR_PAGINA,
    paginaValesAtivosModal * ITENS_MODAL_POR_PAGINA
  );
  const calcularValorBrutoCte = (acerto) => {
    if (acerto?.valor_bruto_viagens_com_cte !== undefined && acerto?.valor_bruto_viagens_com_cte !== null) {
      return Number(acerto.valor_bruto_viagens_com_cte);
    }

    return Number(acerto?.valor_total_viagens_com_cte || 0) + Number(acerto?.desconto_cte || 0);
  };

  return (
    <div className="acertos-container">
      <h1 className="titulo">HISTÓRICO DE ACERTOS</h1>

      <div className="info-acertos">
        <p className="total-text">TOTAL DE ACERTOS: {acertos.length}</p>
      </div>

      <div className="table-wrapper">
        <table className="acertos-table">
          <thead>
            <tr>
              <th>DATA GERAÇÃO</th>
              <th>MOTORISTA</th>
              <th>PERÍODO</th>
              <th>VIAGENS</th>
              <th>VALOR A RECEBER</th>
              <th>AÇÕES</th>
            </tr>
          </thead>
          <tbody>
            {acertosPaginados.map((acerto) => (
              <tr key={acerto.id}>
                <td>{formatarDataHora(acerto.data_geracao)}</td>
                <td>{acerto.motorista_nome}</td>
                <td>
                  {formatarData(acerto.data_inicio)} até {formatarData(acerto.data_fim)}
                </td>
                <td>{acerto.total_viagens}</td>
                <td>R$ {Number(acerto.valor_a_receber).toFixed(2)}</td>
                <td>
                  <button
                    className="btn-visualizar"
                    onClick={() => visualizarAcerto(acerto.id)}
                  >
                    VISUALIZAR
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PaginationControls
          totalItems={acertos.length}
          itemsPerPage={ITENS_POR_PAGINA}
          currentPage={paginaAtual}
          onPageChange={setPaginaAtual}
        />
      </div>

      {/* Modal de Detalhes */}
      {showModal && acertoSelecionado && (
        <div className="modal-overlay" onClick={fecharModal}>
          <div className="modal-acerto-detalhes" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Detalhes do Acerto</h2>
              <button className="btn-fechar" onClick={fecharModal}>✕</button>
            </div>

            <div className="acerto-info-box">
              <div className="info-row">
                <strong>Período:</strong> {formatarData(acertoSelecionado.data_inicio)} até {formatarData(acertoSelecionado.data_fim)}
              </div>
            </div>

            <div className="acerto-section">
              <h3>Viagens ({acertoSelecionado.total_viagens})</h3>
              <div className="table-wrapper-modal">
                <table className="tabela-modal">
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
                    </tr>
                  </thead>
                  <tbody>
                    {itensPaginados.map((item) => (
                      <tr key={item.id}>
                        <td>{formatarData(item.data)}</td>
                        <td>{item.origem}</td>
                        <td>{item.destino}</td>
                        <td>{item.cliente}</td>
                        <td>{item.peso}</td>
                        <td>R$ {Number(item.valor_tonelada).toFixed(2)}</td>
                        <td>R$ {Number(item.valor_bruto || item.valor_total).toFixed(2)}</td>
                        <td>R$ {Number(item.valor_desconto_cte || 0).toFixed(2)}</td>
                        <td>R$ {Number(item.valor_total).toFixed(2)}</td>
                        <td>{item.teve_cte ? "SIM" : "NÃO"}</td>
                        <td>
                          <span className={`status-badge ${item.pago ? 'status-pago' : 'status-pendente'}`}>
                            {item.pago ? "SIM" : "NÃO"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <PaginationControls
                  totalItems={itensModal.length}
                  itemsPerPage={ITENS_MODAL_POR_PAGINA}
                  currentPage={paginaItensModal}
                  onPageChange={setPaginaItensModal}
                />
              </div>
            </div>

            <div className="acerto-section">
              <h3>Vales descontados ({acertoSelecionado.vales.length})</h3>
              <div className="table-wrapper-modal">
                <table className="tabela-modal">
                  <thead>
                    <tr>
                      <th>DATA</th>
                      <th>SALDO ANTES</th>
                      <th>DESCONTO</th>
                      <th>SALDO APÓS</th>
                      <th>SITUAÇÃO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valesPaginados.length > 0 ? (
                      valesPaginados.map((vale) => (
                        <tr key={vale.id}>
                          <td>{formatarData(vale.data)}</td>
                          <td>R$ {Number(vale.valor_original || 0).toFixed(2)}</td>
                          <td>R$ {Number(vale.valor).toFixed(2)}</td>
                          <td>R$ {Number(vale.valor_restante || 0).toFixed(2)}</td>
                          <td>{vale.quitado ? "QUITADO" : "PARCIAL"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="tabela-vazia">Nenhum vale descontado neste acerto.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <PaginationControls
                  totalItems={valesModal.length}
                  itemsPerPage={ITENS_MODAL_POR_PAGINA}
                  currentPage={paginaValesModal}
                  onPageChange={setPaginaValesModal}
                />
              </div>
            </div>

            <div className="acerto-section">
              <h3>Vales ativos do motorista ({valesAtivosModal.length})</h3>
              <div className="table-wrapper-modal">
                <table className="tabela-modal">
                  <thead>
                    <tr>
                      <th>DATA</th>
                      <th>VALOR ORIGINAL</th>
                      <th>SALDO ATUAL</th>
                      <th>DESCONTADO</th>
                      <th>SITUAÇÃO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valesAtivosPaginados.length > 0 ? (
                      valesAtivosPaginados.map((vale) => (
                        <tr key={vale.id}>
                          <td>{formatarData(vale.data)}</td>
                          <td>R$ {Number(vale.valor_original || 0).toFixed(2)}</td>
                          <td>R$ {Number(vale.valor || 0).toFixed(2)}</td>
                          <td>R$ {Number(vale.valor_descontado || 0).toFixed(2)}</td>
                          <td>ATIVO</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="tabela-vazia">Nenhum vale ativo para este motorista.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <PaginationControls
                  totalItems={valesAtivosModal.length}
                  itemsPerPage={ITENS_MODAL_POR_PAGINA}
                  currentPage={paginaValesAtivosModal}
                  onPageChange={setPaginaValesAtivosModal}
                />
              </div>
            </div>

            <div className="acerto-resumo">
              <table className="resumo-table">
                <thead>
                  <tr>
                    <th>DESCRIÇÃO</th>
                    <th>QUANTIDADE</th>
                    <th>VALOR</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Valor Total Líquido das Viagens</td>
                    <td>{acertoSelecionado.total_viagens}</td>
                    <td>R$ {Number(acertoSelecionado.valor_total_viagens).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Com CT-e - valor bruto</td>
                    <td>{acertoSelecionado.total_viagens_com_cte || 0}</td>
                    <td>R$ {calcularValorBrutoCte(acertoSelecionado).toFixed(2)}</td>
                  </tr>
                  <tr className="resumo-desconto">
                    <td>Desconto CT-e (10%)</td>
                    <td>-</td>
                    <td>- R$ {Number(acertoSelecionado.desconto_cte || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Com CT-e - líquido após desconto</td>
                    <td>{acertoSelecionado.total_viagens_com_cte || 0}</td>
                    <td>R$ {Number(acertoSelecionado.valor_total_viagens_com_cte || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Sem CT-e</td>
                    <td>{acertoSelecionado.total_viagens_sem_cte || 0}</td>
                    <td>R$ {Number(acertoSelecionado.valor_total_viagens_sem_cte || 0).toFixed(2)}</td>
                  </tr>
                  <tr className="resumo-total-liquido">
                    <td>Valor Total (com CT-e + sem CT-e)</td>
                    <td>{acertoSelecionado.total_viagens}</td>
                    <td>R$ {(
                      Number(acertoSelecionado.valor_total_viagens_com_cte || 0) +
                      Number(acertoSelecionado.valor_total_viagens_sem_cte || 0)
                    ).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Saldo dos Vales Selecionados</td>
                    <td>-</td>
                    <td>- R$ {Number(acertoSelecionado.total_vales).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Desconto Aplicado em Vales</td>
                    <td>{acertoSelecionado.vales?.length || 0}</td>
                    <td>- R$ {Number(acertoSelecionado.desconto_vales || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Comissão ({Number(acertoSelecionado.percentual_comissao || 13).toFixed(2)}% sobre o valor líquido)</td>
                    <td>-</td>
                    <td>R$ {Number(acertoSelecionado.comissao).toFixed(2)}</td>
                  </tr>
                  <tr className="resumo-valor-pagar">
                    <td>Valor a Pagar ao Motorista</td>
                    <td>-</td>
                    <td>R$ {Number(acertoSelecionado.valor_a_receber).toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="acerto-info-box acerto-info-box-bottom">
              <div className="info-row">
                <strong>Motorista:</strong> {acertoSelecionado.motorista_nome}
              </div>
              <div className="info-row">
                <strong>Data de Geração:</strong> {formatarDataHora(acertoSelecionado.data_geracao)}
              </div>
              {acertoSelecionado.regra_aplicada_nome && (
                <div className="info-row">
                  <strong>Regra aplicada:</strong> {acertoSelecionado.regra_aplicada_nome}
                </div>
              )}
            </div>

            <div className="modal-buttons">
              <button className="btn-cancelar" onClick={fecharModal}>
                FECHAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Acertos;
