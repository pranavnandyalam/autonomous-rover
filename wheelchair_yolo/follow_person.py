import cv2
import numpy as np
from ultralytics import YOLO
import time
import socket
import imutils
import threading
import sys
import urllib.request

TCP_IP = '192.168.50.207'
TCP_PORT = 5005
STREAM_URL = f'http://{TCP_IP}/stream'
MODEL_PATH = "/Users/prn/Documents/Code/ENGR100/runs/detect/wheelchair_person/weights/best.pt"
DRIVE_ENABLED = "--no-drive" not in sys.argv
LOG_PATH = "/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/" + ("follow_log.txt" if DRIVE_ENABLED else "follow_log_nodrive.txt")
FREEZE_S = 0.4

PERSON_CLASS = 1
WHEELCHAIR_CLASS = 0
CONFIDENCE = 0.3
IMG_SIZE = 320

FAR_HEIGHT = 0.4
STOP_HEIGHT = 1.1
BACK_HEIGHT = 1.5
MAX_FORWARD = 140
MIN_DRIVE = 80
MAX_SPEED = 170
BACK_SPEED = 100

TURN_KP = 120
TURN_KD = 15
TURN_DEADBAND = 0.08
ERROR_SMOOTHING = 0.5
HOLD_S = 0.5

FRAME_TIMEOUT_S = 1.0
STREAM_TIMEOUT_S = 3.0
RECONNECT_DELAY_S = 1.0


def clamp(value, low, high):
    return max(low, min(high, value))


class MJPEGStream:
    def __init__(self, url):
        self.url = url
        self.frame = None
        self.frame_id = 0
        self.new_frame = threading.Condition()
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            try:
                self.read_stream()
            except Exception as e:
                print(f"Stream error ({e}). Reconnecting...")
            time.sleep(RECONNECT_DELAY_S)

    def read_stream(self):
        with urllib.request.urlopen(self.url, timeout=STREAM_TIMEOUT_S) as response:
            print("Stream opened.")
            buffer = b""
            while True:
                chunk = response.read1(16384)
                if not chunk:
                    raise ConnectionError("stream ended")
                buffer = self.take_latest_jpeg(buffer + chunk)

    def take_latest_jpeg(self, buffer):
        end = buffer.rfind(b"\xff\xd9")
        if end == -1:
            return buffer if len(buffer) < 1_000_000 else b""
        start = buffer.rfind(b"\xff\xd8", 0, end)
        if start != -1:
            frame = cv2.imdecode(np.frombuffer(buffer[start:end + 2], np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                with self.new_frame:
                    self.frame = frame
                    self.frame_id += 1
                    self.new_frame.notify_all()
        return buffer[end + 2:]

    def wait_for_frame(self, last_id, timeout):
        with self.new_frame:
            self.new_frame.wait_for(lambda: self.frame_id != last_id, timeout)
            return self.frame, self.frame_id


class ESP32Link:
    def __init__(self, ip, port):
        self.address = (ip, port)
        self.sock = None
        self.last_attempt = 0.0
        self.connect()

    def connect(self):
        self.last_attempt = time.time()
        print(f"Connecting to ESP32 at {self.address[0]}:{self.address[1]}...")
        try:
            sock = socket.create_connection(self.address, timeout=1)
        except OSError as e:
            print(f"Couldn't connect to ESP32: {e}")
            return
        sock.setblocking(False)
        self.sock = sock
        print("Successfully connected to ESP32.")

    def send(self, cmd):
        if self.sock is None and time.time() - self.last_attempt >= RECONNECT_DELAY_S:
            self.connect()
        if self.sock is None:
            return
        try:
            self.sock.sendall(f"{cmd}\n".encode())
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                for line in data.decode(errors="ignore").splitlines():
                    if line.startswith("INFO"):
                        print(f"ESP32 {line}")
        except BlockingIOError:
            pass
        except OSError as e:
            print(f"Lost connection to ESP32 ({e}). Reconnecting...")
            self.close()

    def close(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = None


def center_x(box):
    return (box[0] + box[2]) / 2


class Tracker:
    def __init__(self):
        self.last_box = None
        self.last_seen = 0.0

    def update(self, boxes, now):
        if len(boxes) > 0:
            self.last_box = self.pick(boxes)
            self.last_seen = now
            return self.last_box, False
        if self.last_box is not None and now - self.last_seen <= HOLD_S:
            return self.last_box, True
        self.last_box = None
        return None, False

    def pick(self, boxes):
        if self.last_box is None:
            return max(boxes, key=lambda b: b[3] - b[1])
        last_x = center_x(self.last_box)
        return min(boxes, key=lambda b: abs(center_x(b) - last_x))


def forward_speed(height):
    if height >= STOP_HEIGHT:
        return 0
    closeness = clamp((STOP_HEIGHT - height) / (STOP_HEIGHT - FAR_HEIGHT), 0, 1)
    return MIN_DRIVE + closeness * (MAX_FORWARD - MIN_DRIVE)


def mix(forward, turn):
    if forward == 0:
        if turn == 0:
            return 0, 0
        spin = clamp(abs(turn), MIN_DRIVE, MAX_SPEED)
        return (int(spin), 0) if turn > 0 else (0, int(spin))
    left = clamp(forward + turn, 0, MAX_SPEED)
    right = clamp(forward - turn, 0, MAX_SPEED)
    return int(left), int(right)


class Controller:
    def __init__(self):
        self.reset()

    def reset(self):
        self.error = None
        self.last_time = None

    def update(self, box, frame_w, frame_h, now):
        raw_error = (center_x(box) - frame_w / 2) / (frame_w / 2)
        height = (box[3] - box[1]) / frame_h

        previous = self.error
        self.error = raw_error if previous is None else ERROR_SMOOTHING * raw_error + (1 - ERROR_SMOOTHING) * previous
        dt = now - self.last_time if self.last_time is not None else 0
        self.last_time = now
        rate = (self.error - previous) / dt if previous is not None and dt > 0 else 0

        if height >= BACK_HEIGHT:
            return f"{BACK_SPEED},{BACK_SPEED},s", f"BACK  h={height:.2f}"

        turn = 0 if abs(self.error) < TURN_DEADBAND else TURN_KP * self.error + TURN_KD * rate
        left, right = mix(forward_speed(height), turn)
        if left == 0 and right == 0:
            return "STOP", f"STOP (close)  h={height:.2f}"
        return f"{left},{right},w", f"DRIVE L={left:3d} R={right:3d}  x={self.error:+.2f} h={height:.2f}"


def person_boxes(result):
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    return boxes.xyxy.cpu().numpy()[boxes.cls.cpu().numpy() == PERSON_CLASS]


def draw(result, box, status, fps):
    frame = result.plot()
    if box is not None:
        x1, y1, x2, y2 = (int(v) for v in box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
    cx = frame.shape[1] // 2
    cv2.line(frame, (cx, 0), (cx, frame.shape[0]), (0, 255, 255), 1)
    cv2.putText(frame, status, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(frame, f"{fps:.1f} fps", (5, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    cv2.imshow("Person Follower", imutils.resize(frame, width=640))
    return cv2.waitKey(1) in (27, ord('q'))


def follow(stream, model, esp32):
    tracker = Tracker()
    controller = Controller()
    frame_id = 0
    fps = 0.0
    start_time = last_frame_time = time.time()
    freezes = []

    while True:
        frame, new_id = stream.wait_for_frame(frame_id, FRAME_TIMEOUT_S)
        if new_id == frame_id:
            print("No frames from camera. Stopping robot.")
            esp32.send("STOP")
            if cv2.waitKey(1) in (27, ord('q')):
                break
            continue
        frame_id = new_id

        now = time.time()
        gap = now - last_frame_time
        if gap > FREEZE_S and frame_id > 1:
            freezes.append(gap)
            print(f"FREEZE: no new frame for {gap * 1000:.0f}ms")
        fps = 0.9 * fps + 0.1 / max(gap, 1e-3)
        last_frame_time = now

        result = model(frame, classes=[WHEELCHAIR_CLASS, PERSON_CLASS], conf=CONFIDENCE, imgsz=IMG_SIZE, verbose=False)[0]
        box, held = tracker.update(person_boxes(result), now)

        if box is None:
            controller.reset()
            cmd, status = "STOP", "STOP (no person)"
        else:
            cmd, status = controller.update(box, frame.shape[1], frame.shape[0], now)
            if held:
                status += "  [held]"

        esp32.send(cmd if DRIVE_ENABLED else "STOP")
        print(status)
        if draw(result, box, status, fps):
            break

    minutes = (time.time() - start_time) / 60
    print(f"SUMMARY ({'driving' if DRIVE_ENABLED else 'motors off'}): {len(freezes)} freezes in {minutes:.1f} min"
          + (f", longest {max(freezes) * 1000:.0f}ms" if freezes else ""))


class Tee:
    def __init__(self, stream, log_file):
        self.stream = stream
        self.log_file = log_file

    def write(self, text):
        self.stream.write(text)
        if text.strip():
            text = f"[{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] {text}"
        self.log_file.write(text)

    def flush(self):
        self.stream.flush()
        self.log_file.flush()


if __name__ == "__main__":
    log_file = open(LOG_PATH, "w", buffering=1)
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)

    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    esp32 = ESP32Link(TCP_IP, TCP_PORT)
    stream = MJPEGStream(STREAM_URL)

    try:
        follow(stream, model, esp32)
    except KeyboardInterrupt:
        pass
    finally:
        esp32.send("STOP")
        esp32.close()
        cv2.destroyAllWindows()
