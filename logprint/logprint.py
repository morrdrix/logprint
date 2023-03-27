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

__version__ = '0.1.0'

class LogPrint:
    """
LogPrint Class

Description:
This class is used to override the built-in print function and log the output to a file and screen.

:methods
__init__(self, file_name='log.txt', fw_mode='w')
print(self, *args, mode='both', **kwargs) - Overrides the built-in print function and logs the output to a file.

"""
    _ninst = 0  # instance counter

    def __new__(cls, *args, **kwargs):
        '''
        Creates a new instance of the class if not existent yet
        :return Instance or None
        '''
        if LogPrint._ninst:  # already an instance running
            __builtin__.print(f'Error: only one instance of {LogPrint.__name__} allowed')
            return None
        else:
            return super().__new__(cls)

    def __init__(self, file_name='log.txt', fw_mode='w'):
        '''
        Initializes the class and opens the log file.
        :param file_name: File name (default 'log.txt')
        :param fw_mode: Write mode (default 'w')
        '''
        LogPrint._ninst += 1  # register instance
        self.file_hnd = None  # file handle
        self.fw_mode = fw_mode  # write mode
        self.file_name = file_name  # file name
        try:
            self.file_hnd = open(self.file_name, fw_mode)
        except IOError as e:
            print(e)

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

    # funtion to override standart print function
    def print(self, *args, mode='both', **kwargs):
        '''
        Method to override standart print() with
        :param args: see print() 
        :param mode: output target ['screen','file','both'] (default 'both')
        :param kwargs: see print() 
        '''
        if mode == 'both' or mode == 'screen':
            __builtin__.print(*args, **kwargs)  # screen output
        if mode == 'both' or mode == 'file':
            kwargs['file'] = self.file_hnd
            kwargs['flush'] = True  # for instant writing
            __builtin__.print(*args, **kwargs)  # file output


if __name__ == '__main__':
    ''' Usage 
    '''
    log_file = 'log.txt'
    log = LogPrint(file_name=log_file)  # create Logprint instance
    print = log.print  # override buildin print()

    print(f'This text should appear on screen and in log-file {log_file}', 99, sep=' <sep> ', end='<end>\n')
    print(f'This text should appear on screen only', 99, sep=' <sep> ', end='<end>\n', mode='screen')
    print(f'This text should appear on log-file only', 99, sep=' <sep> ', end='<end>\n', mode='file')

    # creating a second instance fails
    log1 = LogPrint(file_name=log_file)
