import meterbus
import asyncio
import logging
import json
import serial
import time
import random
import os
import sys
from paho.mqtt import client as mqtt

from const import DOMAIN, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC, CONF_DEVICE, CONF_BAUDRATE, CONF_METER_ADDRESS, CONF_POLLING_RATE, CONF_MAX_TIMEOUT
from decode import decode_abb_telegram1, decode_abb_telegram2

# Configure logging
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# MQTT Client Setup
client_id = f'abb_b23_mbus-{random.randint(0, 1000)}'
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)

# Global variables for health checks
last_successful_read = 0
mqtt_connected = False

def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_connected
    if rc == 0:
        _LOGGER.info("Connected to MQTT Broker!")
        mqtt_connected = True
    else:
        _LOGGER.error(f"Failed to connect to MQTT Broker. Return code: {rc}")
        mqtt_connected = False

def on_disconnect(client, userdata, rc, properties=None):
    global mqtt_connected
    _LOGGER.warning("Disconnected from MQTT Broker")
    mqtt_connected = False

client.on_connect = on_connect
client.on_disconnect = on_disconnect

# Connect to MQTT Broker
def connect_mqtt():
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        _LOGGER.error(f"Error connecting to MQTT broker: {e}")


async def mqtt_publish_sensor_data(mqtt_client, topic, payload):
    """Publish data to MQTT."""
    global mqtt_connected
    if not mqtt_connected:
        _LOGGER.warning("MQTT not connected. Attempting to reconnect...")
        connect_mqtt()
        await asyncio.sleep(5)  # Wait for connection attempt
    
    if mqtt_connected:
        _LOGGER.info(f"Publishing sensor data to MQTT topic {topic}")
        mqtt_client.publish(topic, json.dumps(payload), retain=True)
    else:
        _LOGGER.error("Failed to publish data: MQTT not connected")


async def mbus_fetch_data(device, baudrate, meter_address):
    """Fetch data from the meter using pyMeterBus."""
    global last_successful_read
    try:
        ibt = meterbus.inter_byte_timeout(baudrate)

        """Establish M-Bus connection"""
        mbus = serial.serial_for_url(device, baudrate, 8, 'E', 1, inter_byte_timeout=ibt, timeout=1)

        """Send REQ_UD telegram to the meter"""
        req_bytes = bytearray([0x10, 0x5B, 0x01, 0x5C, 0x16])
        meterbus.send_request_frame(mbus, meter_address, req_bytes)
        _LOGGER.debug(f"Sent REQ_UD telegram to the meter")

        """Wait for the meter to respond"""
        time.sleep(1)
        
        """Receive RES_UD response from the meter"""
        telegram1 = decode_abb_telegram1(meterbus.recv_frame(mbus, meterbus.FRAME_DATA_LENGTH))
        _LOGGER.debug(f"Received telegram1 from meter: {telegram1}")

        """Send REQ_UD2 telegram to the meter"""
        req_bytes = bytearray([0x10, 0x7B, 0x01, 0x7C, 0x16])
        meterbus.send_request_frame(mbus, meter_address, req_bytes)
        _LOGGER.debug(f"Sent REQ_UD2 telegram to the meter: {req_bytes}") 
        
        """Wait for the meter to respond"""
        time.sleep(2)

        """Receive RES_UD response from the meter"""
        telegram2 = decode_abb_telegram2(meterbus.recv_frame(mbus, meterbus.FRAME_DATA_LENGTH))
        _LOGGER.debug(f"Received telegram2 from meter: {telegram2}")

        """Merge the telegrams"""
        data = dict(telegram1, **telegram2)

        last_successful_read = time.time()

        return data
    except Exception as e:
        _LOGGER.error(f"Error fetching data from meter: {e}")
        return None


async def check_health(max_time_without_data):
    """Check the health of the system and restart if necessary."""
    global last_successful_read
    while True:
        current_time = time.time()
        if current_time - last_successful_read > max_time_without_data:
            _LOGGER.error(f"No data received for {max_time_without_data} seconds. Restarting the container...")
            os.system("exit 1")  # This will cause the container to exit, triggering a restart if configured properly
        await asyncio.sleep(60)  # Check every minute


async def poll_and_publish_data(device, baudrate, meter_address, polling_rate):
    """Poll data from the meter and publish it via MQTT."""
    consecutive_failures = 0
    max_failures = 5  # Maximum number of consecutive failures before restarting

    while True:
        _LOGGER.debug("Polling data from ABB B23 MeterBus...")
        data = await mbus_fetch_data(device, baudrate, meter_address)
        if data:
            _LOGGER.debug(f"Fetched data: {data}")
            payload = {"data": data}
            await mqtt_publish_sensor_data(client, MQTT_TOPIC, payload)
            consecutive_failures = 0  # Reset failure count on success
        else:
            _LOGGER.error("Failed to fetch data from the meter")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                _LOGGER.critical(f"Failed to fetch data {max_failures} times in a row. Restarting the container...")
                os.system("exit 1")  # This will cause the container to exit, triggering a restart if configured properly
        
        # Wait for the next polling interval
        await asyncio.sleep(polling_rate)

# Main function to start the polling and MQTT publishing
async def main():
    device = CONF_DEVICE
    baudrate = CONF_BAUDRATE
    meter_address = CONF_METER_ADDRESS
    polling_rate = CONF_POLLING_RATE
    max_time_without_data = CONF_MAX_TIMEOUT

    connect_mqtt()

    # Start health check and polling tasks
    health_check_task = asyncio.create_task(check_health(max_time_without_data))
    polling_task = asyncio.create_task(poll_and_publish_data(device, baudrate, meter_address, polling_rate))

    # Wait for both tasks to complete (which they never should)
    await asyncio.gather(health_check_task, polling_task)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        _LOGGER.info("Script terminated by user")
    except Exception as e:
        _LOGGER.critical(f"Unhandled exception: {e}")
        sys.exit(1)
    finally:
        loop.close()