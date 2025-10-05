from flask import Flask, render_template, request
from flask import jsonify

app = Flask(__name__)

@app.route('/')
def index():
    # Show the HTML form
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    import time
    LAT = float(request.form["LAT"])  # default if missing
    LON = float(request.form["LON"])
    DATE = str(request.form["DATE"])
    print(LAT,DATE,LON)

    import os
    import requests
    import pandas as pd
    from datetime import datetime, timedelta
    from pathlib import Path
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    # === CONFIGURACIÓN ===
    BASE_DIR = Path(__file__).parent
    # Assign values from JSON to variables

    LAT = float(request.form["LAT"])
    LON = float(request.form["LON"])
    DATE = str(request.form["DATE"])

    print(f"LAT={LAT}, LON={LON}, DATE={DATE}")

    CSV_PATH = BASE_DIR / f"CSV/historico_diario.{LAT}.{LON}.{DATE}.csv"
    DATE_COL = "date"
    RAIN_COL = "precip_mm"
    TEMP_COL = "tmean"  # si existe
    HUM_COL = "rh"
    RAIN_DAY_THRESHOLD = 1.0
    EXTRA_VARS = ["tmax","tmin","rh"]

    # Últimos 15 años
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=15*365)

    # === DESCARGA DE DATOS NASA POWER ===
    BASE_URL = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}"
        f"&latitude={LAT}&longitude={LON}"
        "&parameters=T2M_MAX,T2M_MIN,RH2M,WS2M,PRECTOTCORR"
        "&community=AG&format=JSON"
    )

    folder = BASE_DIR / f"CSV"

    # List all files (only real files, not folders)
    files = [f for f in folder.glob("*") if f.is_file()]

    # Sort files by modification time (oldest first)
    files.sort(key=lambda f: f.stat().st_mtime)

    # If more than 10 files, delete the oldest ones
    max_files = 10
    if len(files) > max_files:
        to_delete = files[:len(files) - max_files]
        for f in to_delete:
            try:
                os.remove(f)
                print(f"🗑️ Deleted old file: {f.name}")
            except Exception as e:
                print(f"⚠️ Could not delete {f.name}: {e}")
    else:
        print(f"✅ Only {len(files)} files, nothing to delete.")



    print(f"Descargando datos reales desde NASA POWER para {LAT},{LON} ({start_date} → {end_date})...")
    r = requests.get(BASE_URL)
    r.raise_for_status()
    data = r.json()

    # === PROCESAR DATOS ===
    records = []
    dates = data["properties"]["parameter"]["T2M_MAX"].keys()

    for d in dates:
        record = {
            "date": pd.to_datetime(d).strftime("%Y-%m-%d"),
            "tmax": data["properties"]["parameter"]["T2M_MAX"].get(d),
            "tmin": data["properties"]["parameter"]["T2M_MIN"].get(d),
            "rh": data["properties"]["parameter"]["RH2M"].get(d),
            "wind": data["properties"]["parameter"]["WS2M"].get(d),
            "precip_mm": data["properties"]["parameter"]["PRECTOTCORR"].get(d)
        }
        records.append(record)

    df = pd.DataFrame(records)
    df = df.sort_values("date")

    # === GUARDAR CSV ===
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)

    print(f"\n✅ Archivo guardado correctamente en:\n{CSV_PATH}")
    print(f"Filas: {len(df)} ({df['date'].min()} → {df['date'].max()})")

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

    def predict_for_day(csv_path, date_str, history_years=15):
        df = pd.read_csv(csv_path, parse_dates=[DATE_COL])
        df["year"] = df[DATE_COL].dt.year
        target_date = pd.to_datetime(date_str)
        
        # 1) revisar si el día ya existe
        df_day = df[df[DATE_COL] == target_date]
        if not df_day.empty:
            row = df_day.iloc[0]
            temp = float(row[TEMP_COL]) if TEMP_COL in df.columns else \
                float((row["tmax"]+row["tmin"])/2) if "tmax" in df.columns and "tmin" in df.columns else None
            hum = float(row[HUM_COL]) if HUM_COL in df.columns else None
            precip = float(row[RAIN_COL]) if pd.notna(row[RAIN_COL]) else None
            clima_general = "rainy" if precip and precip >= RAIN_DAY_THRESHOLD else "dry"
            return {"date": str(target_date.date()), "temperature": temp, "humidity": hum, 
                    "precipitation_mm": precip, "generar_weather": clima_general, "source": "real"}
        
        # 2) calcular features usando los últimos 15 años del mismo día
        start_md = md_tuple(target_date)
        past_years = df[(df[DATE_COL].dt.month == start_md[0]) & (df[DATE_COL].dt.day == start_md[1])]
        feats = window_stats(past_years)
        
        # 3) entrenar modelo simple para predecir precipitación
        if len(past_years) >= 3:  # mínimo 3 años para entrenar
            X = np.arange(len(past_years)).reshape(-1,1)
            y = past_years[RAIN_COL].fillna(0.0).values
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            y_pred = float(model.predict(np.array([[len(past_years)]])))
        else:
            y_pred = feats["mean_mm"]  # fallback
        
        clima_general = "rainy" if y_pred >= RAIN_DAY_THRESHOLD else "dry"
        
        # temperatura y humedad promedio de los años previos
        temp = feats.get("tmean_mean") or (feats.get("tmax_mean") + feats.get("tmin_mean"))/2 if "tmax_mean" in feats else None
        hum = feats.get("rh_mean")
        
        return {"fecha": str(target_date.date()),"LAT": LAT, "LON":LON, "temperature": temp, "humidity": hum, 
                "precipitation_mm": y_pred, "general_weather": clima_general, "source": "prediction"}

    # =========================
    # EJEMPLO




    summary = predict_for_day(CSV_PATH, DATE)
    print(summary)

    return jsonify(summary)


if __name__ == '__main__':
    app.run(debug=True)
