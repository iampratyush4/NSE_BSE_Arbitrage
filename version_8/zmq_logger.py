# zmq_logger.py
import zmq
import orjson

class ZmqLogger:
    def __init__(self, address="tcp://127.0.0.1:5556"):
        context = zmq.Context.instance()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind(address)

    def log(self, level, message):
        log_entry = orjson.dumps({"level": level, "message": message})
        self.socket.send(log_entry)

# Global logger instance
zmq_logger = ZmqLogger()

def info(message):
    zmq_logger.log("INFO", message)

def error(message):
    zmq_logger.log("ERROR", message)

def warning(message):
    zmq_logger.log("WARNING", message)

def debug(message):
    zmq_logger.log("DEBUG", message)
