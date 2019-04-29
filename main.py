import time

__author__ = "Bojan Potočnik"

import ctypes
import os
from collections.abc import Iterator
from typing import Union, Type, Optional

# noinspection PyPackageRequirements
from pylink import JLink, JLinkInterfaces, JLinkRTTException


class SeggerRTTListener(Iterator):
    def __init__(self,
                 device_name: Optional[str] = None,
                 speed: Union[int, str] = 'auto',  # JLink.MAX_JTAG_SPEED,
                 interface: JLinkInterfaces = JLinkInterfaces.SWD,
                 auto_update_fw: bool = False,
                 print_info: bool = True):
        """
        Initialize the RTT viewer.

        :param device_name:    Name of the target device (chip). If not provided and there is no saved device from
                               any previous run, stdin will be used to ask for device name.
        :param speed:          See :func:`pylink.jlink.JLink.connect`.
        :param interface:      Communication interface to use.
        :param auto_update_fw: Whether the emulator FW shall be automatically updated if the newer
                               version is available. If set to False, newer FW is ignored as dialogs
                               are suppressed and this information is hidden.
        :param print_info:     Whether to print various information (progress, device info, ...).
        """
        self._jlink_device_name = device_name
        self._jlink_speed = speed
        # noinspection PyTypeChecker
        self._jlink_interface = int(interface)

        self._jlink = JLink()
        self._jlink.disable_dialog_boxes()
        # disable_dialog_boxes enables SilentUpdateFW.
        self._jlink.exec_command("EnableAutoUpdateFW" if auto_update_fw else "DisableAutoUpdateFW")

        self._print_fn = print if print_info else (lambda *args, **kwargs: None)
        self._jlink_rtt_num_rx_buffers: int = 0

    def _validate_device_name(self, device_name: str) -> bool:
        return device_name.lower() in (self._jlink.supported_device(i).name.lower()
                                       for i in range(self._jlink.num_supported_devices()))

    def _get_device_name(self) -> Optional[str]:
        last_used_chip_name_fn = ".jlink_last_used_device_name"

        if not self._jlink_device_name:
            # Try to read last used device name from file
            try:
                with open(last_used_chip_name_fn) as f:
                    device_name = f.read().strip()
            except FileNotFoundError:
                device_name = None

            if device_name and not self._validate_device_name(device_name):
                self._print_fn(f"Last used device name '{device_name}' is not valid.")
                device_name = None

            if not device_name:
                print("Please enter target device (chip) name."
                      " Entry is not case sensitive and Enter can be pressed any time to print out all of the"
                      f" matching devices (out of {self._jlink.num_supported_devices()} supported).")
                # Do not query all of the devices, wait for at least first letter.
                devices = None
                dn = ""
                while not device_name:
                    input_dn = input(f"Chip name: {dn}")
                    if not input_dn:
                        continue
                    dn += input_dn
                    dn_lower = dn.lower()  # Avoid __getattribute__ on every iteration

                    # Build the list (actually dict to save indexes) of devices on first letter.
                    if not devices:
                        devices = list(filter(
                            lambda sd_: sd_.name.lower().startswith(dn_lower),
                            (self._jlink.supported_device(i) for i in range(self._jlink.num_supported_devices()))
                        ))

                    # Filter out all non-matching devices.
                    devices = [sd_ for sd_ in devices if sd_.name.lower().startswith(dn_lower)]

                    if not devices:
                        print(f"No supported devices found with name starting with '{dn}'")
                        return None

                    for count, sd in enumerate(devices):
                        print(f" {count:2d}: {sd.name} ({sd.manufacturer}"
                              f", {sd.FlashSize / 1024:.0f} kB Flash, {sd.RAMSize / 1024:.0f} kb RAM)")
                        if count > 50:
                            print(f"... and {len(devices) - count} more")
                            break

                    if len(devices) == 1:
                        device_name = devices[0].name
            self._jlink_device_name = device_name

        with open(last_used_chip_name_fn, 'w') as f:
            f.write(self._jlink_device_name)

        return self._jlink_device_name

    def __enter__(self):
        self._jlink.open()
        self._print_fn(f"Using JLinkARM.dll v{self._jlink.version} on"
                       f" J-Link v{self._jlink.hardware_version} running FW {self._jlink.firmware_version}"
                       f"{' (outdated)' if self._jlink.firmware_outdated else ''}")

        chip_name = self._get_device_name()
        if not chip_name:
            raise ValueError("No device (chip) name provided")

        self._print_fn(f"Connecting to {chip_name}"
                       f" using {self._jlink_speed}{' kHz' if type(self._jlink_speed) is int else ''} clock speed"
                       f" at {self._jlink.hardware_status.voltage} mV...")

        # Set SWD as the interface
        self._jlink.set_tif(self._jlink_interface)
        self._jlink.connect(chip_name=chip_name, speed=self._jlink_speed, verbose=True)
        self._jlink.rtt_start()
        # RTT must initialize with the target before retrieving more information.
        for _ in range(20):
            try:
                self._jlink_rtt_num_rx_buffers = self._jlink.rtt_get_num_up_buffers()
                break
            except JLinkRTTException as e:
                if "The RTT Control Block has not yet been found" in str(e):
                    time.sleep(0.1)
                else:
                    raise e

        # noinspection PyProtectedMember
        endian = int(self._jlink._device.EndianMode[0])
        endian = {0: "Little", 1: "Big"}.get(endian, f"Unknown ({endian})")
        self._print_fn(f"RTT (using {self._jlink_rtt_num_rx_buffers} RX buffers at {self._jlink.speed} kHz)"
                       f" connected to {endian}-Endian {self._jlink.core_name()}"
                       f" running at {self._jlink.cpu_speed() / 1e6:.3f} MHz")
        return self

    def read_blocking(self) -> str:
        while True:
            # Try reading all buffers until some data is available
            for i in range(self._jlink_rtt_num_rx_buffers):
                rx_data = self._jlink.rtt_read(i, self._jlink.MAX_BUF_SIZE)
                if rx_data:
                    return bytes(rx_data).decode('utf-8')
            time.sleep(0.01)

    def __next__(self) -> Union[str, Type[StopIteration]]:
        """Read line, blocking mode"""
        if not self.connected:
            return StopIteration
        # Wait for new line indefinitely, remove newline characters at the end and convert it to string
        rx_data = self.read_blocking()
        for line in rx_data.split("\n"):
            # Sometimes lines end with "\r\n", sometimes with "\n" only.
            return line.rstrip()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._jlink.rtt_stop()
            self._jlink.close()
        except JLinkRTTException:
            pass

    @property
    def connected(self) -> bool:
        return self._jlink.target_connected()


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
