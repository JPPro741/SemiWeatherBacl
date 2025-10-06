document.getElementById("getWeatherBtn").addEventListener("click", () => {
    const location = document.getElementById("location").value;
    const date = document.getElementById("datetime").value;
    const resultDiv = document.getElementById("result");

    // Loading message
    resultDiv.innerHTML = `<p>⏳ We are processing your request...</p>`;

    // Check required fields
    if (!location || !date) {
        resultDiv.innerHTML = `<p style="color:red;">⚠️ Please fill in all fields.</p>`;
        return;
    }

    // Send request
    fetch("/weather", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `location=${encodeURIComponent(location)}&date=${encodeURIComponent(date)}`
    })
    .then(async response => {
        if (!response.ok) {
            // Handle HTTP error (like 400)
            const errData = await response.json().catch(() => ({}));
            const msg = errData.error || "❌ Location not found.";
            throw new Error(msg);
        }
        return response.json();
    })
    .then(data => {
        // Decide message based on source
        let sourceLabel =
            data.source === "prediction"
                ? "📈 Predicted Data"
                : "🌦️ Real Data";

        resultDiv.innerHTML = `
            <p><strong>Latitude:</strong> ${Number(data.LAT).toFixed(3)}</p>
            <p><strong>Longitude:</strong> ${Number(data.LON).toFixed(3)}</p>
            <p><strong>Date:</strong> ${data.DATE}</p>
            <p><strong>Temperature:</strong> ${Number(data.temperature).toFixed(1)}°C</p>
            <p><strong>Humidity:</strong> ${Number(data.humidity).toFixed(1)}%</p>
            <p><strong>Precipitation:</strong> ${Number(data.precipitation_mm).toFixed(2)} mm</p>
            <p><strong>General Weather:</strong> ${data.general_weather}</p>
            <p><strong>Source:</strong> ${sourceLabel}</p>
        `;
    })
    .catch(error => {
        resultDiv.innerHTML = `<p style="color:red;">${error.message}</p>`;
    });
});
