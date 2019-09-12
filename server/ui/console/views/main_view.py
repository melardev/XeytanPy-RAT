import sys


class MainView:
    def __init__(self, ui_mediator):
        self.ui_mediator = ui_mediator
        self.running = False
        self.client_id = None

    def loop(self):
        self.running = True
        while self.running:
            self.print_banner()
            line = sys.stdin.readline().strip().lower()
            # Try to handle the instruction
            if not self.handle_instruction(line):
                # If we could not handle it, let the called to handle it
                return line

    def handle_instruction(self, instruction):
        return False

    def print_banner(self):
        if self.client_id is not None and self.client_id != -1:
            sys.stdout.write('XeytanPy/%s>$ ' % self.client_id)
        else:
            sys.stdout.write('XeytanPy>$ ')

    def print_error_message(self, message):
        print('Error %s' % message)

    def get_name(self):
        return "MainView"

    def print_help(self, prefix=''):
        print()
