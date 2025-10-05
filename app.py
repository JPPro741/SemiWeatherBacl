from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="my_weather_app_2025_contact@myemail.com")  # descriptive and unique

app = Flask(__name__)

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/index.html')
def index2():
    return render_template('index.html')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def get_weather():
    address = str(request.form.get("location", "")).strip()
    DATE = str(request.form.get("date", "")).strip()

    if not address or not DATE:
        return jsonify({"error": "Both location and date are required"}), 400

    # Geocode safely
    try:
        location = geolocator.geocode(address, timeout=10)
        if not location:
            return jsonify({"error": "Address not found"}), 400
        LAT, LON = location.latitude, location.longitude
        print(f"Latitude: {LAT}, Longitude: {LON}")
    except Exception as e:
        return jsonify({"error": f"Geocoding failed: {str(e)}"}), 500

    print(f"Received from JS -> LAT: {LAT}, LON: {LON}, DATE: {DATE}")

    # Parameters
    DATE_COL = "date"
    RAIN_COL = "precip_mm"
    TEMP_COL = "tmean"
    HUM_COL = "rh"
    RAIN_DAY_THRESHOLD = 1.0
    EXTRA_VARS = ["tmax", "tmin", "rh"]

    # Last 15 years
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=15*365)

    # Fetch NASA POWER data
    BASE_URL = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}"
        f"&latitude={LAT}&longitude={LON}"
        "&parameters=T2M_MAX,T2M_MIN,RH2M,WS2M,PRECTOTCORR"
        "&community=AG&format=JSON"
    )

    try:
        r = requests.get(BASE_URL)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch NASA POWER data: {str(e)}"}), 500

    # Process data into DataFrame
    try:
        records = []
        dates = data["properties"]["parameter"]["T2M_MAX"].keys()
        for d in dates:
            records.append({
                "date": pd.to_datetime(d).strftime("%Y-%m-%d"),
                "tmax": data["properties"]["parameter"]["T2M_MAX"].get(d),
                "tmin": data["properties"]["parameter"]["T2M_MIN"].get(d),
                "rh": data["properties"]["parameter"]["RH2M"].get(d),
                "wind": data["properties"]["parameter"]["WS2M"].get(d),
                "precip_mm": data["properties"]["parameter"]["PRECTOTCORR"].get(d)
            })
        df = pd.DataFrame(records).sort_values("date")
    except Exception as e:
        return jsonify({"error": f"Failed to process data: {str(e)}"}), 500

    # Helper functions
    def md_tuple(dt):
        return (dt.month, dt.day)

    def window_stats(df):
        rain = df[RAIN_COL].fillna(0.0)
        out = {
            "sum_mm": rain.sum(),
            "mean_mm": rain.mean(),
            "p50_mm": np.percentile(rain, 50),
            "p90_mm": np.percentile(rain, 90),
            "rainy_days": (rain >= RAIN_DAY_THRESHOLD).sum(),
            "n_days": len(rain)
        }
        for v in EXTRA_VARS:
            if v in df.columns:
                out[f"{v}_mean"] = df[v].astype(float).mean()
        return out

    def predict_for_day(df, date_str, history_years=15):
        df[DATE_COL] = pd.to_datetime(df[DATE_COL])
        target_date = pd.to_datetime(date_str)

        # Check if real data exists
        df_day = df[df[DATE_COL] == target_date]
        if not df_day.empty:
            row = df_day.iloc[0]
            temp = float(row[TEMP_COL]) if TEMP_COL in df.columns else \
                   float((row["tmax"]+row["tmin"])/2) if "tmax" in df.columns and "tmin" in df.columns else None
            hum = float(row[HUM_COL]) if HUM_COL in df.columns else None
            precip = float(row[RAIN_COL]) if pd.notna(row[RAIN_COL]) else None
            clima_general = "rainy" if precip and precip >= RAIN_DAY_THRESHOLD else "dry"
            return {"DATE": str(target_date.date()), "temperature": temp, "humidity": hum, 
                    "precipitation_mm": precip, "general_weather": clima_general, "source": "real"}

        # Predict using past years
        start_md = md_tuple(target_date)
        past_years = df[(df[DATE_COL].dt.month == start_md[0]) & (df[DATE_COL].dt.day == start_md[1])]
        feats = window_stats(past_years)

        if len(past_years) >= 3:
            X = np.arange(len(past_years)).reshape(-1,1)
            y = past_years[RAIN_COL].fillna(0.0).values
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            y_pred = float(model.predict(np.array([[len(past_years)]])))
        else:
            y_pred = feats["mean_mm"]

        clima_general = "rainy" if y_pred >= RAIN_DAY_THRESHOLD else "dry"
        temp = feats.get("tmean_mean") or (feats.get("tmax_mean",0) + feats.get("tmin_mean",0))/2
        hum = feats.get("rh_mean")

        return {"DATE": str(target_date.date()), "LAT": LAT, "LON": LON,
                "temperature": temp, "humidity": hum, 
                "precipitation_mm": y_pred, "general_weather": clima_general, "source": "prediction"}

    # Predict for requested date
    summary = predict_for_day(df, DATE)
    print(summary)

    return jsonify(summary)


if __name__ == '__main__':
    app.run(debug=True)
