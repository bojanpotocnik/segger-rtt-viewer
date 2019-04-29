__author__ = "Bojan Potočnik"

import ctypes
import os
from collections.abc import Iterator
from typing import Union, Type, Optional

# noinspection PyPackageRequirements
from pylink import JLink


class SeggerRTTListener(Iterator):
    def __init__(self,
                 device_name: Optional[str] = None,
                 speed: Union[int, str] = 'adaptive',
                 auto_update_fw: bool = False):
        """
        Initialize the RTT viewer.

        :param device_name:    Name of the target device (chip). If not provided and there is no saved device from
                               any previous run, stdin will be used to ask for device name.
        :param speed:          See :func:`pylink.jlink.JLink.connect`.
        :param auto_update_fw: Whether the emulator FW shall be automatically updated if the newer
                               version is available. If set to False, newer FW is ignored as dialogs
                               are suppressed and this information is hidden.
        """
        self._jlink = JLink()
        self._jlink_device_name = device_name
        self._jlink_speed = speed

        self._jlink.disable_dialog_boxes()
        # disable_dialog_boxes enables SilentUpdateFW.
        self._jlink.exec_command("EnableAutoUpdateFW" if auto_update_fw else "DisableAutoUpdateFW")

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
                print(f"Last used device name '{device_name}' is not valid.")
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
        print(f"Using JLinkARM.dll v{self._jlink.version} on"
              f" J-Link v{self._jlink.hardware_version} running FW {self._jlink.firmware_version}"
              f"{' (outdated)' if self._jlink.firmware_outdated else ''}")

        chip_name = self._get_device_name()
        if not chip_name:
            raise ValueError("No device (chip) name provided")

        print(f"Connecting to {chip_name}"
              f" using {self._jlink_speed}{' kHz' if type(self._jlink_speed) is int else ''} speed"
              f" at {self._jlink.hardware_status.voltage} mV...")

        self._jlink.connect(chip_name=chip_name, speed=self._jlink_speed, verbose=True)
        return self

    def read_blocking(self) -> str:
        raise NotImplementedError()

    def __next__(self) -> Union[str, Type[StopIteration]]:
        """Read line, blocking mode"""
        if self.connected:
            self._jlink.close()
            return "TODO: Not implemented"
        # if not self.connected:
        #     return StopIteration
        # Wait for new line indefinitely, remove newline characters at the end and convert it to string
        # return self.telnet.read_until("\r\n".encode('ascii'))[:-2].decode()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._jlink.close()

    @property
    def connected(self) -> bool:
        return self._jlink.target_connected()


if __name__ == '__main__':
    if os.name == 'nt':
        # Running on Windows, enable console colors
        # ENABLE_PROCESSED_OUTPUT = 0x0001
        # ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x01 | 0x02 | 0x04)

    with SeggerRTTListener() as listener:
        for line in listener:
            print(line)
