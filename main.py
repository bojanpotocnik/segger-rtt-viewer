import re
import sys
import time
import typing
import warnings

__author__ = "Bojan Potočnik"

import ctypes
import os
import telnetlib


class SeggerRTTClient:
    def __init__(self, host: str = "localhost", port: int = 19021):
        self.telnet = telnetlib.Telnet(timeout=1)  # type: telnetlib.Telnet
        self.host = host
        self.port = port
        self._opened = False

    # noinspection SpellCheckingInspection
    def open(self, parse_jlink_info: bool = True):
        """Connect to the JLink host."""
        try:
            self.telnet.open(self.host, self.port)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to {self.host}:{self.port}."
                " Are you sure that the JLink is running?"
                " You can run it with 'JLink -Device <DEVICE> -If <IF> -AutoConnect 1 -Speed <kHz>'"
                ", e.g. 'JLink --Device NRF52840_xxAA -If SWD -AutoConnect 1 -Speed 50000'"
            )
        self._opened = True

        # Bold/Bright green
        msg = "\x1B[32;1m" + f"{type(self).__name__} connected to {self.telnet.host}:{self.telnet.port}"
        if parse_jlink_info:
            # Wait for JLink information to be printed.
            # self.telnet.expect() could be used, but it throws error
            # `TypeError: cannot use a string pattern on a bytes-like object` because it executes
            # `m = list[i].search(self.cookedq)` where `self.cookedq` is bytes, not str.
            # Manual matching is done instead.
            # 3 newline characters are required for RegEx below to match.
            data = b''.join(self.telnet.read_until(b'\n', 0.1) for _ in range(3))
            match = re.match(r"SEGGER J-Link (V[\w.]+) - Real time terminal output\r?\n"
                             r"SEGGER J-Link ([\w .]+), SN=([\d]+)\r?\n"
                             r"Process: ([\w.\-]+)\r?\n", data.decode('utf-8')) if data else None
            if match:
                data = data[match.span()[1]:]  # Leave only the unused data in the buffer.
                # Bold/Bright blue
                msg += "\x1B[34;1m" + f" ('{match[3]}' {match[1]} using {match[2]} (SN {match[3]}))"
            # Put unrecognized/unused data back in the buffer (in front of any new data received in meantime).
            self.telnet.cookedq = data + self.telnet.cookedq
        print(msg + "\x1B[0m", flush=True)

    def close(self):
        """Close the connection, if opened."""
        if self._opened:
            self.telnet.close()
            self._opened = False
            # Bold/Bright magenta
            print("\x1B[35;1m"
                  f"Connection to {self.telnet.host}:{self.telnet.port} closed."
                  "\x1B[0m", flush=True)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def read_blocking(self) -> str:
        """Read any available data and return it as-is."""
        while True:
            try:
                rx_data = self.telnet.read_very_eager()
            except ConnectionResetError:
                # Bold red
                print("\x1B[31;1m"
                      f"{type(self).__name__} disconnected from {self.host}:{self.port}."
                      "\x1B[0m")
                self.close()
                return "\x00"
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

    def write_line(self, buffer: typing.Union[bytes, str]) -> None:
        if isinstance(buffer, str):
            buffer = buffer.encode('ascii')
        self.telnet.write(buffer + b"\n")

    def __iter__(self) -> typing.Iterator[str]:
        """Read (undetermined) fragments of received data and return it as-is."""
        while self.connected:
            yield self.read_blocking()

    def __del__(self):
        self.close()

    @property
    def connected(self) -> bool:
        return self.telnet.sock and (not self.telnet.eof) and (self.telnet.get_socket().fileno() != -1)

    def __bool__(self) -> bool:
        return self.connected


class SeggerRTTListener(SeggerRTTClient):
    """Class for backward compatibility of the @ref SeggerRTTClient."""

    def __init__(self, host: str = "localhost", port: int = 19021):
        warnings.warn(f"{type(self).__name__} is deprecated - use {SeggerRTTClient.__name__} instead.")
        super().__init__(host, port)


def read(client):
    """ read only one once instead of using generator forever"""
    print(next(iter(client)), end="")


def main__open_close() -> None:
    """ main to demonstrate bi-directional (read and write) over Telnet to SEGGER J-Link RTT server
        write_line can be used on platforms which support bi-directional RTT transfer, e.g. Nordic CLI.
    """
    client = SeggerRTTClient()
    client.open()
    user_input_sent = False

    try:
        while True:
            read(client)
            if not user_input_sent:  # sent input only once and continue reading
                client.write_line(b"\t")  # tab on Nordic RTT CLI shows available commands
                user_input_sent = True
    except KeyboardInterrupt:
        print("User requested keyboard interrupt")
    finally:
        # In this case calling close() is not strictly required as it will be called
        # automatically when the object is garbage collected, however this shall not be
        # relied upon - open()-ed resources shall always be close()-ed.
        client.close()


def main__context_manager() -> None:
    user_input_sent = False

    with SeggerRTTClient() as client:
        for line in client:
            print(line, end="")
            if not user_input_sent:  # Sent input only once and continue reading
                client.write_line(b"\t")  # Tab on Nordic RTT CLI shows available commands
                user_input_sent = True


if __name__ == '__main__':
    if os.name == 'nt':
        # Running on Windows, enable console colors
        # ENABLE_PROCESSED_OUTPUT = 0x0001
        # ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x01 | 0x02 | 0x04)

    main__context_manager()
    # main__open_close()
