import importlib
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def install_missing_packages():
    required_packages = [
        "asyncio", "configparser", "csv", "datetime", "os", "urllib.parse", "websockets", "json", "logging",
        "arbitrage_finder", "aiohttp", "orjson", "uuid", "gc", "zmq_logger", "setuptools", "Cython", "zmq", "time",
        "py5paisa"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            logging.info(f"Package '{package}' is already installed.")
        except ImportError:
            logging.warning(f"Package '{package}' is missing.")
            missing_packages.append(package)
    
    if missing_packages:
        logging.info(f"Installing missing packages: {missing_packages}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
        logging.info("Installation complete.")
    else:
        logging.info("All required packages are already installed.")

if __name__ == "__main__":
    install_missing_packages()
