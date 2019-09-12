import getpass
import platform
import socket
import time

from shared.net_lib.packets.packet import PacketPresentation
from shared.net_lib.services.net.synchronous.base_client import BaseNetClientService


class NetClientService(BaseNetClientService):
    def __init__(self, app=None):
        super(NetClientService, self).__init__()
        self.app = app

        self.host = 'localhost'
        self.port = 3002
        self.running = True

    def start(self):
        self.running = True
        while True:
            try:
                # create the socket AF_INET states this is an Ipv4 Socket, SOCK_STREAM states this is a TCP socket
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                pc_name = platform.node()
                os_name = platform.system()  # platform.platform() is more complete
                username = getpass.getuser()
                self.send_packet(PacketPresentation(pc_name=pc_name, os_name=os_name, username=username))
                # Our socket may receive data(is readable) and also may write data (is writable)
                self.client_loop()
                time.sleep(1)
            except IOError as e:
                time.sleep(5)

    def client_loop(self):
        while self.running:
            try:
                self.try_read_packet()
            except socket.error:
                self.on_client_disconnected()
                return

    def on_client_disconnected(self):
        self.client_socket.close()
        time.sleep(5)
        self.start()

    def on_packet_received(self, packet):
        self.app.on_packet_received(packet)
