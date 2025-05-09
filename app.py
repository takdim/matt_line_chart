from flask import Flask, render_template, jsonify, request
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import numpy as np

# Custom JSON encoder to handle NaN/Infinity values
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

# Path to the uploaded CSV file - allow setting via environment variable
CSV_PATH = os.environ.get('CSV_PATH', 'static/data/4g_measurement_dbh1.csv')

# Alternative paths to check if main path doesn't exist
ALTERNATIVE_PATHS = [
    '4g_measurement_daily.csv',
    'data/4g_measurement_daily.csv',
    '../4g_measurement_daily.csv',
    '../data/4g_measurement_daily.csv'
]

# Load the data
def load_data():
    global CSV_PATH
    
    try:
        # Check if file exists at primary path
        if not os.path.exists(CSV_PATH):
            print(f"Warning: CSV file not found at {CSV_PATH}")
            
            # Try alternative paths
            for alt_path in ALTERNATIVE_PATHS:
                if os.path.exists(alt_path):
                    print(f"Found CSV at alternative path: {alt_path}")
                    CSV_PATH = alt_path
                    break
            else:
                print("CSV file not found in any location")
                return pd.DataFrame()
            
        # Read the CSV file with explicit error handling
        df = pd.read_csv(CSV_PATH, low_memory=False)
        print(f"Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
        
        # Print column names to help debug
        print(f"CSV columns: {df.columns.tolist()}")
        
        # Handle possible data issues or different column names
        
        # Check for date column with different names
        date_columns = ['date', 'Date', 'DATE', 'datetime', 'Datetime', 'DATETIME']
        found_date_col = None
        for col in date_columns:
            if col in df.columns:
                found_date_col = col
                break
                
        if found_date_col:
            try:
                df.rename(columns={found_date_col: 'date'}, inplace=True)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                # Check for NaT values after conversion
                nat_count = df['date'].isna().sum()
                if nat_count > 0:
                    print(f"Warning: {nat_count} rows have invalid dates")
                    # Remove rows with invalid dates
                    df = df.dropna(subset=['date'])
            except Exception as e:
                print(f"Error converting dates: {e}")
        else:
            print("Warning: No date column found")
            
        # Map column names based on possible variations
        column_mapping = {
            'DL PRB Utilization (%)': 'DL PRB Utilization _percent',
            'DL PRB Utilization': 'DL PRB Utilization _percent',
            'PRB Utilization (%)': 'DL PRB Utilization _percent',
            'PRB Utilization': 'DL PRB Utilization _percent',
            'Downlink Carrier Frequency': 'Downlink Center Carrier Frequency',
            'Carrier Frequency': 'Downlink Center Carrier Frequency',
            'Cell_Name': 'Cell Name',
            'CellName': 'Cell Name',
            'Site ID': 'site_id',
            'SiteID': 'site_id'
        }
        
        # Apply column mapping for columns that exist
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['DL PRB Utilization _percent', 'Downlink Center Carrier Frequency', 'Cell Name', 'site_id']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Warning: Missing required columns: {missing_cols}")
        
        # Ensure correct data types
        if 'DL PRB Utilization _percent' in df.columns:
            df['DL PRB Utilization _percent'] = pd.to_numeric(df['DL PRB Utilization _percent'], errors='coerce')
        
        if 'Downlink Center Carrier Frequency' in df.columns:
            df['Downlink Center Carrier Frequency'] = pd.to_numeric(df['Downlink Center Carrier Frequency'], errors='coerce')
            
        # Convert site_id to string
        if 'site_id' in df.columns:
            df['site_id'] = df['site_id'].astype(str)
            
        # Fill nulls with appropriate values
        df = df.fillna({
            'DL PRB Utilization _percent': 0,
            'Downlink Center Carrier Frequency': 0
        })
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Determine sector based on the VBA logic
def determine_sector(cell_name):
    if isinstance(cell_name, str):
        if cell_name[-4:] in ['VR11', 'VR12', 'VR13', 'VR14', 'VL11', 'VL12', 'VL13', 'VL14']:
            return 1
        elif cell_name[-4:] in ['VR21', 'VR22', 'VR23', 'VR24', 'VL21', 'VL22', 'VL23', 'VL24']:
            return 2
        elif cell_name[-4:] in ['VR31', 'VR32', 'VR33', 'VR34', 'VL31', 'VL32', 'VL33', 'VL34']:
            return 3
        elif len(cell_name) >= 2 and cell_name[-2:].isdigit():
            return int(cell_name[-2:])
    return None

# Determine band based on carrier frequency (exactly as in VBA)
def determine_band(frequency):
    if frequency == 930:
        return 'L900'
    elif frequency == 1870:
        return 'L1800'
    elif frequency == 2160:
        return 'L2100'
    elif frequency == 2310:
        return 'L2300 F1'
    elif frequency == 2329.8:
        return 'L2300 F2'
    elif frequency == 2344.2:
        return 'L2300 F3'
    return 'Unknown Band'

# Process data using the same logic as in VBA code
def process_prb_data(site_ids, reference_date=None):
    df = load_data()
    if df.empty:
        return pd.DataFrame()

    # Use today if no reference date is provided
    if reference_date is None:
        reference_date = datetime.now().date()
    else:
        reference_date = pd.to_datetime(reference_date).date()
    
    # Filter data for the last 3 days as in VBA (including reference date)
    start_date = reference_date - timedelta(days=2)
    
    # Prepare the dataframe with calculated fields
    df['sector'] = df['Cell Name'].apply(determine_sector)
    df['band'] = df['Downlink Center Carrier Frequency'].apply(determine_band)
    
    # Filter by site_ids and date range
    df = df[df['site_id'].isin(site_ids)]
    if 'date' in df.columns:
        df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= reference_date)]
    
    # Create the result DataFrame with the same structure as in VBA
    result = []
    
    for site_id in site_ids:
        site_data = df[df['site_id'] == site_id]
        
        for sector_num in range(1, 4):  # Sectors 1, 2, 3
            sector_data = site_data[site_data['sector'] == sector_num]
            
            if not sector_data.empty:
                # Calculate band combination (count of distinct bands)
                bands = sector_data['band'].unique()
                band_combination = len(bands)
                
                # Calculate average PRB utilization for each band
                l900 = sector_data[sector_data['band'] == 'L900']['DL PRB Utilization _percent'].mean()
                l1800 = sector_data[sector_data['band'] == 'L1800']['DL PRB Utilization _percent'].mean()
                l2100 = sector_data[sector_data['band'] == 'L2100']['DL PRB Utilization _percent'].mean()
                l2300_f1 = sector_data[sector_data['band'] == 'L2300 F1']['DL PRB Utilization _percent'].mean()
                l2300_f2 = sector_data[sector_data['band'] == 'L2300 F2']['DL PRB Utilization _percent'].mean()
                l2300_f3 = sector_data[sector_data['band'] == 'L2300 F3']['DL PRB Utilization _percent'].mean()
                
                # Convert NaN values to None (which will be converted to null in JSON)
                l900 = None if pd.isna(l900) else l900
                l1800 = None if pd.isna(l1800) else l1800
                l2100 = None if pd.isna(l2100) else l2100
                l2300_f1 = None if pd.isna(l2300_f1) else l2300_f1
                l2300_f2 = None if pd.isna(l2300_f2) else l2300_f2 
                l2300_f3 = None if pd.isna(l2300_f3) else l2300_f3
                
                # Add to results
                result.append({
                    'site_id': site_id,
                    'sector': sector_num,
                    'band_combination': band_combination,
                    'L900': l900,
                    'L1800': l1800,
                    'L2100': l2100,
                    'L2300_F1': l2300_f1,
                    'L2300_F2': l2300_f2,
                    'L2300_F3': l2300_f3
                })
    
    return result

# Get cell names for a specific site
def get_cell_names_for_site(site_id):
    df = load_data()
    if df.empty:
        return []
    
    # Filter by site_id and get unique cell names
    site_data = df[df['site_id'] == site_id]
    cell_names = site_data['Cell Name'].unique().tolist() if 'Cell Name' in site_data.columns else []
    
    return sorted(cell_names)

# Get historical PRB utilization data for a specific cell
def get_historical_cell_data(site_id, cell_name, days=7):
    df = load_data()
    if df.empty:
        return {}
    
    # Convert days to integer
    days = int(days)
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Filter data
    filtered_df = df[(df['site_id'] == site_id) & 
                      (df['Cell Name'] == cell_name) & 
                      (df['date'].dt.date >= start_date) & 
                      (df['date'].dt.date <= end_date)]
    
    if filtered_df.empty:
        return {'dates': [], 'bands': {}}
    
    # Add band column if not present
    if 'band' not in filtered_df.columns:
        filtered_df['band'] = filtered_df['Downlink Center Carrier Frequency'].apply(determine_band)
    
    # Get unique dates and sort them
    dates = sorted(filtered_df['date'].dt.date.unique())
    date_strings = [d.strftime('%Y-%m-%d') for d in dates]
    
    # Initialize result structure
    bands_data = {
        'L900': [0] * len(dates),
        'L1800': [0] * len(dates),
        'L2100': [0] * len(dates),
        'L2300 F1': [0] * len(dates),
        'L2300 F2': [0] * len(dates),
        'L2300 F3': [0] * len(dates)
    }
    
    # Group by date and band, calculate mean PRB utilization
    for i, date in enumerate(dates):
        day_data = filtered_df[filtered_df['date'].dt.date == date]
        
        for band in bands_data.keys():
            band_data = day_data[day_data['band'] == band]
            if not band_data.empty:
                # Convert percentage values to decimal for consistency (0-1 range)
                prb_util = band_data['DL PRB Utilization _percent'].mean() / 100.0
                # Handle NaN values
                bands_data[band][i] = 0 if pd.isna(prb_util) else prb_util
    
    return {
        'dates': date_strings,
        'bands': bands_data
    }

# Routes
@app.route('/')
def index():
    df = load_data()
    site_ids = []
    
    if not df.empty and 'site_id' in df.columns:
        site_ids = sorted(df['site_id'].unique().tolist())
    
    return render_template('chart_site.html', site_ids=site_ids)

@app.route('/data')
def get_data():
    site_ids = request.args.getlist('site_ids[]')
    reference_date = request.args.get('reference_date')
    
    if not site_ids:
        return jsonify([])
    
    result = process_prb_data(site_ids, reference_date)
    return jsonify(result)

@app.route('/cell_names')
def get_cell_names():
    site_id = request.args.get('site_id')
    
    if not site_id:
        return jsonify({'error': 'No site_id provided', 'cell_names': []})
    
    cell_names = get_cell_names_for_site(site_id)
    return jsonify({'cell_names': cell_names})

@app.route('/historical_cell_data')
def historical_cell_data():
    site_id = request.args.get('site_id')
    cell_name = request.args.get('cell_name')
    days = request.args.get('days', 7)
    
    if not site_id or not cell_name:
        return jsonify({'error': 'Missing required parameters (site_id, cell_name)'})
    
    try:
        data = get_historical_cell_data(site_id, cell_name, days)
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)