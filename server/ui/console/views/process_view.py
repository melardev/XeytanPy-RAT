class ProcessView:
    def __init__(self, mediator):
        self.mediator = mediator

    @staticmethod
    def print_process_list(client, processes):
        if client and type(processes) == list:
            print('Process list for %s' % client['pc_name'])
            for process in processes:
                if process.get('success', False):
                    print('Name: %s\n\tPath: %s\n\tPid: %s\n\tUsername: %s\n\tCmdLine: %s' % (
                        process.get('name', None),
                        process.get('path', None),
                        process.get('pid', None),
                        process.get('username', None),
                        process.get('cmdline', None)
                    ))
                else:
                    print('Error with Process %s: %s',
                          process.get('name', None),
                          process.get('error_message', 'Unknown error'))
        else:
            print('ProcessView::print_process_list() Unexpected argument values')

    @staticmethod
    def print_shell_data(shell_data, client=None):
        if client is not None:
            print('Shell Output from %s' % client['pc_name'])
        print(shell_data)
