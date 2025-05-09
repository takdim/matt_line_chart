from flask import Flask, render_template, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# Path to the uploaded CSV file
CSV_PATH = 'static/data/4g_measurement_daily.csv'

# Load the data
def load_data():
    try:
        df = pd.read_csv(CSV_PATH)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

# Determine sector based on the VBA logic
def determine_sector(cell_name):
    if cell_name[-4:] in ['VR11', 'VR12', 'VR13', 'VR14', 'VL11', 'VL12', 'VL13', 'VL14']:
        return 1
    elif cell_name[-4:] in ['VR21', 'VR22', 'VR23', 'VR24', 'VL21', 'VL22', 'VL23', 'VL24']:
        return 2
    elif cell_name[-4:] in ['VR31', 'VR32', 'VR33', 'VR34', 'VL31', 'VL32', 'VL33', 'VL34']:
        return 3
    elif cell_name[-2:].isdigit():
        return int(cell_name[-2:])
    return None

# Filter data for sector 1
def filter_sector_data(df, site_id=None):
    df['Sector'] = df['Cell Name'].apply(determine_sector)
    df = df.dropna(subset=['Sector'])

    # Ensure site_id is treated as a string
    df['site_id'] = df['site_id'].astype(str)
    if site_id:
        df = df[df['site_id'] == site_id]
    # Filter to only include sector 1
    df = df[df['Sector'] == 1]
    return df

@app.route('/')
def index():
    # Load data to get unique site_ids
    df = load_data()
    # Ensure site_id is treated as a string
    df['site_id'] = df['site_id'].astype(str)
    site_ids = df['site_id'].unique().tolist() if not df.empty else []
    return render_template('chart_site.html', site_ids=site_ids)

@app.route('/data')
def data():
    # Get site_id from query parameter
    site_id = request.args.get('site_id')

    # Load and filter data
    df = load_data()
    if df.empty:
        return jsonify({"error": "Data not found or could not be loaded."}), 404

    df = filter_sector_data(df, site_id)
    if df.empty:
        return jsonify({"error": "No data available for sector 1."}), 404

    # Aggregate data by date
    df_grouped = df.groupby('date').agg({'DL PRB Utilization _percent': 'mean'}).reset_index()
    data = {
        "date": df_grouped['date'].tolist(),
        "utilization": df_grouped['DL PRB Utilization _percent'].tolist()
    }

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)