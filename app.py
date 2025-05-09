from flask import Flask, render_template, request
import pandas as pd
import json

app = Flask(__name__)

# Load CSV sekali saja
df_all = pd.read_csv("static/data/4g_measurement_daily.csv")
df_all['date'] = pd.to_datetime(df_all['date'])

# Hilangkan duplikat site_id
unique_sites = sorted(df_all['site_id'].dropna().unique().tolist())

def extract_sector(cell_name):
    try:
        return int(str(cell_name)[-2:])
    except:
        return None

df_all['sector'] = df_all['Cell Name'].apply(extract_sector)

@app.route("/", methods=["GET"])
def index():
    selected_site = request.args.get("site_id")

    if selected_site:
        df = df_all[df_all['site_id'] == selected_site]
        pivot_df = df.pivot_table(index='date', columns='Cell Name', values='DL PRB Utilization _percent', aggfunc='mean')
        labels = pivot_df.index.strftime('%d-%b').tolist()

        import random
        def random_color():
            return f"rgba({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}, 1)"

        datasets = []
        for cell in pivot_df.columns:
            datasets.append({
                'label': cell,
                'data': pivot_df[cell].apply(lambda x: None if pd.isna(x) else x).tolist(),
                'borderColor': random_color(),
                'fill': False
            })

        chart_data = {
            'labels': labels,
            'datasets': datasets
        }
    else:
        chart_data = None

    return render_template("chart_site.html", site_ids=unique_sites, selected_site=selected_site, chart_data=json.dumps(chart_data) if chart_data else None)

if __name__ == "__main__":
    app.run(debug=True)
