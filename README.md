# Python J-Link RTT Viewer

> [SEGGER's Real Time Transfer (RTT)](https://www.segger.com/products/debug-probes/j-link/technology/about-real-time-transfer/) is the new technology for interactive user I/O in embedded applications. It combines the advantages of SWO and semihosting at very high performance.

SEGGER already provides [J-Link RTT Viewer](https://www.segger.com/products/debug-probes/j-link/technology/about-real-time-transfer/#j-link-rtt-viewer) tool for viewing the RTT output, however despite being practical the tool has limited scrollback and its _Scroll to the end_ cannot be paused.
Theferore if one wish to look back at some output line, the first problem is that this line may already be out of the 100-lines scrollback limit, and even it is not, every new received message will make the terminal jump to the end.

This script uses [pylink](https://github.com/square/pylink) library to load `JLinkARM.dll` and directly use the J-Link device, therefore removing requirement to run J-Link RTT Viewer simultaneously and connecting via telnet. The downside to this approach is noticeable performance decrease - first, the maximum clock speed is limited to 12 kHz and second, polling method is used for checking the received data (lack of asyncio API).


More features are pending, first one being colored output, then filtering (Logcat style) using PyQT. 
