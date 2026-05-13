#Database intergration with SQLite - works with r4-wifi-8
from flask import Flask, request, jsonify, Response
import sqlite3
import os
import csv
from datetime import datetime

def init_db():
    conn = sqlite3.connect("sensor_data.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            turbidity REAL,
            tds REAL,
            ec REAL,
            ph REAL,
            orp REAL
        )
    """)

    conn.commit()
    conn.close()

def insert_reading(data):
    conn = sqlite3.connect("sensor_data.db")
    c = conn.cursor()

    c.execute(""" 
        INSERT INTO readings (
            timestamp,
            temperature,
            turbidity,
            tds,
            ec,
            ph,
            orp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("timestamp"),
        data.get("temperature"),
        data.get("turbidity"),
        data.get("tds"),
        data.get("ec"),
        data.get("ph"),
        data.get("orp"),

    ))
    
    conn.commit()
    conn.close()

app = Flask(__name__)

# holds most recent reading
latest_data = {}

#includes: error catching if server stops etc. and connection status handling 
@app.route('/')
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Water Dashboard</title>
        <style>
            body {
                font-family: Arial;
                margin: 20px;
            }
            .card {
                padding: 10px;
                margin: 10px;
                border: 1px solid #ccc;
                width: 300px;
            }
        </style>
    </head>

    <body>
        <h1>Live Water Monitoring Dashboard</h1>
        <p>Status: <span id="status">Waiting for data...</span></p>

        <div class="card">Temperature: <span id="temperature">-</span></div>
        <div class="card">Turbidity: <span id="turbidity">-</span></div>
        <div class="card">TDS: <span id="tds">-</span></div>
        <div class="card">EC: <span id="ec">-</span></div>
        <div class="card">pH: <span id="ph">-</span></div>
        <div class="card">ORP: <span id="orp">-</span></div>
        <div class="card">Timestamp: <span id="timestamp">-</span></div>

        <script>
            async function updateData() {

                try {

                    const response = await fetch('/latest');
                    const data = await response.json();


                    document.getElementById("temperature").innerText = data.temperature;
                    document.getElementById("turbidity").innerText = data.turbidity;
                    document.getElementById("tds").innerText = data.tds;
                    document.getElementById("ec").innerText = data.ec;
                    document.getElementById("ph").innerText = data.ph;
                    document.getElementById("orp").innerText = data.orp;
                    document.getElementById("timestamp").innerText = data.timestamp;

                    document.getElementById("status").innerText = "Live";
                    

                } catch(error) {

                    document.getElementById("status").innerText = "Disconnected";

                    console.log(error);
                }
            }

            setInterval(updateData, 1000);
            updateData();
        </script>
    </body>
    </html>
    """

#Arduino sends sensor values
@app.route('/data', methods=['POST'])
def receive_data():
    global latest_data

    # gets and reads JSON from Arduino
    data = request.json or {}

    # store with server-side timestamp
    latest_data = {
        "timestamp": data.get("timestamp"),
        "temperature": data.get("temperature"),
        "turbidity": data.get("turbidity"),
        "tds": data.get("tds"),
        "ec": data.get("ec"),
        "ph": data.get("ph"),
        "orp": data.get("orp"),
    }

    insert_reading(latest_data)

    print("Stored in DB:", latest_data)

    return "Data stored", 200

#new endpoint browser will use
@app.route('/latest', methods=['GET'])
def get_latest():
    return jsonify(latest_data)

#endpoint for historical data log saved on RAM
@app.route('/history')
def history():
    conn = sqlite3.connect("sensor_data.db")
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, temperature, turbidity, tds, ec, ph, orp
        FROM readings
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = c.fetchall()
    conn.close()

    data = [
        {
            "timestamp": r[0],
            "temperature": r[1],
            "turbidity": r[2],
            "tds": r[3],
            "ec": r[4],
            "ph": r[5],
            "orp": r[6],
        }
        for r in rows
    ]

    return jsonify(data)

@app.route('/download')
def download_csv():

    conn = sqlite3.connect("sensor_data.db")
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, temperature, turbidity, tds, ec, ph, orp
        FROM readings
        ORDER BY id DESC
    """)

    rows = c.fetchall()
    conn.close()

    def generate():

        yield "timestamp,temperature,turbidity,tds,ec,ph,orp\n"

        for row in rows:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=sensor_data.csv"
        }
    )

init_db()

if __name__ == '__main__':
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

    
