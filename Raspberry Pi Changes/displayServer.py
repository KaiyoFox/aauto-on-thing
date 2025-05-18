print('flask...')
from flask import Flask, Response, render_template,request,jsonify
from flask_cors import CORS
print('image...')
#from cv2 import imencode, IMWRITE_JPEG_QUALITY #USE OPEN-CV-HEADLESS, cuz otherwise its SLOW
#from turbojpeg import TurboJPEG #cv2 replacment (ONLY FASTER ON GOOD COMPUTER)
import numpy as np
from mss import mss
from PIL import Image#, ImageGrab #Image grab is,, okay, same performance, maybe more stable, but slightlyyy worse fps 
#import pyautogui
#scrot is also,,, --ehh
print('input...')
from pynput.mouse import Button, Controller
from pynput.keyboard import Key, Controller as keyContr
print('misc...')
import time
import multitasking
import os
import subprocess
import sys
import json
from io import BytesIO #NEEEDED WITH PIL METHOD,
print("General Imports Done.")

#jpeg = TurboJPEG() #TURBOJPEG

os.environ["DISPLAY"] = ":0"

app = Flask(__name__)
CORS(app)  # Enable CORS for this app
app_events = Flask(__name__)
CORS(app_events)  # Enable CORS for this app

mouse = Controller()
keyboard = keyContr()

sct = mss()
mon = {'top': 0, 'left': 0, 'width': 800, 'height': 480}

# Global flag to control the video stream
frame_quality = 80  #somehow, a lower frame quality, does not help fps ??? MAYBE better latency???
#fps_target = 5000 # Target FPS (avg like 20, but sometimes when AA isn't running it can go upto 30, soo 25?
gen_frame = 'pi3'
#frame_interval = 1 / fps_target

frameAvail = False

frame = np.zeros((480, 800, 4), dtype=np.uint8)
#CV2 & NORMAL PILLOW BUT SIMPLIFIED ALL AROUND
def generate_frames_pi3(skipWait):
    global frameAvail #(this works because we usually only have 1 client
    if(not skipWait):
        m=time.time()
        while(not frameAvail and time.time()-m < 1): #70ms #basically if image capture is too bad, at least dont hold up the other device
            continue
    #frameAvail=False
    
    #np.copyto(frame, np.array(sct_img))
    #frame = np.array(sct_img, dtype=np.uint8)
    #np.copyto(frame, np.array(sct_img))
    #_, buffer = imencode('.jpg', frame, [int(IMWRITE_JPEG_QUALITY), frame_quality, int(IMWRITE_JPEG_OPTIMIZE), 1])

    #_, buffer = imencode('.jpg', frame, [int(IMWRITE_JPEG_QUALITY), frame_quality])
    frame_bytes = buffer.data#buffer.data #tobytes() BOTH OKAY
    frameAvail=False
    
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            

#TURBOJPEG & --PILLOW SIMD-- nevermind, NORMAL PILLOW #GOOD ON PC, ... not RPI 3
def generate_frames_pi4(skipWait):
    global frameAvail #(this works because we usually only have 1 client
    if(not skipWait):
        m=time.time()
        while(not frameAvail and time.time()-m < 1): #70ms #basically if image capture is too bad, at least dont hold up the other device
            continue

    #np.copyto(frame, np.array(sct_img))
    #frame = np.array(sct_img, dtype=np.uint8)#np.array(sct_img)[:, :, :3]  # Drop alpha channel
        
    #frame_bytes = jpeg.encode(frame[..., :3], quality=frame_quality) #frame[..., :3]


    frame_bytes = jpeg.encode(frame[..., :3], quality=frame_quality, flags=TJFLAG_FASTDCT)
    frameAvail=False
    
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

if(gen_frame=='pi3'):
    from cv2 import imencode, IMWRITE_JPEG_QUALITY, IMWRITE_JPEG_OPTIMIZE
    generate_frames = generate_frames_pi3
else:
    from turbojpeg import TurboJPEG, TJFLAG_FASTDCT
    jpeg = TurboJPEG() #TURBOJPEG
    generate_frames = generate_frames_pi4


'''
#CV2 & NORMAL PILLOW | But not trying funKky stuff
def generate_frames():
    #previous_time = time.time()
    #runForShort = time.time()
    #while True:
    if(True):
        #start_time = time.time()
        
        sct_img = sct.grab(mon)
        frame = np.array(sct_img, dtype=np.uint8)#np.array(sct_img)[:, :, :3] (MAKES IT SLOWER)
        
        _, buffer = imencode('.jpg', frame, [int(IMWRITE_JPEG_QUALITY), frame_quality])
        frame_bytes = buffer.data #tobytes() BOTH OKAY

        #elapsed_time = time.time() - start_time
        #if elapsed_time < frame_interval:
        #    time.sleep(frame_interval - elapsed_time)  # Sleep to match FPS

        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
'''

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(process_input_events()), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/vnc.html')
def index():
    return render_template('index.html')





def process_input_events():
    tap_events = request.args.getlist('tap')  # Get all tap events
    key_events = request.args.getlist('key')  # Get all key events

    for tap in tap_events:
        try:
            tap_data = json.loads(tap)  # Parse JSON event data
            mouse_event(tap_data)
            #print(f"Received tap event: {tap_data}")
        except json.JSONDecodeError:
            print(f"Invalid tap data: {tap}")

    for key in key_events:
        try:
            key_data = json.loads(key)  # Parse JSON event data
            keyboard_event(key_data)
            #print(f"Received key event: {key_data}")
        except json.JSONDecodeError:
            print(f"Invalid key data: {key}")

    return len(tap_events)>0
            




@app.route('/test')
def test():
    return "Test OK"

@app.route('/status')
def status():
    return {"status": "ok"}




SPECIAL_KEYS = {
    'Enter': Key.enter,
    'Shift': Key.shift,
    'Backspace': Key.backspace,
    'Tab': Key.tab,
    'Escape': Key.esc,
    'ArrowUp': Key.up,
    'ArrowDown': Key.down,
    'ArrowLeft': Key.left,
    'ArrowRight': Key.right,
    'Space': Key.space,
    'Control': Key.ctrl,
    'Alt': Key.alt,
    'CapsLock': Key.caps_lock
}

#@app_events.route('/keyboard_event', methods=['POST'])
@multitasking.task
def keyboard_event(data):
    #data = request.get_json()
    key = data.get('key')
    event_type = data.get('type')

    if event_type == 'keydown':
        #print(f"Key down: {key}")
        if(key=="right"):
            keyboard.press(']')
            keyboard.release(']')
        elif(key=="left"):
            keyboard.press('[')
            keyboard.release('[')
            
        elif key in SPECIAL_KEYS:
            keyboard.press(SPECIAL_KEYS[key])
        else:
            keyboard.press(key)
    elif event_type == 'keyup':
        #print(f"Key up: {key}")
        if key in SPECIAL_KEYS:
            keyboard.release(SPECIAL_KEYS[key])
        else:
            keyboard.release(key)
    
    #return jsonify({'status': 'success'}), 200

#@app_events.route('/mouse_event', methods=['POST','OPTIONS'])
@multitasking.task
def mouse_event(data):
    try:
        #print('mousee')
        #print(request.data)
        #data = request.json
        #print(data)
        x, y, event_type = data['x'] + mon['left'], data['y'] + mon['top'], data['type']

        # Convert screen stream coordinates to actual screen coordinates
        #screen_width, screen_height = 1920, 1080  # Set to your screen's actual resolution
        #x = int(x * (screen_width / mon['width']))
        #y = int(y * (screen_height / mon['height']))
        
        if event_type == "mousemove":
            #mouse.move(x, y)
            mouse.position = (x, y)  # Set the mouse position
        elif event_type == "mousedown":
            #mouse.move(x, y)
            mouse.position = (x, y)  # Set the mouse position
            #time.sleep(0.01)  # 50 milliseconds delay (adjust as needed)
            #mouse.press(button=mouse.LEFT)
            mouse.press(Button.left)  # Press the left mouse button
        elif event_type == "mouseup":
            #mouse.move(x, y)
            mouse.position = (x, y)  # Set the mouse position
            #time.sleep(0.01)  # 50 milliseconds delay (adjust as needed)
            #mouse.release(button=mouse.LEFT)
            mouse.release(Button.left)  # Press the left mouse button
    except:
        pass

    #return jsonify({"status": "ok"})





import subprocess
import time

DEVICE_USB_ID = "1d6b:1014" #dosen't change
ADB_DEVICE_ID = "8556RP82Q410" #Changes accross devices
ADB_REVERSE_CMD = ["adb", "-s", ADB_DEVICE_ID, "reverse", "tcp:6080", "tcp:6080"]
ADB_CHROMIUM_CMD = ["adb", "-s", ADB_DEVICE_ID, "shell", "supervisorctl", "restart", "chromium"]

def run_command(cmd, sudo=False):
    """ Run a shell command, optionally with sudo. """
    if sudo:
        cmd.insert(0, "sudo")
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def device_present():
    """ Check if the target device appears in lsusb. """
    result = run_command(["lsusb"])
    return DEVICE_USB_ID in result.stdout

def adb_device_ready():
    """ Check if the target device appears in adb devices. """
    result = run_command(["adb", "devices"])
    for line in result.stdout.splitlines():
        if ADB_DEVICE_ID in line and "device" in line:
            return True
    return False

def setup_adb():
    """ Ensure adb server is running as root. """
    run_command(["adb", "kill-server"])
    run_command(["adb", "start-server"], sudo=True)


ADB_REVERSE_CMD_TWO = ["adb", "-s", ADB_DEVICE_ID, "reverse", "tcp:5001", "tcp:5001"]

def handle_device():
    """ Run ADB commands to reverse port and restart Chromium. """
    print("[*] Device found! Waiting for ADB to recognize it...")
    while not adb_device_ready():
        time.sleep(2)

    print("[*] Device is ready. Running adb reverse...")
    time.sleep(1)
    print("running")
    run_command(ADB_REVERSE_CMD)
    print("ok")
    #run_command(ADB_REVERSE_CMD_TWO)#5001
    
    print("[*] Restarting Chromium...")
    run_command(ADB_CHROMIUM_CMD)
    
    print("[*] Monitoring for device disconnection...")

@multitasking.task
def checkDev():
    print("[*] Starting ADB server as root...")
    setup_adb()
    
    while True:
        if device_present():
            handle_device()
        
            # Keep checking lsusb to make sure device stays connected
            while device_present():
                time.sleep(5)
            
            print("[!] Device disconnected. Restarting search...")
        
        time.sleep(1)  # Fast check, but not overwhelming

@multitasking.task
def ooot():
    app.run(host="0.0.0.0", port=6080, debug=False, threaded=True)

@multitasking.task
def aaat():
    global sct_img
    global frameAvail
    global buffer

    #np.copyto(frame, np.array(sct_img))
    _, buffer = imencode('.jpg', frame, [int(IMWRITE_JPEG_QUALITY), frame_quality])

    frameAvail = True
    
if __name__ == "__main__":
    checkDev()

    #OOOT METHOD IS BADDDD FOR GOOD COMPTUER!!; INSETAD CAPTURE EACH FRAME IN ROUTE FUNC, AND DONT THREAD SERVER
    ooot()
    sct_img=None
    buffer=None
    #aaat()
    #app.run(host="0.0.0.0", port=6080, debug=False, threaded=False)

    while True:
        #start_time = time.time()

        sct_img = sct.grab(mon)
        np.copyto(frame, np.array(sct_img))
        if(gen_frame=='pi3'):
            aaat()
        #_, buffer = imencode('.jpg', frame, [int(IMWRITE_JPEG_QUALITY), frame_quality])
        
        #frame = np.array(sct_img, dtype=np.uint8)#, dtype=np.uint8 #np.array(sct_img)[:, :, :3] (MAKES IT SLOWER)
        #frameAvail = True

        #elapsed_time = time.time() - start_time
        #if elapsed_time < frame_interval:
        #    time.sleep(frame_interval - elapsed_time)  # Sleep to match FPS
        #while(frameAvail):
        #    continue
