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
                <p><strong>Estimated Temperature:</strong> ${data.temperature}°C</p>
                <p><strong>Estimated Humidity:</strong> ${data.humidity}%</p>
                <p><strong>Estimated Precipitation:</strong> ${data.precipitation_mm} mm</p>
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
