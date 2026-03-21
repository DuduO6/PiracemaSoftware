import { useState } from "react";

import { calcularSeguroCargas } from "../services/seguroCargasService";
import "../styles/seguroCargas.css";

const LOCALIDADES = [
  "Acre",
  "Alagoas",
  "Amapá",
  "Amazonas",
  "Bahia",
  "Ceará",
  "D.F.(Brasília)",
  "Esp.Santo",
  "Goiás",
  "Maranhão",
  "Mato Grosso",
  "M. G. do Sul",
  "Minas Gerais",
  "Pará",
  "Paraíba",
  "Paraná",
  "Pernambuco",
  "Piauí",
  "Rio de Janeiro",
  "R.G. do Norte",
  "R.G. do Sul",
  "Rondônia",
  "Roraima",
  "S.Cantarina",
  "São Paulo",
  "Sergipe",
  "Tocantis",
  "Urbano",
];

const formatarMoeda = valor =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(valor || 0));

const valorInicial = {
  origem: "",
  destino: "",
  valor_rctr_c: "",
  valor_rcdc: "",
};

function SeguroCargas() {
  const [formData, setFormData] = useState(valorInicial);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = event => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validarFormulario = () => {
    if (!formData.origem.trim() || !formData.destino.trim()) {
      return "Origem e destino são obrigatórios.";
    }

    const valorRctr = Number(formData.valor_rctr_c);
    const valorRcdc = Number(formData.valor_rcdc);

    if (Number.isNaN(valorRctr) || Number.isNaN(valorRcdc)) {
      return "Informe valores numéricos válidos para as cargas.";
    }

    if (valorRctr < 0 || valorRcdc < 0) {
      return "Os valores das cargas não podem ser negativos.";
    }

    if (valorRctr === 0 && valorRcdc === 0) {
      return "Informe ao menos um valor de carga maior que zero.";
    }

    return "";
  };

  const handleSubmit = async event => {
    event.preventDefault();
    setErro("");
    setResultado(null);

    const erroValidacao = validarFormulario();
    if (erroValidacao) {
      setErro(erroValidacao);
      return;
    }

    setLoading(true);

    try {
      const response = await calcularSeguroCargas({
        origem: formData.origem.trim(),
        destino: formData.destino.trim(),
        valor_rctr_c: Number(formData.valor_rctr_c),
        valor_rcdc: Number(formData.valor_rcdc),
      });
      setResultado(response);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      const serializerError = requestError.response?.data?.non_field_errors?.[0];
      setErro(detail || serializerError || "Não foi possível calcular o seguro de cargas.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="seguro-cargas-page">
      <section className="seguro-cargas-hero">
        <div>
          <p className="seguro-cargas-kicker">Seguro de Cargas</p>
          <h1>Calcule RCTR-C e RC-DC sem depender da planilha</h1>
          <p className="seguro-cargas-description">Informe origem, destino e valores da carga.</p>
        </div>
      </section>

      <section className="seguro-cargas-grid">
        <form className="seguro-cargas-card seguro-cargas-form" onSubmit={handleSubmit}>
          <div className="seguro-cargas-card-header">
            <h2>Dados da viagem</h2>
            <span>Preencha os campos para calcular</span>
          </div>

          <div className="seguro-cargas-fields">
            <label>
              Origem
              <div className="seguro-cargas-select-wrapper">
                <select
                  className="seguro-cargas-select-input"
                  name="origem"
                  value={formData.origem}
                  onChange={handleChange}
                >
                  <option value="">Selecione a origem</option>
                  {LOCALIDADES.map(localidade => (
                    <option key={`origem-${localidade}`} value={localidade}>
                      {localidade}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <label>
              Destino
              <div className="seguro-cargas-select-wrapper">
                <select
                  className="seguro-cargas-select-input"
                  name="destino"
                  value={formData.destino}
                  onChange={handleChange}
                >
                  <option value="">Selecione o destino</option>
                  {LOCALIDADES.map(localidade => (
                    <option key={`destino-${localidade}`} value={localidade}>
                      {localidade}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <label>
              Valor da carga RCTR-C
              <input
                type="number"
                name="valor_rctr_c"
                min="0"
                step="0.01"
                value={formData.valor_rctr_c}
                onChange={handleChange}
                placeholder="0,00"
              />
            </label>

            <label>
              Valor da carga RC-DC
              <input
                type="number"
                name="valor_rcdc"
                min="0"
                step="0.01"
                value={formData.valor_rcdc}
                onChange={handleChange}
                placeholder="0,00"
              />
            </label>
          </div>

          {erro ? <div className="seguro-cargas-alert erro">{erro}</div> : null}

          <div className="seguro-cargas-actions">
            <button type="submit" className="seguro-cargas-button" disabled={loading}>
              {loading ? "Calculando..." : "Calcular"}
            </button>
            <button
              type="button"
              className="seguro-cargas-button secondary"
              onClick={() => {
                setFormData(valorInicial);
                setResultado(null);
                setErro("");
              }}
              disabled={loading}
            >
              Limpar
            </button>
          </div>
        </form>

        <div className="seguro-cargas-card seguro-cargas-resultados">
          <div className="seguro-cargas-card-header">
            <h2>Resultado</h2>
            <span>Resumo do cálculo da apólice</span>
          </div>

          {resultado ? (
            <>
              <div className="seguro-cargas-summary">
                <div>
                  <strong>Origem</strong>
                  <span>{resultado.origem}</span>
                </div>
                <div>
                  <strong>Destino</strong>
                  <span>{resultado.destino}</span>
                </div>
                <div>
                  <strong>Taxa base</strong>
                  <span>{resultado.taxa_base_encontrada}%</span>
                </div>
                <div>
                  <strong>Busca</strong>
                  <span>{resultado.taxa_base_modo_busca}</span>
                </div>
              </div>

              <div className="seguro-cargas-metrics">
                <article>
                  <span>RCTR-C sem IOF</span>
                  <strong>{formatarMoeda(resultado.rctr_c_sem_iof)}</strong>
                </article>
                <article>
                  <span>RCTR-C com IOF</span>
                  <strong>{formatarMoeda(resultado.rctr_c_com_iof)}</strong>
                </article>
                <article>
                  <span>RC-DC sem IOF</span>
                  <strong>{formatarMoeda(resultado.rcdc_sem_iof)}</strong>
                </article>
                <article>
                  <span>RC-DC com IOF</span>
                  <strong>{formatarMoeda(resultado.rcdc_com_iof)}</strong>
                </article>
              </div>

              <div className="seguro-cargas-total">
                <span>Total</span>
                <strong>{formatarMoeda(resultado.total)}</strong>
              </div>
            </>
          ) : (
            <div className="seguro-cargas-empty">
              <p>Os valores calculados aparecerão aqui após o envio.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default SeguroCargas;
