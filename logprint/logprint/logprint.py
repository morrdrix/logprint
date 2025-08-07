#
# LogPrint Class
#
# This lightweight class provides a convenient method of logging, allowing existing code using print() to be
# easily augmented with a logging functionality.
#
# LogPrint.print( *args, **kwargs) is used to to override the standard print() and is fully compatible with it.
#
# License:
# This code is released under the terms of the MIT License
# Copyright © 2020 Julian Klein
#


import builtins as __builtin__
import datetime
from sys import argv

__version__ = '1.1.0'

_MAIN_SCRIPT = argv[0]


class LogPrint:
    """
    LogPrint Class

    Description:
    This class is used to override the built-in print function and log the output to a file and screen.
    Using this logger existing code can be augumented to logging functionality easily.

    Usage info:
    - implemented as Singelton (only one instance of LogPrint allowed)
    - output configuration can be set with set_config(**kwargs)
    - default output configuration:
        timestamp_format: '[%Y-%m-%d %H:%M:%S]' (string)
        timestamp: False (bool)
        screen: True (bool)
        file: True (bool)

    - output configuration can be overridden temporarily by passing configuration **kwargs to print()
    - output streams to screen and file are always identical when both are activated
    - print() keywords "file" and "flush" are used by LogPrint.print( *args, **kwargs) and get overwitten if set
    """

    _ninst = 0  # instance counter

    def __new__(cls, *args, **kwargs):
        '''
        Creates a new instance of the class if not existent yet
        :return Instance or None
        '''
        if LogPrint._ninst:  # already an instance running
            print(f'Error: only one instance of {cls.__name__} allowed')
            return None
        else:
            return super().__new__(cls)

    def __init__(self, file='log.txt', write_mode='w', print_header='False'):
        '''
        Initializes the class and opens the log file.
        :param file: File name (default 'log.txt')
        :param write_mode: Write mode (default: 'w' from ['w','a'])
        :param print_header: print logging informaton at start
        '''
        LogPrint._ninst += 1  # register instance

        self.script_name = _MAIN_SCRIPT
        self.file_hnd = None  # file handle
        self.file_name = file

        self.configuration = {'timestamp_format': '[%Y-%m-%d %H:%M:%S]',
                              'timestamp': False,
                              'screen': True,
                              'file': True,
                              }
        try:
            self.file_hnd = open(self.file_name, write_mode, encoding='utf-8')
        except IOError as e:
            print(e)

        if print_header:
            self.print(f'logging {self.script_name} to {self.file_name}')

    def __del__(self):
        '''
        Destructor, reduces instance counter by 1 and closes log file.
        '''
        LogPrint._ninst -= 1  # unregister instance
        try:
            self.file_hnd.close()  # close file
            return True
        except IOError as e:
            print(e)
            return False

    def set_temp_config(self, **kwargs):
        '''
        create manipulated copy of configuration dict
        manipulation is defined by **kwargs
        :param kwargs:
        :return: configuration dictionary
        '''
        temporary_configuration = self.configuration.copy()
        excess_kwargs = dict()

        for key in kwargs:
            if key in temporary_configuration:
                temporary_configuration[key] = kwargs[key]
            else:
                excess_kwargs[key] = kwargs[key]

        return temporary_configuration, excess_kwargs

    def set_config(self, **kwargs):
        '''
        set specified keys in configuration dict
        :param kwargs:
        :return: None
        '''
        self.configuration = self.set_temp_config(**kwargs)[0]

    def print(self, *args, **kwargs):
        '''
        Method to override standart print() with
        Output is handled according to configuration
        Output handling is overridden by inline configuration kwargs
        :param args: see print()
        :param kwargs: see print()
        '''
        temp_config, print_kwargs = self.set_temp_config(**kwargs)

        if temp_config['timestamp']:
            args = [datetime.datetime.now().strftime(temp_config['timestamp_format'])] + list(args)

        if temp_config['screen']:
            __builtin__.print(*args, **print_kwargs)  # screen output

        if temp_config['file']:
            print_kwargs['file'] = self.file_hnd
            print_kwargs['flush'] = True  # for instant writing
            __builtin__.print(*args, **print_kwargs)  # file output


if __name__ == '__main__':
    ''' Usage 
    '''

    log = LogPrint()  # create Logprint instance

    print = log.print  # override buildin print()

    # configure output
    log.set_config(timestamp=True)
    print(f'This timestamp and text should appear on screen and in log-file {log.file_name}', sep=' <sep> ',
          end='<end>\n')
    # configure output temporarily with inline configuration kwargs
    print(f'This text should appear on screen and in log-file {log.file_name}', 'a second positional argument',
          sep=' <sep> ', end='<end>\n', timestamp=False)
    # previous inline outpot configuration was temporary
    print(f'This text and timestamp should appear on screen and in log-file {log.file_name} again',
          'a second positional argument and a third positional integer argument', 99, sep=' <sep> ', end='<end>\n')

    # creating a second instance fails
    log1 = LogPrint()
