import pickle
import socket
import struct

from shared.net_lib.packets.packet import PACKET_HEADER_LENGTH


class BaseNetClientService:
    def __init__(self, client_socket=None):
        self.client_socket = client_socket

    def send_packet(self, packet):
        packet_serialized = pickle.dumps(packet)
        packet_size = len(packet_serialized)
        header_serialized = struct.pack('Q', packet_size)

        self.client_socket.send(header_serialized)
        self.client_socket.send(packet_serialized)

    def try_read_packet(self):
        # noinspection DuplicatedCode
        try:
            # The client will send str(hex(packet_lenth)) + content
            packet_size = struct.unpack('Q', self.client_socket.recv(PACKET_HEADER_LENGTH))[0]
            data = self.client_socket.recv(packet_size)
            while len(data) < packet_size:
                data = self.client_socket.recv(packet_size - len(data))

            if data:
                packet = pickle.loads(data)
                self.on_packet_received(packet)
                # self.app_channel.post_to_app()
            else:
                self.on_client_disconnected()
                # self.clients_socket.remove(client)
                # self.writable_fd_list.remove(client)

        except socket.error:
            self.on_client_disconnected()

            # self.clients_socket.remove(client)
            # self.writable_fd_list.remove(client)

    def on_client_disconnected(self):
        pass

    def on_packet_received(self, packet):
        pass
