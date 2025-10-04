from flask import Flask, request, jsonify, render_template
import requests
from datetime import date, datetime
import re

app = Flask(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Rota inicial
@app.route("/", methods=["GET"])
def home():
    return "<h2>API de Previsão do Tempo</h2><p>Use <a href='/interface'>Interface</a></p>"

# Rota da interface
@app.route("/interface")
def interface():
    return render_template("interface.html")

# Rota da API
@app.route("/clima", methods=["GET"])
def clima():
    cidade = request.args.get("cidade")
    data_input = request.args.get("data")
    if not cidade:
        return jsonify({"erro": 'Parâmetro "cidade" é obrigatório.'}), 400

    # Validar data
    if data_input:
        try:
            data_formatada = datetime.strptime(data_input, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"erro": "Data inválida"}), 400
    else:
        data_formatada = date.today()

    # Geocodificação
    try:
        resp = requests.get(GEOCODE_URL, params={"name": cidade, "count": 1, "format": "json"}, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results")
        if not results:
            return jsonify({"erro": f'Cidade "{cidade}" não encontrada.'}), 404
        geo = results[0]
    except requests.Timeout:
        return jsonify({"erro": "Tempo de resposta da geocodificação esgotou. Tente novamente mais tarde."}), 504
    except Exception as e:
        return jsonify({"erro": "Erro na geocodificação", "detalhes": str(e)}), 500

    # Previsão
    try:
        params = {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "hourly": "relativehumidity_2m",
            "start_date": data_formatada.isoformat(),
            "end_date": data_formatada.isoformat(),
            "timezone": geo.get("timezone", "auto")
        }
        resp = requests.get(FORECAST_URL, params=params, timeout=30)  # Timeout maior
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return jsonify({"erro": "Tempo de resposta da previsão esgotou. Tente novamente mais tarde."}), 504
    except Exception as e:
        return jsonify({"erro": "Erro na previsão", "detalhes": str(e)}), 500

    daily = data.get("daily", {})
    idx = 0
    temp_max = daily["temperature_2m_max"][idx]
    temp_min = daily["temperature_2m_min"][idx]
    precip_prob = daily.get("precipitation_probability_max", [None])[idx]

    # Texto para exibir na interface
    texto = (
        f"Previsão para {geo.get('name')}, {geo.get('country')} em {data_formatada.isoformat()}:\n"
        f"- Temperatura máxima: {temp_max}°C\n"
        f"- Temperatura mínima: {temp_min}°C\n"
        f"- Chance de chuva: {precip_prob}%"
    )

    return jsonify({
        "cidade_busca": cidade,
        "cidade_encontrada": f"{geo.get('name')}, {geo.get('country')}",
        "data": data_formatada.isoformat(),
        "temperatura_maxima_c": temp_max,
        "temperatura_minima_c": temp_min,
        "chance_de_chuva_percent": precip_prob,
        "texto": texto
    })

# Rodar o Flask
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
