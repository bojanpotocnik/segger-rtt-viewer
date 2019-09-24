import sys
import time
import typing

__author__ = "Bojan Potočnik"

import ctypes
import os
import telnetlib


class SeggerRTTListener:
    def __init__(self, host: str = "localhost", port: int = 19021):
        self.telnet = telnetlib.Telnet(timeout=1)  # type: telnetlib.Telnet
        self.host = host
        self.port = port
        try:
            self.telnet.open(self.host, self.port)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to {self.host}:{self.port}."
                f" Are you sure that the JLink is running?"
                f" You can run it with 'JLink -Device <DEVICE> -If <IF> -AutoConnect 1 -Speed <kHz>'"
                f", e.g. 'JLink --Device NRF52840_xxAA -If SWD -AutoConnect 1 -Speed 50000'"
            )
        # Bold green
        print("\x1B[1m\x1B[32m"
            f"{type(self).__name__} connected to {self.telnet.host}:{self.telnet.port}."
            "\x1B[0m")

    def read_blocking(self) -> str:
        """Read any available data and return it as-is."""
        while True:
            try:
                rx_data = self.telnet.read_very_eager()
            except ConnectionResetError:
                self.telnet.close()
                # Bold red
                return ("\x1B[1m\x1B[31m"
                        f"{type(self).__name__} disconnected from {self.host}:{self.port}."
                        "\x1B[0m")
            if rx_data:
                break
            time.sleep(0.01)
        try:
            return rx_data.decode('utf-8')
        except UnicodeDecodeError as e:
            print(f"While decoding {rx_data}: {e}", file=sys.stderr)
            return rx_data.decode('utf-8', errors='replace')

    def read_lines(self) -> typing.Iterator[str]:
        """Read line by line and strip all newline characters (\r\n) at the end."""
        while self.connected:
            # Wait for new line indefinitely, remove newline characters at the end and convert it to string.
            # Only wait for \n as some code uses \r\n as newline and other only \n.
            rx_data = ""
            while "\n" not in rx_data:
                rx_data += self.read_blocking()
            # Multiple lines can be received.
            for line in rx_data.split("\n"):
                yield line.strip("\r\n")

    def write_line(self, buffer) -> None:
        self.telnet.write(buffer + b"\n")

    def __iter__(self) -> typing.Iterator[str]:
        """Read (undetermined) fragments of received data and return it as-is."""
        while self.connected:
            yield self.read_blocking()

    def __del__(self):
        print("{}Connection to {}:{} closed{}".format("\x1B[1m\x1B[32m",
              self.telnet.host, self.telnet.port, "\x1B[0m"))
        self.telnet.close()

    @property
    def connected(self) -> bool:
        return self.telnet.sock and (not self.telnet.eof) and (self.telnet.get_socket().fileno() != -1)

    def __bool__(self) -> bool:
        return self.connected

def read(client):
    """ read only one once instead of using generator forever"""
    print(next(iter(client)), end="")

def main() -> None:
    """ main to demonstrate bi-directional (read and write) over Telnet to SEGGER J-Link RTT server
        write_line can be used on platforms which support bi-directional RTT transfer, e.g. Nordic CLI.
    """
    client = SeggerRTTListener()
    user_input_sent = False

    try:
        while(True):
            read(client)
            if not user_input_sent: # sent input only once and continue reading
                client.write_line(b"\t") # tab on Nordic RTT CLI shows available commands
                user_input_sent = True
    except KeyboardInterrupt:
        print("User requested keyboard interrupt")

if __name__ == '__main__':
    if os.name == 'nt':
        # Running on Windows, enable console colors
        # ENABLE_PROCESSED_OUTPUT = 0x0001
        # ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x01 | 0x02 | 0x04)

    main()
