import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/novoCaminhao.css";

function NovoCaminhao() {
  const navigate = useNavigate();

  const [nomeConjunto, setNomeConjunto] = useState("");
  const [qtdPlacas, setQtdPlacas] = useState(1);
  const [custos, setCustos] = useState({
    ipva_anual: "",
    licenciamento_anual: "",
    seguro_anual: "",
    seguro_terceiros_anual: "",
  });

  // Cada entrada representa: { placa, renavam, crlv }
  const [placas, setPlacas] = useState([
    { placa: "", renavam: "", crlv: null }
  ]);

  // atualizar quantidade de placas
  const handleQtdPlacas = (valor) => {
    setQtdPlacas(valor);

    // reconstruir array
    const novaLista = Array.from({ length: valor }, (_, i) => 
      placas[i] || { placa: "", renavam: "", crlv: null }
    );

    setPlacas(novaLista);
  };

  // atualização de cada campo das placas
  const updatePlaca = (index, field, value) => {
    const novaLista = [...placas];
    novaLista[index][field] = value;
    setPlacas(novaLista);
  };

  const handleCustosChange = event => {
    const { name, value } = event.target;
    setCustos(prev => ({ ...prev, [name]: value }));
  };

  // enviar
  const handleSubmit = async (e) => {
    e.preventDefault();

    // validar campos essenciais (PLACA e RENAVAM)
    for (let i = 0; i < placas.length; i++) {
      if (!placas[i].placa || !placas[i].renavam) {
        alert(`Placa e RENAVAM são obrigatórios para a posição ${i + 1}`);
        return;
      }
    }

    try {
      const form = new FormData();

      form.append("nome_conjunto", nomeConjunto);
      form.append("qtd_placas", qtdPlacas);
      form.append("ipva_anual", custos.ipva_anual || 0);
      form.append("licenciamento_anual", custos.licenciamento_anual || 0);
      form.append("seguro_anual", custos.seguro_anual || 0);
      form.append("seguro_terceiros_anual", custos.seguro_terceiros_anual || 0);

      // JSON com dados manuais
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

      // anexar arquivos CRLV (opcionais)
      placas.forEach((p, i) => {
        if (p.crlv) {
          form.append(`crlv_${i}`, p.crlv);
        }
      });

      await api.post("/api/caminhoes/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      alert("Caminhão cadastrado com sucesso!");
      navigate("/caminhoes");

    } catch (err) {
      console.error("Erro ao cadastrar:", err);
      alert("Erro ao cadastrar caminhão.");
    }
  };

  return (
    <div className="novo-container">
      <h1 className="titulo">NOVO CAMINHÃO</h1>

      <form className="form-card" onSubmit={handleSubmit}>

        <label>Nome do Conjunto</label>
        <input
          type="text"
          value={nomeConjunto}
          onChange={(e) => setNomeConjunto(e.target.value)}
          className="input"
          placeholder="Ex: Conjunto Scania 2021"
        />

        <label>Quantidade total de placas (cavalo + carretas)</label>
        <input
          type="number"
          min="1"
          value={qtdPlacas}
          onChange={(e) => handleQtdPlacas(parseInt(e.target.value))}
          className="input"
        />

        <h2 className="subtitulo">Informações das Placas</h2>

        {placas.map((item, index) => (
          <div key={index} className="crlv-card">
            <h3>{index === 0 ? "Cavalo" : `Carreta ${index}`}</h3>

            <label>Placa *</label>
            <input
              type="text"
              value={item.placa}
              onChange={(e) => updatePlaca(index, "placa", e.target.value)}
              className="input"
            />

            <label>RENAVAM *</label>
            <input
              type="text"
              value={item.renavam}
              onChange={(e) => updatePlaca(index, "renavam", e.target.value)}
              className="input"
            />

          </div>
        ))}

        <h2 className="subtitulo">Custos Fixos Anuais</h2>

        <label>IPVA anual</label>
        <input type="number" step="0.01" min="0" name="ipva_anual" value={custos.ipva_anual} onChange={handleCustosChange} className="input" />

        <label>Licenciamento anual</label>
        <input type="number" step="0.01" min="0" name="licenciamento_anual" value={custos.licenciamento_anual} onChange={handleCustosChange} className="input" />

        <label>Seguro anual</label>
        <input type="number" step="0.01" min="0" name="seguro_anual" value={custos.seguro_anual} onChange={handleCustosChange} className="input" />

        <label>Seguro de terceiros</label>
        <input type="number" step="0.01" min="0" name="seguro_terceiros_anual" value={custos.seguro_terceiros_anual} onChange={handleCustosChange} className="input" />

        <button className="white-btn salvar-btn">SALVAR</button>
      </form>
    </div>
  );
}

export default NovoCaminhao;
