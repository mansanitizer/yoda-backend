import socket
import struct
import threading
import time
from http import server
import json
from queue import Empty, Queue

import cv2
import numpy as np
from app.detection.detector_service import SessionDetector


HOST = "0.0.0.0"
PORT = 65432
PREVIEW_PORT = 8081
CONTROL_PORT = 65433


latest_frame_jpeg = None
latest_frame_lock = threading.Lock()
latest_status = {
    "connected": False,
    "frame_count": 0,
    "last_updated_at": None,
    "last_detection": None,
}
status_lock = threading.Lock()
detector = SessionDetector()
command_queue: Queue[str] = Queue()


def is_valid_command(cmd: str) -> bool:
    return cmd == "S" or (len(cmd) > 1 and cmd[0] in ["F", "B", "L", "R"] and cmd[1:].isdigit())


class PreviewHandler(server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ["/", "/index.html"]:
            body = (
                "<html><body style='margin:0;background:#111;color:#eee;"
                "font-family:Helvetica,Arial,sans-serif'>"
                "<div style='max-width:1120px;margin:0 auto;padding:16px'>"
                "<h1 style='margin:0 0 12px'>Rover Boxing Preview</h1>"
                "<div id='stats' style='margin:0 0 12px;padding:12px;background:#1b1b1b;"
                "border:1px solid #333;border-radius:8px;white-space:pre-wrap'>Waiting for stream...</div>"
                "<img src='/stream.mjpg' style='width:100%;max-width:1120px;"
                "display:block;margin:0 auto;border:1px solid #333;border-radius:8px' />"
                "</div>"
                "<script>"
                "async function refreshStatus(){"
                "try{"
                "const response=await fetch('/status.json',{cache:'no-store'});"
                "const data=await response.json();"
                "const detection=data.last_detection||{};"
                "document.getElementById('stats').textContent="
                "'Connected: '+data.connected+'\\n'+"
                "'Frames: '+data.frame_count+'\\n'+"
                "'Last update: '+(data.last_updated_at||'n/a')+'\\n'+"
                "'Punch side: '+(detection.action||'NONE')+'\\n'+"
                "'Punch type: '+(detection.punch_type||'n/a')+'\\n'+"
                "'Confidence: '+(detection.confidence||'n/a');"
                "}catch(e){"
                "document.getElementById('stats').textContent='Status fetch failed';"
                "}"
                "}"
                "refreshStatus();"
                "setInterval(refreshStatus, 500);"
                "</script>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/status.json":
            with status_lock:
                body = json.dumps(latest_status).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path != "/stream.mjpg":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header(
            "Content-Type", "multipart/x-mixed-replace; boundary=frame"
        )
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        try:
            while True:
                with latest_frame_lock:
                    frame_bytes = latest_frame_jpeg

                if frame_bytes is None:
                    time.sleep(0.1)
                    continue

                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(
                    f"Content-Length: {len(frame_bytes)}\r\n\r\n".encode("utf-8")
                )
                self.wfile.write(frame_bytes)
                self.wfile.write(b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args) -> None:
        return


def start_preview_server() -> None:
    preview_server = server.ThreadingHTTPServer(("0.0.0.0", PREVIEW_PORT), PreviewHandler)
    preview_thread = threading.Thread(target=preview_server.serve_forever, daemon=True)
    preview_thread.start()
    print(f"Preview stream available at http://127.0.0.1:{PREVIEW_PORT}", flush=True)


def start_control_server() -> None:
    def control_server_loop() -> None:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", CONTROL_PORT))
        server_socket.listen(5)
        print(
            f"Local command socket available at 127.0.0.1:{CONTROL_PORT}",
            flush=True,
        )
        while True:
            conn, _ = server_socket.accept()
            with conn:
                buffer = b""
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        command = line.decode("utf-8").strip().upper()
                        if is_valid_command(command):
                            command_queue.put(command)
                            conn.sendall(f"QUEUED {command}\n".encode("utf-8"))
                        elif command:
                            conn.sendall(b"ERROR invalid command\n")

    control_thread = threading.Thread(target=control_server_loop, daemon=True)
    control_thread.start()


def main() -> None:
    start_preview_server()
    start_control_server()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print("==================================================", flush=True)
    print("Robot command server active on port 65432...", flush=True)
    print("Waiting for client connection...", flush=True)
    print("==================================================", flush=True)

    payload_size = struct.calcsize(">I")

    while True:
        conn, addr = server_socket.accept()
        print(f"Client connected from {addr[0]}:{addr[1]}", flush=True)
        state = {"frame_count": 0, "running": True}
        with status_lock:
            latest_status["connected"] = True

        def video_stream_handler() -> None:
            try:
                while state["running"]:
                    data_buffer = b""
                    while len(data_buffer) < payload_size:
                        packet = conn.recv(payload_size - len(data_buffer))
                        if not packet:
                            state["running"] = False
                            return
                        data_buffer += packet

                    msg_size = struct.unpack(">I", data_buffer)[0]
                    image_buffer = b""
                    while len(image_buffer) < msg_size:
                        packet = conn.recv(msg_size - len(image_buffer))
                        if not packet:
                            state["running"] = False
                            return
                        image_buffer += packet

                    np_array = np.frombuffer(image_buffer, dtype=np.uint8)
                    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
                    if frame is not None:
                        detection, annotated_jpeg = detector.process_frame(frame)
                        with latest_frame_lock:
                            global latest_frame_jpeg
                            latest_frame_jpeg = annotated_jpeg or image_buffer
                        state["frame_count"] += 1
                        with status_lock:
                            latest_status["frame_count"] = state["frame_count"]
                            latest_status["last_updated_at"] = time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            latest_status["last_detection"] = (
                                {
                                    "action": detection.action.value,
                                    "punch_type": detection.punch_type,
                                    "confidence": round(detection.confidence, 3),
                                }
                                if detection
                                else latest_status["last_detection"]
                            )
                        if state["frame_count"] % 30 == 0:
                            height, width = frame.shape[:2]
                            print(
                                f"received {state['frame_count']} frames ({width}x{height})",
                                flush=True,
                            )
            except Exception as exc:
                print(f"Stream processing halted: {exc}", flush=True)
                state["running"] = False

        stream_thread = threading.Thread(target=video_stream_handler, daemon=True)
        stream_thread.start()

        def queued_command_dispatcher() -> None:
            while state["running"]:
                try:
                    cmd = command_queue.get(timeout=0.25)
                except Empty:
                    continue
                try:
                    conn.sendall(cmd.encode("utf-8"))
                    print(f"sent queued command: {cmd}", flush=True)
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                    state["running"] = False
                    return

        dispatch_thread = threading.Thread(target=queued_command_dispatcher, daemon=True)
        dispatch_thread.start()

        with conn:
            try:
                while state["running"]:
                    cmd = input(
                        "Enter Command String (F50/B20/L20/R20/S or EXIT): "
                    ).strip().upper()
                    if cmd == "EXIT":
                        print("Shutting down server...", flush=True)
                        raise KeyboardInterrupt

                    if is_valid_command(cmd):
                        conn.sendall(cmd.encode("utf-8"))
                        print(f"sent command: {cmd}", flush=True)
                    else:
                        print("Invalid entry pattern.", flush=True)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                print("Client disconnected. Waiting for reconnection...", flush=True)
            except KeyboardInterrupt:
                server_socket.close()
                raise
            finally:
                state["running"] = False
                with status_lock:
                    latest_status["connected"] = False
                print("Connection closed.", flush=True)


if __name__ == "__main__":
    main()
