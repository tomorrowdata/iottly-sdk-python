
import socket
from multiprocessing import Process, Event


class UDSStubServer:
    """UDS stub server for testing
    """
    def __init__(self, socket_path, on_bind=None, on_connect=None):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(socket_path)
        self.socket.listen()
        if on_bind:
            on_bind()
        self.on_client_connected_cb = on_connect
        self.proc = None

    def loop(self):
        while True:
            try:
                client_sock, _ = self.socket.accept()
            except OSError:
                # Socket closed
                break  # exit
            with client_sock:
                if self.on_client_connected_cb:
                    self.on_client_connected_cb(client_sock)

    def start(self):
        self.proc = Process(target=self.loop)
        self.proc.start()

    def stop(self):
        self.socket.close()
        self.proc.terminate()
