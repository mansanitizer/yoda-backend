import socket


HOST = "127.0.0.1"
PORT = 65433
HELP_TEXT = """Commands:
  F<number>  Forward, e.g. F35
  B<number>  Backward, e.g. B20
  L<number>  Left turn, e.g. L30
  R<number>  Right turn, e.g. R30
  S          Stop
  q          Quit
"""


def main() -> None:
    print(HELP_TEXT)
    with socket.create_connection((HOST, PORT)) as sock:
        while True:
            command = input("rover> ").strip().upper()
            if not command:
                continue
            if command in {"Q", "QUIT", "EXIT"}:
                print("Closing console.")
                return
            sock.sendall(f"{command}\n".encode("utf-8"))
            response = sock.recv(1024).decode("utf-8").strip()
            print(response)


if __name__ == "__main__":
    main()
