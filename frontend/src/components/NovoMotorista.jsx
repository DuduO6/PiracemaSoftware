import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/novoMotorista.css";

function NovoMotorista() {
  const navigate = useNavigate();

  const [nome, setNome] = useState("");
  const [cpf, setCpf] = useState("");
  const [idade, setIdade] = useState("");
  const [vencCnh, setVencCnh] = useState("");
  const [caminhao, setCaminhao] = useState("");

  const [caminhoes, setCaminhoes] = useState([]);

  // Carregar lista de conjuntos/caminhões
  useEffect(() => {
    api.get("/api/caminhoes/")
      .then(res => setCaminhoes(res.data))
      .catch(err => console.error("Erro ao carregar caminhões:", err));
  }, []);

  // Enviar cadastro
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const body = {
        nome,
        cpf,
        idade,
        venc_cnh: vencCnh,
        caminhao: caminhao || null,
      };

      await api.post("/api/motoristas/", body);

      alert("Motorista cadastrado com sucesso!");
      navigate("/motoristas");

    } catch (err) {
      console.error(err);
      alert("Erro ao salvar motorista.");
    }
  };

  return (
    <div className="novo-container">
      <h1 className="titulo">NOVO MOTORISTA</h1>

      <form className="form-card" onSubmit={handleSubmit}>

        <label>Nome Completo</label>
        <input
          type="text"
          className="input"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
        />

        <label>CPF</label>
        <input
          type="text"
          className="input"
          value={cpf}
          onChange={(e) => setCpf(e.target.value)}
          required
        />

        <label>Idade</label>
        <input
          type="number"
          className="input"
          value={idade}
          onChange={(e) => setIdade(e.target.value)}
          required
        />

        <label>Vencimento da CNH</label>
        <input
          type="date"
          className="input"
          value={vencCnh}
          onChange={(e) => setVencCnh(e.target.value)}
          required
        />

        <label>Vincular ao Conjunto</label>
        <select
          className="input"
          value={caminhao}
          onChange={(e) => setCaminhao(e.target.value)}
        >
          <option value="">Nenhum</option>

          {caminhoes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome_conjunto} — {c.placa_cavalo}
            </option>
          ))}
        </select>

        <button className="white-btn salvar-btn">SALVAR</button>

      </form>
    </div>
  );
}

export default NovoMotorista;
