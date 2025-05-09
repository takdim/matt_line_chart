import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
df = pd.read_csv('static/data/4g_measurement_daily.csv')

df['CA Payload'] = pd.to_numeric(df['CA Payload'], errors='coerce')
df['DL PRB Utilization _percent'] = pd.to_numeric(df['DL PRB Utilization _percent'], errors='coerce')
df.fillna(0, inplace=True)

@app.route('/')
def index():
    site_ids = df['site_id'].dropna().unique().tolist()
    return render_template('chart.html', site_ids=site_ids)

@app.route('/get_data')
def get_data():
    site_id = request.args.get('site_id')
    if site_id:
        filtered = df[df['site_id'] == site_id].copy()
        filtered['date'] = pd.to_datetime(filtered['date']).dt.date.astype(str)

        return jsonify({
            'labels': filtered['date'].tolist(),  # tetap per baris
            'payload_values': filtered['CA Payload'].tolist(),
            'dl_prb_values': filtered['DL PRB Utilization _percent'].tolist()
        })

    return jsonify({'labels': [], 'payload_values': [], 'dl_prb_values': []})


@app.route('/get_site_ids')
def get_site_ids():
    site_ids = df['site_id'].dropna().drop_duplicates().tolist()
    return jsonify(site_ids)

if __name__ == '__main__':
    app.run(debug=True)
