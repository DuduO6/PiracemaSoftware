import { BrowserRouter, Routes, Route } from "react-router-dom";
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

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Sem sidebar */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Com sidebar */}
        <Route element={<Layout />}>
          <Route path="/home" element={<Home />} />
          <Route path="/caminhoes" element={<Caminhoes />} />
          <Route path="/caminhoes/novo" element={<NovoCaminhao />} />
          <Route path="/caminhoes/:id" element={<CaminhaoDetalhes />} />
          <Route path="/motoristas" element={<Motoristas />} />
          <Route path="/motoristas/novo" element={<NovoMotorista />} />
          <Route path="/motoristas/:id" element={<MotoristaDetalhes />} />
          <Route path="/viagens" element={<Viagens />} />

        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default App;
