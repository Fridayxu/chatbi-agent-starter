import time


def create_logger(name: str):
    def log(msg: str):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{name}][{ts}] {msg}")

    def error(msg: str):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{name}][{ts}] ERROR: {msg}")

    return type("Logger", (), {"log": staticmethod(log), "error": staticmethod(error)})()
