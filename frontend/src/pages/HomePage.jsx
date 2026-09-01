import { useState, useEffect } from 'react';
import WestAfricaMap from '../components/WestAfricaMap';

function HomePage() {
  const [countries, setCountries] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/countries')
      .then(response => response.json())
      .then(data => setCountries(data));

    fetch('http://127.0.0.1:8000/api/stats')
      .then(response => response.json())
      .then(data => setStats(data));
  }, []);

  return (
    <div>
      <h1>MANRS West Africa Observatory</h1>

      {stats && (
        <div>
          <p>ASN surveillés : {stats.total_asn}</p>
          <p>Membres MANRS : {stats.manrs_members_pct}%</p>
          <p>Couverture ROA moyenne : {stats.roa_coverage_pct}%</p>
        </div>
      )}

      <WestAfricaMap countries={countries} />

      <table>
        <thead>
          <tr>
            <th>Pays</th>
            <th>Nb ASN</th>
            <th>Membres MANRS</th>
            <th>Score moyen</th>
            <th>% ROA</th>
          </tr>
        </thead>
        <tbody>
          {countries.map(country => (
            <tr key={country.country_code}>
              <td>{country.country_name}</td>
              <td>{country.total_asn}</td>
              <td>{country.manrs_members}</td>
              <td>{country.avg_manrs_score}%</td>
              <td>{country.roa_coverage_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default HomePage;