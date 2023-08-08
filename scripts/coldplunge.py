import os
import glob
import time
import datetime
import RPi.GPIO as GPIO

# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# DS18B20 base directory
BASE_DIR = '/sys/bus/w1/devices/'
DEVICE_FOLDERS = glob.glob(BASE_DIR + '28*')
DEVICE_FILES = [device + '/w1_slave' for device in DEVICE_FOLDERS]

# Ensure you match the right sensor to the right location based on the addresses
TEMP_INLET_FILE = DEVICE_FILES[0]
TEMP_OUTLET_FILE = DEVICE_FILES[1]
#TEMP_FLOOR_FILE = DEVICE_FILES[2]

# Relay pins
FREEZER_RELAY_PIN = 20
PUMP_RELAY_PIN = 21

# Setup relay pins
for pin in [FREEZER_RELAY_PIN, PUMP_RELAY_PIN]:
    GPIO.setup(pin, GPIO.OUT)

def read_temp_raw(device_file):
    with open(device_file, 'r') as f:
        return f.readlines()

def read_temp(device_file):
    lines = read_temp_raw(device_file)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(device_file)
    temp_output = lines[1].find('t=')
    if temp_output != -1:
        temp_string = lines[1][temp_output+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def pulse_pump(duration_minutes):
    print(f"Pulsing the pump for {duration_minutes} minutes...")
    GPIO.output(PUMP_RELAY_PIN, GPIO.LOW)  # Turn on the pump
    time.sleep(duration_minutes * 60)  # Let the pump run for the duration
    GPIO.output(PUMP_RELAY_PIN, GPIO.HIGH)  # Turn off the pump

def get_average_temp():
    pulse_pump(2)  # Pulse the pump for 2 minutes
    inlet_temp = read_temp(TEMP_INLET_FILE)
    outlet_temp = read_temp(TEMP_OUTLET_FILE)
    #floor_temp = read_temp(TEMP_FLOOR_FILE)
    #avg_temp = (inlet_temp + outlet_temp + floor_temp) / 3.0
    avg_temp = (inlet_temp + outlet_temp) / 2.0
    #print(f"Temperature readings - Inlet: {inlet_temp}°C, Outlet: {outlet_temp}°C, Floor: {floor_temp}°C. Average: {avg_temp}°C.")
    print(f"Temperature readings - Inlet: {inlet_temp}°C, Outlet: {outlet_temp}°C. Average: {avg_temp}°C.")
    return avg_temp

def filter_schedule():
    now = datetime.datetime.now().time()
    if datetime.time(8, 30) <= now <= datetime.time(10, 0):
        return True
    return False

def main_loop():
    # Pulse the pump for 2 minutes and get the average temperature
    avg_temp = get_average_temp()

    # Control freezer based on average temperature
    if avg_temp > TARGET_TEMP:
        print("Turning on the freezer...")
        GPIO.output(FREEZER_RELAY_PIN, GPIO.LOW)  # Turn on the freezer
    else:
        print("Turning off the freezer...")
        GPIO.output(FREEZER_RELAY_PIN, GPIO.HIGH)  # Turn off the freezer

    # Control the pool pump based on schedule
    if filter_schedule():
        print("Turning on the pump due to filter schedule...")
        GPIO.output(PUMP_RELAY_PIN, GPIO.LOW)  # Turn on the pump
    else:
        print("Turning off the pump as it's outside the filter schedule...")
        GPIO.output(PUMP_RELAY_PIN, GPIO.HIGH)  # Turn off the pump

    print("Waiting for 30 minutes before the next cycle...")
    time.sleep(30 * 60)

TARGET_TEMP = 2.0

print("Starting cold plunge control program...")

try:
    while True:
        main_loop()

except KeyboardInterrupt:
    print("Shutting down...")
    GPIO.cleanup()
