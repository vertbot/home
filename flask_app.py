from flask import Flask, request, render_template
import csv
import datetime
import seaborn as sns
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

CSV_FILE = 'weights.csv'

# Ensure the CSV file exists and has headers
with open(CSV_FILE, 'a', newline='') as f:
    writer = csv.writer(f)
    if f.tell() == 0:  # If file is empty
        writer.writerow(['Name', 'Weight', 'Timestamp'])

def plot():
    with open(CSV_FILE, 'r') as f:
        reader = list(csv.reader(f))
        if len(reader) < 3:  # Header + at least 2 records
            return None
        
        data = []
        for row in reader[1:]:  # Skip header
            name, weight, timestamp = row
            weight = float(weight)
            timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            data.append([name, weight, timestamp])
        
        df = pd.DataFrame(data, columns=['Name', 'Weight', 'Timestamp'])
        
        # Calculate percentage change
        df['PercentChange'] = df.groupby('Name')['Weight'].pct_change() * 100
        
        # Plotting
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='Timestamp', y='PercentChange', hue='Name', marker='o')
        plt.title('Percentage Change in Weight Over Time')
        plt.xlabel('Timestamp')
        plt.ylabel('Percentage Change')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save plot to a file
        plot_file = 'static/plot.png'
        plt.savefig(plot_file)
        plt.close()
        return plot_file

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
    
    # Read unique names from the CSV file
    unique_names = set()
    with open(CSV_FILE, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            unique_names.add(row[0])
    
    return render_template('index.html', unique_names=unique_names)

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
                
        plot_file = plot()
        
        return render_template('percentage_change.html', percent_changes=percent_changes, earliest_timestamps=earliest_timestamps, latest_timestamps=latest_timestamps, time_differences=time_differences, plot_file=plot_file)
    except Exception as e:
        return render_template('percentage_change.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)
