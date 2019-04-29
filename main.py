__author__ = "Bojan Potočnik"

import ctypes
import os
import telnetlib
from collections.abc import Iterator
from typing import Union, Type


class SeggerRTTListener(Iterator):
    def __init__(self):
        self.telnet = telnetlib.Telnet()  # type: telnetlib.Telnet

    def __enter__(self):
        self.telnet.open("127.0.0.1", 19021)
        print(f"SeggerRTTListener connected to {self.telnet.host}:{self.telnet.port}.")
        return self

    def read_blocking(self) -> str:
        return self.telnet.read_some().decode()

    def __next__(self) -> Union[str, Type[StopIteration]]:
        """Read line, blocking mode"""
        if not self.connected:
            return StopIteration
        # Wait for new line indefinitely, remove newline characters at the end and convert it to string
        return self.telnet.read_until("\r\n".encode('ascii'))[:-2].decode()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.telnet.close()

    @property
    def connected(self) -> bool:
        return self.telnet.get_socket().fileno() != -1


def main() -> None:
    with SeggerRTTListener() as listener:
        for line in listener:
            print(line)


if __name__ == '__main__':
    if os.name == 'nt':
        # Running on Windows, enable console colors
        # ENABLE_PROCESSED_OUTPUT = 0x0001
        # ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x01 | 0x02 | 0x04)

    main()
