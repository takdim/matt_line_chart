from flask import Flask, render_template
import pandas as pd
import numpy as np
import json

app = Flask(__name__)

@app.route("/")
def chart():
    # Baca data
    df = pd.read_csv("static/data/4g_measurement_daily.csv")

    # Ubah kolom tanggal
    df['date'] = pd.to_datetime(df['date'])

    # Hitung sector dari Cell Name (ambil 2 karakter terakhir yang bisa dikonversi ke int)
    def extract_sector(cell_name):
        try:
            return int(str(cell_name)[-2:])
        except:
            return None

    df['sector'] = df['Cell Name'].apply(extract_sector)

    # Filter untuk sector tertentu (misalnya 1)
    df = df[df['sector'] == 1]

    # Buat kolom "band" dari 'Downlink Center Carrier Frequency'
    def map_band(freq):
        freq_map = {
            930: 'LTE900',
            1870: 'LTE1800',
            2160: 'LTE2100',
            2310: 'LTE2300 F1',
            2329.8: 'LTE2300 F2',
            2344.2: 'LTE2300 F3'
        }
        return freq_map.get(freq, 'Unknown Band')

    df['band'] = df['Downlink Center Carrier Frequency'].apply(map_band)

    # Pivot table: date sebagai index, band sebagai columns
    pivot_df = df.pivot_table(index='date', columns='band', values='DL PRB Utilization _percent', aggfunc='mean')

    # Siapkan data untuk Chart.js
    labels = pivot_df.index.strftime('%d-%b').tolist()
    datasets = []

    colors = {
        'LTE900': 'rgba(128,0,128,1)',
        'LTE1800': 'rgba(75,0,130,1)',
        'LTE2100': 'rgba(0,0,255,1)',
        'LTE2300 F1': 'rgba(255,165,0,1)',
        'LTE2300 F2': 'rgba(255,215,0,1)',
        'LTE2300 F3': 'rgba(255,20,147,1)'
    }

    for band in pivot_df.columns:
        datasets.append({
            'label': band,
            'data': pivot_df[band].apply(lambda x: None if pd.isna(x) else x).tolist(),
            'borderColor': colors.get(band, 'rgba(100,100,100,1)'),
            'fill': False
        })

    chart_data = {
        'labels': labels,
        'datasets': datasets
    }

    return render_template("chart.html", chart_data=json.dumps(chart_data))

if __name__ == "__main__":
    app.run(debug=True)
