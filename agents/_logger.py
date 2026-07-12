import time


def create_logger(name: str):
    def log(msg: str, extra: dict = None):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        extra_str = f" {extra}" if extra else ""
        print(f"[{name}][{ts}] {msg}{extra_str}")

    def error(msg: str, extra: dict = None):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        extra_str = f" {extra}" if extra else ""
        print(f"[{name}][{ts}] ERROR: {msg}{extra_str}")

    return type("Logger", (), {"log": staticmethod(log), "error": staticmethod(error)})()
