import { useEffect } from "react";
import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import Register from "./components/Register.jsx";
import Login from "./components/Login.jsx";
import Home from "./components/Home.jsx";
import Caminhoes from "./components/Caminhoes.jsx";
import NovoCaminhao from "./components/NovoCaminhao.jsx";
import CaminhaoDetalhes from "./components/CaminhaoDetalhes.jsx";
import Layout from "./components/Layout.jsx";
import Motoristas from "./components/Motoristas.jsx";
import NovoMotorista from "./components/NovoMotorista.jsx";
import MotoristaDetalhes from "./components/MotoristaDetalhes.jsx";
import Viagens from "./components/Viagens.jsx";
import Despesas from "./components/Despesas.jsx";
import Acertos from "./components/Acertos.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import SeguroCargas from "./pages/SeguroCargas.jsx";

function App() {
  useEffect(() => {
    const handleNumberInputWheel = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      const numberInput = target.closest('input[type="number"]');
      if (!numberInput) return;

      if (document.activeElement === numberInput) {
        numberInput.blur();
      }
      event.preventDefault();
    };

    document.addEventListener("wheel", handleNumberInputWheel, {
      passive: false,
      capture: true,
    });

    return () => {
      document.removeEventListener("wheel", handleNumberInputWheel, {
        capture: true,
      });
    };
  }, []);

  return (
    <HashRouter>
      <Routes>
        {/* Rotas públicas */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Rotas protegidas com sidebar */}
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/home" element={<Home />} />
          <Route path="/caminhoes" element={<Caminhoes />} />
          <Route path="/caminhoes/novo" element={<NovoCaminhao />} />
          <Route path="/caminhoes/:id" element={<CaminhaoDetalhes />} />
          <Route path="/motoristas" element={<Motoristas />} />
          <Route path="/motoristas/novo" element={<NovoMotorista />} />
          <Route path="/motoristas/:id" element={<MotoristaDetalhes />} />
          <Route path="/viagens" element={<Viagens />} />
          <Route path="/despesas" element={<Despesas />} />
          <Route path="/acertos" element={<Acertos />} />
          <Route path="/seguro-cargas" element={<SeguroCargas />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
