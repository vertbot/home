from flask import Flask, request, render_template
import csv
import datetime
import seaborn as sns
import pandas as pd
import matplotlib
import io
import base64
from user_agents import parse
import requests
matplotlib.use('Agg')


app = Flask(__name__)

CSV_FILE = 'weights.csv'

# Ensure the CSV file exists and has headers
with open(CSV_FILE, 'a', newline='') as f:
    writer = csv.writer(f)
    if f.tell() == 0:  # If file is empty
        writer.writerow(['Name', 'Weight', 'Timestamp'])


 
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        weight = float(request.form['weight'])
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([name, weight, timestamp])
        return render_template('thank_you.html', name=name, weight=weight, timestamp=timestamp)
    
    return render_template('index.html')

@app.route('/user_info', methods=['GET'])
def user_info():
    user_agent = request.headers.get('User-Agent')
    user_agent_parsed = parse(user_agent)
    
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address:
        ip_address = ip_address.split(',')[0].strip()  # Get the first IP if there are multiple
    
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}')
        location_data = response.json()
        location = f"{location_data['city']}, {location_data['regionName']}, {location_data['country']}"
    except Exception as e:
        location = f"Could not determine location: {str(e)}"
    
    browser = user_agent_parsed.browser.family
    browser_version = user_agent_parsed.browser.version_string
    os = user_agent_parsed.os.family
    os_version = user_agent_parsed.os.version_string
    device = user_agent_parsed.device.family
    device_brand = user_agent_parsed.device.brand
    device_model = user_agent_parsed.device.model
    
    # Store information in user_info.log
    with open('user_info.log', 'a') as log_file:
        log_file.write(f"{ip_address},{location},{browser} {browser_version},{os} {os_version},{device} {device_brand} {device_model},{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return render_template('user_info.html', ip_address=ip_address, location=location, browser=browser, browser_version=browser_version, os=os, os_version=os_version, device=device, device_brand=device_brand, device_model=device_model)


@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    name = request.form['name']
    weight = float(request.form['weight'])
    timestamp = request.form['timestamp']
    
    with open(CSV_FILE, 'r') as f:
        rows = list(csv.reader(f))
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        for row in rows:
            if row != [name, str(weight), timestamp]:
                writer.writerow(row)
    
    return render_template('entry_deleted.html', name=name, weight=weight, timestamp=timestamp)



@app.route('/percentage_change', methods=['GET'])
def percentage_change():
    try:
        with open(CSV_FILE, 'r') as f:
            reader = list(csv.reader(f))
            if len(reader) < 3:  # Header + at least 2 records
                return render_template('percentage_change.html', error="Not enough data to calculate percentage change.")
            
            data = {}
            timestamps = {}
            for row in reader[1:]:  # Skip header
                name, weight, timestamp = row
                weight = float(weight)
                if name not in data:
                    data[name] = []
                    timestamps[name] = []
                data[name].append(weight)
                timestamps[name].append(timestamp)
            
            percent_changes = {}
            earliest_timestamps = {}
            latest_timestamps = {}
            time_differences = {}
            for name, weights in data.items():
                if len(weights) < 2:
                    continue
                oldest_weight = weights[0]
                latest_weight = weights[-1]
                if oldest_weight == 0:
                    percent_changes[name] = "Previous weight is zero, cannot calculate percentage change."
                else:
                    percent_change = ((latest_weight - oldest_weight) / oldest_weight) * 100
                    percent_changes[name] = f"{percent_change:.2f}%"
                earliest_timestamps[name] = timestamps[name][0]
                latest_timestamps[name] = timestamps[name][-1]
                
                # Calculate time difference
                time_format = '%Y-%m-%d %H:%M:%S'
                oldest_time = datetime.datetime.strptime(earliest_timestamps[name], time_format)
                latest_time = datetime.datetime.strptime(latest_timestamps[name], time_format)
                time_difference = latest_time - oldest_time
                time_differences[name] = time_difference
            
            # Sort by percent change (lowest to highest)
            sorted_percent_changes = dict(sorted(percent_changes.items(), key=lambda item: float(item[1].strip('%')) if isinstance(item[1], str) and item[1].endswith('%') else float('inf')))
                        
        return render_template('percentage_change.html', percent_changes=sorted_percent_changes, earliest_timestamps=earliest_timestamps, latest_timestamps=latest_timestamps, time_differences=time_differences)
    except Exception as e:
        return render_template('percentage_change.html', error=str(e))

@app.route('/plot', methods=['GET'])
def plot():
    try:
        with open(CSV_FILE, 'r') as f:
            reader = list(csv.reader(f))
            if len(reader) < 3:  # Header + at least 2 records
                return render_template('plot.html', error="Not enough data to create plot.")
            
            data = {}
            for row in reader[1:]:  # Skip header
                name, weight, timestamp = row
                weight = float(weight)
                if name not in data:
                    data[name] = []
                data[name].append((timestamp, weight))
            
            # Create a DataFrame for plotting
            plot_data = []
            for name, weights in data.items():
                weights.sort()  # Sort by timestamp
                for i in range(1, len(weights)):
                    prev_weight = weights[i-1][1]
                    curr_weight = weights[i][1]
                    if prev_weight == 0:
                        percent_change = 0
                    else:
                        percent_change = ((curr_weight - prev_weight) / prev_weight) * 100
                    plot_data.append([name, weights[i][0], percent_change])
            
            df = pd.DataFrame(plot_data, columns=['Name', 'Timestamp', 'Percent Change'])
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])  # Convert 'Timestamp' to datetime
            
            # Plotting
            sns.set_theme(style="whitegrid")
            plot = sns.lineplot(x='Timestamp', y='Percent Change', hue='Name', data=df, marker='o')
            plot.figure.set_size_inches(12, 6)  # Make the graph wider
            import matplotlib.dates as mdates
            plot.xaxis.set_major_locator(mdates.AutoDateLocator())
            plot.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
            plot.tick_params(axis='x', rotation=45)  # Rotate datetime labels
            plot.set_ylabel('Percent Change', fontsize=8)  # Make y-axis label smaller
            
            # Save plot to a bytes buffer
            buf = io.BytesIO()
            plot.figure.savefig(buf, format='png', bbox_inches='tight')  # Ensure nothing is cut off
            buf.seek(0)
            plot.figure.clf()
            
            plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
            
        return render_template('plot.html', plot_data=plot_data)
    except Exception as e:
        return render_template('plot.html', error=str(e))

  

if __name__ == '__main__':
    app.run(debug=True)
