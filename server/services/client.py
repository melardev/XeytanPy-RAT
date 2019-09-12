import time
import threading

from shared.net_lib.packets.packet import PacketType
from shared.net_lib.services.net.synchronous.base_client import BaseNetClientService


class NetClientService(BaseNetClientService):
    def __init__(self, server=None, address=None, socket_obj=None):
        super().__init__(socket_obj)
        self.server = server
        self.running = False
        self.client_data = {'address': address, 'client_id': socket_obj.fileno(), 'socket_object': socket_obj,
                            'connection_time': '%s' % time.time()}
        self.client_thread = None

    def interact_async(self):
        self.running = True
        self.client_thread = threading.Thread(target=self.interact)
        self.client_thread.start()

    def interact(self):
        while self.running:
            self.try_read_packet()

    def on_packet_received(self, packet):
        if packet.packet_type == PacketType.PACKET_TYPE_PRESENTATION:
            self.client_data['pc_name'] = packet.pc_name
            self.client_data['username'] = packet.username
            self.client_data['os_name'] = packet.os_name

        self.server.on_packet_received(self.client_data, packet)

    def get_client_model(self):
        return self.client_data

    def on_client_disconnected(self):
        self.running = False
        self.server.on_client_disconnected(self.client_data)
