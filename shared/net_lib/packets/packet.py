import struct

PACKET_HEADER_LENGTH = struct.calcsize('Q')


class PacketType:
    INVALID_PACKET_TYPE = -1,
    PACKET_TYPE_PRESENTATION = 1
    PACKET_TYPE_INFORMATION = 2,
    PACKET_TYPE_FILESYSTEM = 3,
    PACKET_TYPE_PROCESS = 4,
    PACKET_TYPE_SHELL = 5,
    PACKET_TYPE_DESKTOP = 6,
    PACKET_TYPE_UNINSTALL = 10
    MIN_VALID_PACKET_TYPE = PACKET_TYPE_PRESENTATION
    MAX_VALID_PACKET_TYPE = PACKET_TYPE_UNINSTALL


class Packet:
    def __init__(self, packet_type=PacketType.INVALID_PACKET_TYPE, success=True, error_message=None):
        self.packet_type = packet_type
        self.success = success
        self.error_message = error_message


class PacketPresentation(Packet):
    def __init__(self, pc_name='', os_name='', username=''):
        super(PacketPresentation, self).__init__(PacketType.PACKET_TYPE_PRESENTATION)
        self.pc_name = pc_name
        self.os_name = os_name
        self.username = username


class PacketInformation(Packet):
    def __init__(self, info=None):
        super(PacketInformation, self).__init__(PacketType.PACKET_TYPE_INFORMATION)
        self.info = info


class PacketDesktop(Packet):
    class Actions:
        Play = 1
        Stop = 2

    def __init__(self, instruction=Actions.Play, image=None):
        super(PacketDesktop, self).__init__(PacketType.PACKET_TYPE_DESKTOP)
        self.instruction = instruction
        self.image = image


class PacketFileSystem(Packet):
    class Actions:
        List = 1
        Download = 2
        Upload = 3

    def __init__(self, success=True, error_message=None, fs_action=Actions.List, path=None, list_dir=None,
                 file_data=None,
                 filename=None):
        super(PacketFileSystem, self).__init__(packet_type=PacketType.PACKET_TYPE_FILESYSTEM, success=success,
                                               error_message=error_message)

        self.fs_action = fs_action
        self.path = path
        self.list_dir = list_dir

        self.file_data = file_data
        self.filename = filename


class PacketProcess(Packet):
    class Actions:
        List = 1
        Kill = 2

    def __init__(self, ps_action=Actions.List, pid=None):
        super(PacketProcess, self).__init__(PacketType.PACKET_TYPE_PROCESS)
        self.processes = []
        self.ps_action = ps_action
        self.pid = pid


class PacketShell(Packet):
    class Actions:
        Exec = 1
        ExecPiped = 2,
        Interactive = 3
        Stop = 4

        MinValue = Exec
        MaxValue = Stop

    def __init__(self, shell_action, command=None, data=None):
        super(PacketShell, self).__init__(PacketType.PACKET_TYPE_SHELL)
        if shell_action < PacketShell.Actions.MinValue or shell_action > PacketShell.Actions.MaxValue:
            raise NotImplementedError("action must be a valid value")
        self.shell_action = shell_action
        self.command = command
        self.data = data
