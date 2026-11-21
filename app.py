
import json
import threading
import time
import webbrowser

from flask import Flask, jsonify, request
import paho.mqtt.client as mqtt

# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

# --------------------------------------------------
# MQTT CONFIGURATION
# --------------------------------------------------

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

MQTT_USERNAME = "smartgarden"
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"

STATUS_TOPIC = "smartgarden/status"
COMMAND_TOPIC = "smartgarden/command"

mqtt_connected = False

# --------------------------------------------------
# DEFAULT SENSOR AND DEVICE STATUS
# --------------------------------------------------

device_status = {
    "rain": False,
    "soilWet": False,
    "soilValue": 0,
    "humidity": 0,
    "temperature": 0,
    "redLed": False,
    "greenLed": False,
    "buzzer": False,
    "clotheslineAngle": 0,
    "wallAngle": 0,
    "motorState": "IDLE"
}

# --------------------------------------------------
# MQTT CALLBACK FUNCTIONS
# --------------------------------------------------

def on_connect(client, userdata, flags, rc):
    global mqtt_connected

    if rc == 0:
        mqtt_connected = True
        print("Connected to MQTT broker")

        client.subscribe(STATUS_TOPIC)
        print("Subscribed to:", STATUS_TOPIC)

    else:
        mqtt_connected = False
        print("MQTT connection failed. Code:", rc)


def on_disconnect(client, userdata, rc):
    global mqtt_connected

    mqtt_connected = False
    print("Disconnected from MQTT broker")


def on_message(client, userdata, message):
    global device_status

    try:
        received_data = message.payload.decode("utf-8")
        new_status = json.loads(received_data)

        device_status.update(new_status)

        print("Received device status:", new_status)

    except Exception as error:
        print("Error reading MQTT message:", error)


# --------------------------------------------------
# CREATE MQTT CLIENT
# --------------------------------------------------

mqtt_client = mqtt.Client()

mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message

# --------------------------------------------------
# CONNECT TO MQTT BROKER
# --------------------------------------------------

def start_mqtt():

    try:
        mqtt_client.connect(
            MQTT_HOST,
            MQTT_PORT,
            60
        )

        mqtt_client.loop_start()

    except Exception as error:
        print("Could not connect to MQTT broker:", error)


# --------------------------------------------------
# DASHBOARD HTML PAGE
# --------------------------------------------------

PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Smart Rain Protection Dashboard</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #f1f4f8;
            color: #222;
        }

        .container {
            max-width: 1200px;
            margin: auto;
        }

        header {
            background: #263b57;
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
        }

        header h1 {
            margin: 0 0 10px;
        }

        .connection {
            margin-top: 12px;
            font-weight: bold;
        }

        .section-title {
            margin-top: 25px;
            margin-bottom: 15px;
        }

        .grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .card h3 {
            margin-top: 0;
            color: #52657c;
            font-size: 16px;
        }

        .value {
            font-size: 25px;
            font-weight: bold;
            margin-top: 12px;
        }

        .controls {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
        }

        button {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover {
            opacity: 0.85;
        }

        button:disabled {
            background: #999;
            cursor: not-allowed;
        }

        .blue {
            background: #2878c7;
        }

        .green {
            background: #218838;
        }

        .orange {
            background: #e58a19;
        }

        .red {
            background: #c83b3b;
        }

        .message {
            margin-top: 15px;
            padding: 12px;
            background: white;
            border-radius: 8px;
            min-height: 42px;
        }

        footer {
            text-align: center;
            margin-top: 30px;
            color: #777;
        }

    </style>

</head>

<body>

<div class="container">

    <header>

        <h1>Smart Rain Protection Clothesline</h1>

        <p>IoT-Based Automatic Rain Protection System</p>

        <div class="connection">
            MQTT Connection:
            <span id="mqttConnection">Checking...</span>
        </div>

    </header>


    <h2 class="section-title">Sensor Readings</h2>

    <div class="grid">

        <div class="card">
            <h3>Rain Sensor</h3>
            <div class="value" id="rain">--</div>
        </div>

        <div class="card">
            <h3>Soil Moisture</h3>
            <div class="value" id="soil">--</div>
        </div>

        <div class="card">
            <h3>Temperature</h3>
            <div class="value" id="temperature">--</div>
        </div>

        <div class="card">
            <h3>Humidity</h3>
            <div class="value" id="humidity">--</div>
        </div>

    </div>


    <h2 class="section-title">Device Status</h2>

    <div class="grid">

        <div class="card">
            <h3>Red LED</h3>
            <div class="value" id="redLed">--</div>
        </div>

        <div class="card">
            <h3>Green LED</h3>
            <div class="value" id="greenLed">--</div>
        </div>

        <div class="card">
            <h3>Buzzer</h3>
            <div class="value" id="buzzer">--</div>
        </div>

        <div class="card">
            <h3>Motor State</h3>
            <div class="value" id="motorState">--</div>
        </div>

        <div class="card">
            <h3>Clothesline Position</h3>
            <div class="value" id="clothesline">--</div>
        </div>

        <div class="card">
            <h3>Protective Wall Position</h3>
            <div class="value" id="wall">--</div>
        </div>

    </div>


    <h2 class="section-title">Manual Controls</h2>

    <div class="controls">

        <button class="blue"
                onclick="sendCommand('CLOSE_CLOTHESLINE')">
            Close Clothesline
        </button>

        <button class="green"
                onclick="sendCommand('EXPAND_CLOTHESLINE')">
            Expand Clothesline
        </button>

        <button class="orange"
                onclick="sendCommand('RAISE_WALL')">
            Raise Wall
        </button>

        <button class="red"
                onclick="sendCommand('LOWER_WALL')">
            Lower Wall
        </button>

    </div>


    <div class="message" id="message">
        Dashboard is ready.
    </div>


    <footer>
        Smart Rain Protection Clothesline | Raspberry Pi 4
    </footer>

</div>


<script>

    function displayBoolean(value) {

        if (value === true || value === 1 || value === "true") {
            return "ON";
        }

        return "OFF";
    }


    async function updateDashboard() {

        try {

            const response = await fetch("/api/status");

            const data = await response.json();

            document.getElementById("mqttConnection").textContent =
                data.mqttConnected ? "Connected" : "Disconnected";

            document.getElementById("rain").textContent =
                data.rain ? "Rain Detected" : "No Rain";

            document.getElementById("soil").textContent =
                (data.soilWet ? "Wet" : "Dry") +
                " (" + data.soilValue + ")";

            document.getElementById("temperature").textContent =
                data.temperature + " °C";

            document.getElementById("humidity").textContent =
                data.humidity + " %";

            document.getElementById("redLed").textContent =
                displayBoolean(data.redLed);

            document.getElementById("greenLed").textContent =
                displayBoolean(data.greenLed);

            document.getElementById("buzzer").textContent =
                displayBoolean(data.buzzer);

            document.getElementById("motorState").textContent =
                data.motorState;

            document.getElementById("clothesline").textContent =
                data.clotheslineAngle + "°";

            document.getElementById("wall").textContent =
                data.wallAngle + "°";

        }

        catch (error) {

            document.getElementById("message").textContent =
                "Unable to update dashboard.";

            console.log(error);

        }

    }


    async function sendCommand(command) {

        const message = document.getElementById("message");

        message.textContent = "Sending command: " + command;

        try {

            const response = await fetch("/command", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    command: command
                })

            });

            const result = await response.json();

            message.textContent = result.message;

        }

        catch (error) {

            message.textContent =
                "Error sending command.";

            console.log(error);

        }

    }


    updateDashboard();

    setInterval(updateDashboard, 2000);

</script>

</body>
</html>
"""


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return PAGE


# --------------------------------------------------
# SEND STATUS TO DASHBOARD
# --------------------------------------------------

@app.route("/api/status")
def get_status():

    result = device_status.copy()

    result["mqttConnected"] = mqtt_connected

    return jsonify(result)


# --------------------------------------------------
# MANUAL CONTROL COMMANDS
# --------------------------------------------------

@app.route("/command", methods=["POST"])
def send_command():

    if not mqtt_connected:
        return jsonify({
            "success": False,
            "message": "MQTT broker is disconnected."
        }), 503

    data = request.get_json(silent=True) or {}

    command = data.get("command")

    allowed_commands = [
        "CLOSE_CLOTHESLINE",
        "EXPAND_CLOTHESLINE",
        "RAISE_WALL",
        "LOWER_WALL"
    ]

    if command not in allowed_commands:
        return jsonify({
            "success": False,
            "message": "Invalid command."
        }), 400

    try:

        result = mqtt_client.publish(
            COMMAND_TOPIC,
            command,
            qos=0
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:

            print("Command sent:", command)

            return jsonify({
                "success": True,
                "message": "Command sent: " + command
            })

        return jsonify({
            "success": False,
            "message": "Unable to publish MQTT command."
        }), 500

    except Exception as error:

        print("Command error:", error)

        return jsonify({
            "success": False,
            "message": "Error sending command."
        }), 500


# --------------------------------------------------
# AUTOMATICALLY OPEN BROWSER
# --------------------------------------------------

def open_browser():

    webbrowser.open("http://127.0.0.1:5000")


# --------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":

    print("--------------------------------------")
    print("Smart Rain Protection Dashboard")
    print("--------------------------------------")

    start_mqtt()

    threading.Timer(
        2.0,
        open_browser
    ).start()

    print("Starting Flask dashboard...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
