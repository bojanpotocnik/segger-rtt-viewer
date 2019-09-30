# Python J-Link RTT Client

> [SEGGER's Real Time Transfer (RTT)](https://www.segger.com/products/debug-probes/j-link/technology/about-real-time-transfer/) is the new technology for interactive user I/O in embedded applications. It combines the advantages of SWO and semihosting at very high performance.

SEGGER already provides [J-Link RTT Viewer](https://www.segger.com/products/debug-probes/j-link/technology/about-real-time-transfer/#j-link-rtt-viewer) tool for viewing the RTT output, however despite being practical the tool has limited scrollback, its _Scroll to the end_ cannot be paused and it misses some output when _a lot_ of debug is printed using the highest interface speeds.
Therefore if one wish to look back at some output line, the first problem is that this line may already be out of the 100-lines scrollback limit, and even it is not, every new received message will make the terminal jump to the end.

This script outputs the data to the standard console output, which can have any scrollback set and can be (un)paused with right-clicking.

In addition, write functionality can be used to interact with the backend when supported by the platform (e.g. with [Nordic Command Line Interface (CLI) RTT transfer](https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.sdk5.v15.0.0%2Fgroup__nrf__cli__rtt__config.html)) (_thanks to [vilvo](https://github.com/bojanpotocnik/segger-rtt-viewer/pull/2)_).

**Note**: J-Link driver/server **must be running** for this script to work. This can be done by:
 - using _J-Link Commander_ (preferred, more lightweight) with command `JLink -Device <DEVICE> -If <IF> -AutoConnect 1 -Speed <kHz>` (e.g. `JLink.exe -Device NRF52840_xxAA -AutoConnect 1 -If SWD -Speed 50000`)
 - running the above mentioned _J-Link RTT Viewer_ (output will not be visible in _RTT Viewer_ as it is automatically redirected when any telnet client connects)

One can then use tool such as [RBTray](http://rbtray.sourceforge.net/) to "minimize" the _J-Link Commander_/_RTT Viewer_ window to the system tray.

Branch [pylink](https://github.com/bojanpotocnik/segger-rtt-viewer/tree/pylink) removes this requirement with the cost of lower performance.

<br>

Contributions and pull requests are welcome!
Due to lack of free time, the development of this project is not as active as I originally intended/wished (my TODO: colored output, filtering (by debug levels, colors, RegEx) using PyQT, ...).
