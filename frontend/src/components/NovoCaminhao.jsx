import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/novoCaminhao.css";

function NovoCaminhao() {
  const navigate = useNavigate();

  const [nomeConjunto, setNomeConjunto] = useState("");
  const [qtdPlacas, setQtdPlacas] = useState(1);

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

        <button className="white-btn salvar-btn">SALVAR</button>
      </form>
    </div>
  );
}

export default NovoCaminhao;
