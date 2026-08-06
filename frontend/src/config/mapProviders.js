const providers = {
  osm: { name: "OpenStreetMap", url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19 },
  cartodb: { name: "CartoDB Positron", url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 20 },
  opentopomap: { name: "OpenTopoMap", url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attribution: 'Map data &copy; OpenStreetMap contributors, SRTM | Map style &copy; OpenTopoMap', maxZoom: 17 },
};

export function getTileProvider(providerName = process.env.REACT_APP_TILE_PROVIDER || "osm", customUrl = "") {
  if (customUrl) return { name: "Personalizado", url: customUrl, attribution: "", maxZoom: 20 };
  return providers[providerName] || providers.osm;
}

export { providers as mapTileProviders };
