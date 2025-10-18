from server.drivers.server_api import ServerAPI
import time

def monitor_server(device):
    server = ServerAPI(device)
    while True:
        data = server.get_utilization()
        time.sleep(5)
