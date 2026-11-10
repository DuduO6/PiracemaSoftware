import UiIcon from "./UiIcon";
import { useTheme } from "../theme/ThemeContext";

const icons = { light: "sun", dark: "moon", system: "system" };

export default function ThemeControl({ compact = false }) {
  const { preference, setPreference } = useTheme();
  return (
    <label className={`theme-control ${compact ? "compact" : ""}`} title="Tema da interface">
      <UiIcon name={icons[preference]} size={18} />
      <span className="sr-only">Tema da interface</span>
      <select
        aria-label="Tema da interface"
        value={preference}
        onChange={(event) => setPreference(event.target.value)}
      >
        <option value="system">Automático</option>
        <option value="light">Claro</option>
        <option value="dark">Escuro</option>
      </select>
    </label>
  );
}
