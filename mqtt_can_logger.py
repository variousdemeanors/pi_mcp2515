import paho.mqtt.client as mqtt
from datetime import datetime

# --- Configuration ---
MQTT_BROKER = "localhost"  # The MQTT broker is running on the same Pi
MQTT_PORT = 1883
MQTT_TOPIC = "can/raw"
LOG_FILE = "can_log.txt"

# --- MQTT Callbacks ---

def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the MQTT broker."""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the topic once connected
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    """Callback function for when a message is received from the subscribed topic."""
    # Decode the message payload from bytes to a string
    payload = msg.payload.decode()

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # Format the log entry
    log_entry = f"{timestamp} | {msg.topic} | {payload}"

    # Print to console for real-time monitoring
    print(log_entry)

    # Write to the log file
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
    except IOError as e:
        print(f"Error writing to log file: {e}")

# --- Main Script ---

if __name__ == "__main__":
    print("Starting MQTT CAN Logger...")

    # Create an MQTT client instance
    client = mqtt.Client()

    # Assign the callback functions
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Connect to the broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Start a blocking loop that processes network traffic, dispatches callbacks,
        # and handles reconnecting. This is a simple, single-threaded approach.
        print(f"Subscribed to topic '{MQTT_TOPIC}'. Waiting for messages...")
        client.loop_forever()

    except ConnectionRefusedError:
        print(f"Connection to MQTT broker at {MQTT_BROKER}:{MQTT_PORT} was refused.")
        print("Please ensure the Mosquitto broker is running.")
    except KeyboardInterrupt:
        print("\nLogger stopped by user.")
        client.disconnect()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        client.disconnect()