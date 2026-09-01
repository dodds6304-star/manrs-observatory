import { useState, useEffect } from 'react';

function HomePage() {
  const [countries, setCountries] = useState([]);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/countries')
      .then(response => response.json())
      .then(data => setCountries(data));
  }, []);

  return (
    <div>
      <h1>MANRS West Africa Observatory</h1>
      <p>{countries.length} pays chargés</p>
      <ul>
        {countries.map(country => (
          <li key={country.country_code}>
            {country.country_name} — Score: {country.avg_manrs_score}%
          </li>
        ))}
      </ul>
    </div>
  );
}

export default HomePage;