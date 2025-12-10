import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/caminhoes.css";

function Caminhoes() {
  const [caminhoes, setCaminhoes] = useState([]);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [modoRemocao, setModoRemocao] = useState(false);
  const [caminhaoSelecionado, setCaminhaoSelecionado] = useState(null);
  const [formData, setFormData] = useState({});
  const [placas, setPlacas] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/caminhoes/")
      .then(res => setCaminhoes(res.data))
      .catch(err => console.error("Erro ao carregar caminhões:", err));
  }, []);

  const handleCardClick = (caminhao) => {
    if (modoEdicao) {
      setCaminhaoSelecionado(caminhao);
      setFormData({ ...caminhao });
      
      // Inicializar array de placas apenas com as carretas (cavalo é separado)
      const placasIniciais = caminhao.carretas.map(c => ({ 
        placa: c.placa, 
        renavam: c.renavam || "", 
        crlv: null 
      }));
      setPlacas(placasIniciais);
    } else if (modoRemocao) {
      handleRemoverCaminhao(caminhao);
    } else {
      // Modo normal: navegar para a página de informações
      navigate(`/caminhoes/${caminhao.id}`);
    }
  };

  const handleEditarClick = () => {
    setModoEdicao(!modoEdicao);
    if (modoEdicao) {
      setCaminhaoSelecionado(null);
    }
    if (modoRemocao) {
      setModoRemocao(false);
    }
  };

  const handleRemoverClick = () => {
    setModoRemocao(!modoRemocao);
    if (modoRemocao) {
      setCaminhaoSelecionado(null);
    }
    if (modoEdicao) {
      setModoEdicao(false);
      setCaminhaoSelecionado(null);
    }
  };

  const handleRemoverCaminhao = async (caminhao) => {
    const confirmar = window.confirm(
      `Tem certeza que deseja remover o caminhão "${caminhao.nome_conjunto}"?\nEsta ação não pode ser desfeita.`
    );

    if (!confirmar) return;

    try {
      await api.delete(`/api/caminhoes/${caminhao.id}/`);
      
      setCaminhoes(caminhoes.filter(c => c.id !== caminhao.id));
      setModoRemocao(false);
      alert("Caminhão removido com sucesso!");

    } catch (err) {
      console.error("Erro ao remover caminhão:", err);
      alert("Erro ao remover caminhão");
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });

    // Quando mudar qtd_placas, ajustar array de placas (qtd_placas - 1, pois o cavalo é separado)
    if (name === "qtd_placas") {
      const qtd = parseInt(value);
      const qtdCarretas = qtd - 1; // Subtrair 1 porque o cavalo já está definido
      const novaLista = Array.from({ length: qtdCarretas }, (_, i) => 
        placas[i] || { placa: "", renavam: "", crlv: null }
      );
      setPlacas(novaLista);
    }
  };

  const updatePlaca = (index, field, value) => {
    const novaLista = [...placas];
    novaLista[index][field] = value;
    setPlacas(novaLista);
  };

  const handleSalvar = async () => {
    // Validar placa do cavalo
    if (!formData.placa_cavalo || !formData.renavam_cavalo) {
      alert("Placa e RENAVAM do cavalo são obrigatórios");
      return;
    }

    // Validar campos essenciais das carretas
    for (let i = 0; i < placas.length; i++) {
      if (!placas[i].placa || !placas[i].renavam) {
        alert(`Placa e RENAVAM são obrigatórios para Carreta ${i + 1}`);
        return;
      }
    }

    try {
      const form = new FormData();

      form.append("nome_conjunto", formData.nome_conjunto);
      form.append("qtd_placas", formData.qtd_placas);
      form.append("placa_cavalo", formData.placa_cavalo);
      form.append("renavam_cavalo", formData.renavam_cavalo);

      // JSON com dados das carretas
      form.append(
        "carretas",
        JSON.stringify(
          placas.map((p, i) => ({
            placa: p.placa,
            renavam: p.renavam,
            crlv_index: i
          }))
        )
      );

      // Anexar arquivos CRLV (opcionais)
      placas.forEach((p, i) => {
        if (p.crlv) {
          form.append(`crlv_${i}`, p.crlv);
        }
      });

      await api.put(`/api/caminhoes/${caminhaoSelecionado.id}/`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Recarregar lista
      const res = await api.get("/api/caminhoes/");
      setCaminhoes(res.data);

      setCaminhaoSelecionado(null);
      setModoEdicao(false);
      alert("Caminhão atualizado com sucesso!");

    } catch (err) {
      console.error("Erro ao atualizar caminhão:", err);
      alert("Erro ao atualizar caminhão");
    }
  };

  const handleCancelar = () => {
    setCaminhaoSelecionado(null);
    setFormData({});
    setPlacas([]);
  };

  return (
    <div className="caminhoes-container">
      <h1 className="titulo">CAMINHÕES</h1>

      <div className="btn-row">
        <button className="white-btn" onClick={() => navigate("/caminhoes/novo")}>
          NOVO
        </button>

        <button 
          className={`white-btn ${modoEdicao ? 'active' : ''}`}
          onClick={handleEditarClick}
        >
          {modoEdicao ? "CANCELAR EDIÇÃO" : "EDITAR"}
        </button>

        <button 
          className={`white-btn ${modoRemocao ? 'active-remover' : ''}`}
          onClick={handleRemoverClick}
        >
          {modoRemocao ? "CANCELAR REMOÇÃO" : "REMOVER"}
        </button>
      </div>

      {modoEdicao && !caminhaoSelecionado && (
        <p className="modo-edicao-aviso">
          Clique em um card para editar o caminhão
        </p>
      )}

      {modoRemocao && (
        <p className="modo-remocao-aviso">
          Clique em um card para remover o caminhão
        </p>
      )}

      {/* Modal de Edição */}
      {caminhaoSelecionado && (
        <div className="modal-overlay" onClick={handleCancelar}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Editar Caminhão</h2>
            
            <div className="form-group">
              <label>Nome do Conjunto:</label>
              <input
                type="text"
                name="nome_conjunto"
                value={formData.nome_conjunto || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>Placa do Cavalo *</label>
              <input
                type="text"
                name="placa_cavalo"
                value={formData.placa_cavalo || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>RENAVAM do Cavalo *</label>
              <input
                type="text"
                name="renavam_cavalo"
                value={formData.renavam_cavalo || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>Quantidade Total de Placas (Cavalo + Carretas):</label>
              <input
                type="number"
                name="qtd_placas"
                min="1"
                value={formData.qtd_placas || ''}
                onChange={handleInputChange}
              />
            </div>

            {placas.length > 0 && <h3 className="subtitulo-modal">Informações das Carretas</h3>}

            {placas.map((item, index) => (
              <div key={index} className="crlv-card-modal">
                <h4>Carreta {index + 1}</h4>

                <div className="form-group">
                  <label>Placa *</label>
                  <input
                    type="text"
                    value={item.placa}
                    onChange={(e) => updatePlaca(index, "placa", e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>RENAVAM *</label>
                  <input
                    type="text"
                    value={item.renavam}
                    onChange={(e) => updatePlaca(index, "renavam", e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>CRLV (opcional)</label>
                  <input
                    type="file"
                    onChange={(e) => updatePlaca(index, "crlv", e.target.files[0])}
                    className="file-input"
                  />
                </div>
              </div>
            ))}

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={handleSalvar}>
                SALVAR
              </button>
              <button className="btn-cancelar" onClick={handleCancelar}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="cards-grid">
        {caminhoes.map((c) => (
          <div 
            key={c.id} 
            className={`caminhao-card ${modoEdicao ? 'editavel' : ''} ${modoRemocao ? 'removivel' : ''}`}
            onClick={() => handleCardClick(c)}
            style={{ cursor: 'pointer' }}
          >
            <h2 className="caminhao-nome">{c.nome_conjunto}</h2>
            <p><strong>Placa cavalo:</strong> {c.placa_cavalo}</p>
            <p><strong>Total de placas:</strong> {c.qtd_placas}</p>
            <p><strong>Carretas:</strong> {c.carretas.length}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Caminhoes;