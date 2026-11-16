import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ThemeControl from "./components/ThemeControl";
import ManifestosMdfe from "./pages/ManifestosMdfe";
import {
  atualizarManifestos,
  listarEmpresasMdfe,
  listarManifestos,
} from "./services/mdfeService";
import { ThemeProvider } from "./theme/ThemeContext";

jest.mock("./services/mdfeService", () => ({
  atualizarManifestos: jest.fn(),
  confirmarOperacao: jest.fn(),
  criarEmpresaMdfe: jest.fn(),
  encerrarManifesto: jest.fn(),
  importarXmlMdfe: jest.fn(),
  listarEmpresasMdfe: jest.fn(),
  listarHistoricoMdfe: jest.fn(),
  listarManifestos: jest.fn(),
  obterConfiguracaoFiscal: jest.fn(),
  salvarConfiguracaoFiscal: jest.fn(),
}));

let mediaQuery;

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  mediaQuery = {
    matches: false,
    media: "(prefers-color-scheme: dark)",
    addEventListener: jest.fn((event, callback) => { mediaQuery.listener = callback; }),
    removeEventListener: jest.fn(),
  };
  window.matchMedia = jest.fn().mockReturnValue(mediaQuery);
});

test("alterna o tema e persiste a preferência do usuário", () => {
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);

  const selector = screen.getByLabelText("Tema da interface");
  expect(selector).toHaveValue("system");
  expect(document.documentElement).toHaveAttribute("data-theme", "light");

  fireEvent.change(selector, { target: { value: "dark" } });

  expect(selector).toHaveValue("dark");
  expect(localStorage.getItem("piracema-theme")).toBe("dark");
  expect(document.documentElement).toHaveAttribute("data-theme", "dark");
});

test("acompanha mudanças do sistema enquanto o tema está no modo automático", () => {
  mediaQuery.matches = true;
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  expect(document.documentElement).toHaveAttribute("data-theme", "dark");

  act(() => {
    mediaQuery.matches = false;
    mediaQuery.listener();
  });

  expect(document.documentElement).toHaveAttribute("data-theme", "light");
});

test("consulta a SEFAZ somente após clique em Atualizar manifestos", async () => {
  listarEmpresasMdfe.mockResolvedValue({
    data: [{ id: 1, nome: "Transportadora Teste", papel: "ADMIN" }],
  });
  listarManifestos.mockResolvedValue({
    data: {
      count: 0,
      results: {
        items: [],
        resumo: { abertos: 0, encerrados: 0, pendentes: 0 },
        consulta: null,
      },
    },
  });
  atualizarManifestos.mockResolvedValue({ data: { estado: "SUCESSO" } });

  render(<ThemeProvider><ManifestosMdfe /></ThemeProvider>);

  await waitFor(() => expect(listarManifestos).toHaveBeenCalledTimes(1));
  expect(atualizarManifestos).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: /atualizar manifestos/i }));

  await waitFor(() => expect(atualizarManifestos).toHaveBeenCalledTimes(1));
});

test("não mantém a lista de municípios sobre a data ao abrir o encerramento", async () => {
  listarEmpresasMdfe.mockResolvedValue({
    data: [{ id: 1, nome: "Transportadora Teste", papel: "ADMIN" }],
  });
  listarManifestos.mockResolvedValue({
    data: {
      count: 1,
      results: {
        items: [{
          chave: "31261129725802000140580010000003001309348491",
          numero: "300",
          situacao: "ABERTO",
          situacao_display: "Aberto",
          protocolo_autorizacao: "931260068258794",
          destinos: [{ codigo: 3150604, municipio: "Piracema", uf: "MG" }],
          condutores: [],
        }],
        resumo: { abertos: 1, encerrados: 0, pendentes: 0 },
        consulta: null,
      },
    },
  });

  render(<ThemeProvider><ManifestosMdfe /></ThemeProvider>);

  await waitFor(() => expect(screen.getAllByRole("button", { name: /encerrar mdf-e/i })).toHaveLength(2));
  fireEvent.click(screen.getAllByRole("button", { name: /encerrar mdf-e/i })[0]);

  expect(screen.getByRole("dialog", { name: /confirmar encerramento do mdf-e/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/município de encerramento/i)).toHaveValue("Piracema - MG");
  expect(screen.queryByRole("listbox", { name: /municípios encontrados/i })).not.toBeInTheDocument();
  expect(screen.getByLabelText(/data efetiva do encerramento/i)).toBeInTheDocument();
});
