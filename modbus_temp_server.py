
import argparse
import asyncio
import logging
import signal
import struct
import threading
import time

from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusSlaveContext)
from pymodbus.server.async_io import ModbusTcpServer

logging.basicConfig()
_logger = logging.getLogger(__file__)

def float_to_registers(value):
    # 將浮點數轉換成 32 位元整數，然後拆分成兩個 16 位元整數
    int_value = struct.unpack('!I', struct.pack('!f', value))[0]
    high_word = (int_value >> 16) & 0xFFFF
    low_word = int_value & 0xFFFF
    return high_word, low_word

def registers_to_float(high_word, low_word):
    # 將兩個 16 位元整數合併成一個 32 位元整數，然後轉換成浮點數
    int_value = (high_word << 16) | low_word
    return struct.unpack('!f', struct.pack('!I', int_value))[0]

def raise_graceful_exit(*_args):
    """Enters shutdown mode"""
    _logger.info("receiving shutdown signal now")
    raise SystemExit


class SerialForwarderTCPServer:
    """SerialRTU2TCP Forwarder Server"""
    def __init__(self):
        """Initialize the server"""
        self.server = None
        self.block = ModbusSequentialDataBlock(3000, [0]*100)  # 在這裡您可以設定您的資料點數量和初始值

    async def run(self):
        """Run the server"""
        port, baudrate, server_port, server_ip, slaves = get_commandline()
        # client = ModbusSerialClient(method="rtu", port=port, baudrate=baudrate)
        message = f"RTU bus on {port} - baudrate {baudrate}"
        _logger.info(message)

        # float_value = 0
        # high_word, low_word = float_to_registers(float_value)
        # self.block.setValues(3002, [high_word, low_word])

        store = ModbusSlaveContext(di=None, co=None, hr=self.block, ir=None)
        context = ModbusServerContext(slaves=store, single=True)
        self.server = ModbusTcpServer(
            context,
            address=(server_ip, server_port),
        )
        message = f"serving on {server_ip} port {server_port}"
        _logger.info(message)
        message = f"listening to slaves {context.slaves()}"

        _logger.info(message)
        await self.server.serve_forever()

    async def stop(self):
        """Stop the server"""
        if self.server:
            await self.server.shutdown()
            _logger.info("TCP server is down")


def get_commandline():
    """Read and validate command line arguments"""
    parser = argparse.ArgumentParser(description="Command line options")
    parser.add_argument(
        "--log",
        choices=["critical", "error", "warning", "info", "debug"],
        help="set log level, default is info",
        default="info",
        type=str,
    )
    parser.add_argument(
        "--port", help="RTU serial port", default="/dev/ttyUSB0", type=str
    )
    parser.add_argument("--baudrate", help="RTU baudrate", default=9600, type=int)
    parser.add_argument("--server_port", help="server port", default=5020, type=int)
    parser.add_argument("--server_ip", help="server IP", default="127.0.0.1", type=str)
    parser.add_argument(
        "--slaves", help="list of slaves to forward", type=int, nargs="+"
    )
    args = parser.parse_args()
    # set defaults
    _logger.setLevel(args.log.upper())
    if not args.slaves:
        args.slaves = {1, 2, 3}
    return args.port, args.baudrate, args.server_port, args.server_ip, args.slaves


import random
def job(server, exit_signal):
    while not exit_signal.is_set():
        float_value = random.uniform(10, 40)
        high_word, low_word = float_to_registers(float_value)
        server.block.setValues(3002, [high_word, low_word])
        time.sleep(10)


if __name__ == "__main__":
    server = SerialForwarderTCPServer()
    try:
        signal.signal(signal.SIGINT, raise_graceful_exit)

        exit_signal = threading.Event()
        t = threading.Thread(target=job, args = (server, exit_signal, ))
        t.start()

        asyncio.run(server.run())
    finally:
        exit_signal.set()
        t.join()
        asyncio.run(server.stop())
