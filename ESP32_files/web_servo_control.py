import json
import time

import network
import uaioweb
from machine import PWM, Pin
from uaioweb import \
    asyncio  # Note: compatibility between micropython and python.
from utime import sleep_ms

last_update = [0, 0]
servo1_pin = 22
servo2_pin = 23
#last_pos = [55 * 256, 79 * 256]
last_pos = [3457, 4910]

html = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
        }
        .slider-container {
            width: 80%;
            margin: auto;
        }
        .slider-label {
            font-size: 18px;
            margin-bottom: 10px;
        }
        .slider {
            width: 100%;
        }
   .button-container {
        display: flex;
        justify-content: space-between;
        margin: 10px;
    }
    .button-group {
        width: 48%;
        display: flex;
        justify-content: space-between;
    }
    .button {
        width: 45%;
        padding: 5px;
        font-size: 16px;
    }
    .current-position {
        width: 100%; /* Maximize space */
        font-size: 16px;
        margin-top: 10px; /* Add margin for better spacing */
    }
    </style>
</head>
<body>
    <h2>ESP32 Servo Controller</h2>
    <div class="slider-container">
        <div id="label1" class="slider-label">Slider 1</div>
        <input type="range" min="0" max="10000" value="75" class="slider" id="slider1" oninput="updateSlider(1)">
    </div>
<div class="button-container">
        <div class="button-group">
            <button class="button" onclick="adjustPosition(1, -100)">-100</button>
            <button class="button" onclick="adjustPosition(1, -10)">-10</button>
            <button class="button" onclick="adjustPosition(1, -1)">-1</button>
            
        </div>
        <div class="current-position" id="currentPosition1"></div>
        <div class="button-group">
            <button class="button" onclick="adjustPosition(1, 1)">+1</button>
            <button class="button" onclick="adjustPosition(1, 10)">+10</button>
            <button class="button" onclick="adjustPosition(1, 100)">+100</button>
        </div>
    </div>
<div class="slider-container">
    <div id="label2" class="slider-label">Slider 2</div>
    <input type="range" min="0" max="10000" value="75" class="slider" id="slider2" oninput="updateSlider(2)">
</div>
   <div class="button-container">
    <div class="button-group">
        <button class="button" onclick="adjustPosition(2, -100)">-100</button>

<button class="button" onclick="adjustPosition(2, -10)">-10</button>
        <button class="button" onclick="adjustPosition(2, -1)">-1</button>
    </div>
        <div class="current-position" id="currentPosition2"></div>
    <div class="button-group">
        <button class="button" onclick="adjustPosition(2, 1)">+1</button>
        <button class="button" onclick="adjustPosition(2, 10)">+10</button>
        <button class="button" onclick="adjustPosition(2, 100)">+100</button>

    </div>
</div>

<script>
    function updateSlider(sliderNum) {
        var sliderValue = document.getElementById('slider' + sliderNum).value;
        updateLabel();
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/set_slider?slider=' + sliderNum + '&value=' + sliderValue, true);
        xhr.send();
    }


    function adjustPosition(sliderNum, amount) {
        var currentSliderValue = parseInt(document.getElementById('slider' + sliderNum).value);
        var newSliderValue = currentSliderValue + amount;
        document.getElementById('slider' + sliderNum).value = newSliderValue;
        updateSlider(sliderNum)
    }

    function updateLabel() {
        document.getElementById('currentPosition1').innerHTML = 'Position: ' + document.getElementById('slider1').value;
        document.getElementById('currentPosition2').innerHTML = 'Position: ' + document.getElementById('slider2').value;
    }

    // Function to set initial slider values on page load
    function setInitialSliderValues() {
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                var initialValues = JSON.parse(xhr.responseText);
                document.getElementById('slider1').value = initialValues.slider1;
                document.getElementById('label1').innerHTML = initialValues.slider1Name;
                document.getElementById('slider2').value = initialValues.slider2;
                document.getElementById('label2').innerHTML = initialValues.slider2Name;
                updateLabel();
            }
        };
        xhr.open('GET', '/get_sliders_position', true);
        xhr.send();
    }

    // Call the function to set initial slider values on page load
    window.onload = setInitialSliderValues;
</script>

</body>
</html>
"""


def servo_move(servo, pos):
    """Function that moves the servo to the desired position.
    The servo is connected to the ESP32 board via PWM.
    The PWM duty value is set to the desired position.
    """
    try:
        if servo == 1:  # bottom servo
            m_servo = PWM(Pin(servo1_pin), freq=50)  # top servo, connected to Pin 22
        elif servo == 2:  # top servo
            m_servo = PWM(Pin(servo2_pin), freq=50)  # bottom servo, connected to Pin 23
        else:
            print(f"wrong servo number {servo}")
            return
        # m_servo.duty(pos)           # servo is new position
        m_servo.duty_u16(pos)  # servo is new position
        if pos > 0:
            last_update[servo - 1] = time.ticks_ms()
            last_pos[servo - 1] = pos
        else:
            last_update[servo - 1] = 0
    #        m_servo.duty(0)           # servo is new position

    except Exception as e:
        print(f"Error in servo_move: {e}")


async def release_loop():
    while True:
        await asyncio.sleep(1)
        for s in [1, 2]:
            if last_update[s - 1] > 0 and last_update[s - 1] + 1000 < time.ticks_ms():
                servo_move(s, 0)
                print(f"Sleep servo {s}")


def startweb():
    app = uaioweb.App(host="0.0.0.0", port=80)

    @app.route("/")
    async def handler(r, w):
        w.write(b"HTTP/1.0 200 OK\r\n")
        w.write(b"Content-Type: text/html; charset=utf-8\r\n")
        w.write(b"\r\n")
        w.write(html)
        await w.drain()

    @app.route("/set_slider")
    async def set_slider(request, writer):
        params = uaioweb.parse_qs(request.query)
        slider_num = params.get("slider", [""])
        slider_value = params.get("value", [""])
        print(f"Slider {slider_num} set to value {slider_value}")
        writer.write(b"HTTP/1.0 200 OK\r\n")
        writer.write(b"Content-Type: text/plain; charset=utf-8\r\n")
        writer.write(b"\r\n")
        writer.write(b"OK")
        await writer.drain()
        servo_move(int(slider_num), int(slider_value))

    @app.route("/get_sliders_position")
    async def get_initial_sliders(request, writer):
        # Return initial slider values as JSON
        slider_values = {
            "slider1": last_pos[0],  # Adjust with your actual initial values
            "slider2": last_pos[1],
            "slider1Name": "Top Servo",  # Adjust with your actual initial values
            "slider2Name": "Bottom Servo",
        }
        writer.write(b"HTTP/1.0 200 OK\r\n")
        writer.write(b"Content-Type: application/json; charset=utf-8\r\n")
        writer.write(b"\r\n")
        writer.write(json.dumps(slider_values).encode("utf-8"))
        await writer.drain()

    loop = asyncio.get_event_loop()
    fu = loop.create_task(app.serve())
    loop.run_until_complete(asyncio.gather(fu, release_loop()))

if __name__ == "__main__":
    ssid = "MicroPython-AP"
    password = "123456789"

    # try to get the wifi details from wifi.json if error, be an accespoint
    try:
        with open("wifi.json", "r") as openfile:
            # Reading from json file
            wifi = json.load(openfile)
            ssid = wifi.get("ssid", ssid)
            password = wifi.get("key", password)
        station = network.WLAN(network.STA_IF)
        station.active(True)
        station.connect(ssid, password)
        while not station.isconnected():
            time.sleep_ms(100)

        print("Connection successful")
        print(station.ifconfig())
    except Exception as ex:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=ssid, password=password)
        while ap.active() == False:
            pass
        print("Accespoint Connection successful")

    servo_move(1, last_pos[0])
    time.sleep(1)
    servo_move(2, last_pos[1])
    time.sleep(1)

    startweb()
