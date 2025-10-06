document.getElementById("getWeatherBtn").addEventListener("click", () => {
    const location = document.getElementById("location").value;
    const date = document.getElementById("datetime").value;
    const resultDiv = document.getElementById("result");
    resultDiv.innerHTML = `We are processing your request`

    if (!location || !date) {
        resultDiv.innerHTML = `<p style="color:red;">Please fill in all fields.</p>`;
        return;
    }

    // POST request
    fetch("/weather", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `location=${encodeURIComponent(location)}&date=${encodeURIComponent(date)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.source == "prediction") {
            resultDiv.innerHTML = `
                <p><strong>Latitude:</strong> ${data.LAT}</p>
                <p><strong>Longitude:</strong> ${data.LON}</p>
                <p><strong>Date:</strong> ${data.DATE}</p>
                <p><strong>Estimated Temperature:</strong> ${Number(data.temperature).toFixed(1)}°C</p>
                <p><strong>Estimated Humidity:</strong> ${Number(data.humidity).toFixed(1)}%</p>
                <p><strong>Estimated Precipitation:</strong> ${Number(data.precipitation_mm).toFixed(2)} mm</p>
                <p><strong>General Weather:</strong> ${data.general_weather}</p>
                <p><strong>Source:</strong> ${data.source}</p>
            `;
            } else if (data.source == "real") {

            }
    })
    .catch(err => {
        resultDiv.innerHTML = `<p style="color:red;">Error fetching API: ${err}</p>`;
    });
});
