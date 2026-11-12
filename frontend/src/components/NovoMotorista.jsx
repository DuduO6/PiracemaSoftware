import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/novoMotorista.css";

const somenteDigitosCpf = (value) => String(value || "").replace(/\D/g, "").slice(0, 11);

const formatarCpf = (value) => {
  const digits = somenteDigitosCpf(value);
  return digits
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
};

const cpfValido = (value) => {
  const digits = somenteDigitosCpf(value);
  if (digits.length !== 11 || /^(\d)\1{10}$/.test(digits)) return false;
  const numbers = digits.split("").map(Number);
  const calcularDigito = (length) => {
    const total = numbers.slice(0, length).reduce((sum, number, index) => sum + number * (length + 1 - index), 0);
    const remainder = total % 11;
    return remainder < 2 ? 0 : 11 - remainder;
  };
  return numbers[9] === calcularDigito(9) && numbers[10] === calcularDigito(10);
};

const dataMaximaNascimento = () => {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 18);
  return date.toISOString().slice(0, 10);
};

function NovoMotorista() {
  const navigate = useNavigate();

  const [nome, setNome] = useState("");
  const [cpf, setCpf] = useState("");
  const [dataNascimento, setDataNascimento] = useState("");
  const [vencCnh, setVencCnh] = useState("");
  const [caminhao, setCaminhao] = useState("");
  const [cpfError, setCpfError] = useState("");

  const [caminhoes, setCaminhoes] = useState([]);

  // Carregar lista de conjuntos/caminhões
  useEffect(() => {
    api.get("/api/caminhoes/")
      .then(res => setCaminhoes(res.data))
      .catch(err => console.error("Erro ao carregar caminhões:", err));
  }, []);

  const calcularIdade = (dataNasc) => {
    if (!dataNasc) return 0;

    const hoje = new Date();
    const nascimento = new Date(dataNasc);

    let idade = hoje.getFullYear() - nascimento.getFullYear();
    const mes = hoje.getMonth() - nascimento.getMonth();

    if (
      mes < 0 ||
      (mes === 0 && hoje.getDate() < nascimento.getDate())
    ) {
      idade--;
    }

    return idade;
  };

  // Enviar cadastro
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!cpfValido(cpf)) {
      setCpfError("Informe um CPF válido.");
      return;
    }

    const idadeCalculada = calcularIdade(dataNascimento);

    if (idadeCalculada < 18) {
      alert("O motorista deve ter pelo menos 18 anos.");
      return;
    }

    try {
      const body = {
        nome,
        cpf,
        idade: idadeCalculada, // 👈 idade calculada
        venc_cnh: vencCnh,
        caminhao: caminhao || null,
      };

      await api.post("/api/motoristas/", body);

      alert("Motorista cadastrado com sucesso!");
      navigate("/motoristas");

    } catch (err) {
      console.error(err);
      const message = err.response?.data?.cpf?.[0] || err.response?.data?.detail || "Erro ao salvar motorista.";
      setCpfError(err.response?.data?.cpf?.[0] || "");
      alert(message);
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
          onChange={(e) => {
            setCpf(formatarCpf(e.target.value));
            setCpfError("");
          }}
          onBlur={() => setCpfError(cpf && !cpfValido(cpf) ? "Informe um CPF válido." : "")}
          inputMode="numeric"
          autoComplete="off"
          maxLength={14}
          aria-invalid={Boolean(cpfError)}
          aria-describedby="cpf-error"
          required
        />
        {cpfError && <small id="cpf-error" className="field-error" role="alert">{cpfError}</small>}

        <label>Data de nascimento</label>
        <div className="input-with-preview">
          <input
            type="date"
            className="input"
            value={dataNascimento}
            onChange={(e) => setDataNascimento(e.target.value)}
            max={dataMaximaNascimento()}
            autoComplete="bday"
            required
          />
          {dataNascimento && (
            <span className="idade-preview-inline">
              {calcularIdade(dataNascimento)} anos
            </span>
          )}
        </div>


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
