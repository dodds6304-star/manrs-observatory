import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import westAfricaData from '../data/west_africa.json';

function WestAfricaMap({ countries }) {
  function getColor(score) {
    if (score < 25) return '#e74c3c';
    if (score < 60) return '#f39c12';
    return '#27ae60';
  }

  function getCountryScore(isoCode) {
    const country = countries.find(c => c.country_code === isoCode);
    return country ? country.avg_manrs_score : 0;
  }

  function styleFeature(feature) {
    const isoCode = feature.properties['ISO3166-1-Alpha-2'];
    const score = getCountryScore(isoCode);
    return {
      fillColor: getColor(score),
      fillOpacity: 0.7,
      color: '#ffffff',
      weight: 1
    };
  }

  return (
    <MapContainer center={[10, -5]} zoom={5} minZoom={4} style={{ height: '500px', width: '100%' }} scrollWheelZoom={false}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />
      <GeoJSON data={westAfricaData} style={styleFeature} />
    </MapContainer>
  );
}

export default WestAfricaMap;