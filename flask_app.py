from flask import Flask, request, render_template
import csv
import datetime
import seaborn as sns
import pandas as pd
import matplotlib
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
        return render_template('thank_you.html', name=name)
    
    
    return render_template('index.html')

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
                        
        return render_template('percentage_change.html', percent_changes=percent_changes, earliest_timestamps=earliest_timestamps, latest_timestamps=latest_timestamps, time_differences=time_differences)
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
            
            # Plotting
            sns.set_theme(style="whitegrid")
            plot = sns.lineplot(x='Timestamp', y='Percent Change', hue='Name', data=df, marker='o')
            plot.figure.set_size_inches(12, 6)  # Make the graph wider
            plot.set_xticklabels(plot.get_xticklabels(), rotation=45)  # Rotate datetime labels
            plot.set_ylabel('Percent Change', fontsize=8)  # Make y-axis label smaller
            plot.figure.savefig('static/plot.png', bbox_inches='tight')  # Ensure nothing is cut off
            plot.figure.clf()
            
        return render_template('plot.html', plot_file='static/plot.png')
    except Exception as e:
        return render_template('plot.html', error=str(e))
   

if __name__ == '__main__':
    app.run(debug=True)
