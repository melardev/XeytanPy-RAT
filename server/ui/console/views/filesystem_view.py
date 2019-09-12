import os
import sys
import posixpath


class FileSystemView:
    def __init__(self, mediator):
        self.mediator = mediator
        self.running = False
        self.client_id = None
        self.current_dir = '/'

    def loop(self):
        self.running = True
        while self.running:
            self.print_banner()
            line = sys.stdin.readline().strip().lower()
            # Try to handle the instruction
            if not self.handle_instruction(line):
                # If we could not handle it, let the called to handle it
                return line

    def print_banner(self):
        sys.stdout.write('XeytanPyServer/%s/FileSystem' % self.client_id)

        if not self.current_dir.startswith('/'):
            sys.stdout.write('/')

        sys.stdout.write(self.current_dir)

        if not self.current_dir.endswith('/'):
            sys.stdout.write('/')

        sys.stdout.write('>$ ')

    def handle_instruction(self, line):
        parts = line.split(' ')

        if parts[0] == 'cd':
            if len(parts) > 0:
                path = parts[1]

                path = path.replace('\\', '/')
                path = posixpath.normpath(path)

                if not path.endswith('/'):
                    path += '/'

                if os.path.isabs(path):
                    self.current_dir = path
                else:
                    self.current_dir = posixpath.normpath(self.current_dir + path) + '/'

            return True
        elif parts[0] == 'clear':
            self.current_dir = '/'

        return False

    def get_name(self):
        return "File System View"

    def print_help(self, prefix=''):
        print(prefix + 'ls - list files in current directory')
        print(prefix + 'clear - set current directory to /')
        print(prefix + 'cd - Change directory')
        print(prefix + 'download - download a file')
        print(prefix + 'upload - upload a file')

    @staticmethod
    def print_fs_roots(client, roots):
        print('File System Roots for %s' % client['pc_name'])
        for root in roots:
            print('Device: %s (%s), MountPoint: %s, opts=%s'
                  % (root.device, root.fstype, root.mountpoint, root.opts))

    @staticmethod
    def print_client_ls(client, path, list_dir):
        print('File System ls for %s' % client['pc_name'])
        print(path)
        for entry in list_dir:
            print(entry)

    def join_path(self, path):
        if path is not None:
            path = path.replace('//', '/').replace('\\', '/').lstrip('/')
            return self.current_dir + path
        else:
            return self.current_dir

    def print_error_message(self, message):
        print('Error %s', message)
