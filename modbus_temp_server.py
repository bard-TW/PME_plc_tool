
import argparse
import asyncio
import random
import signal
import struct
import threading
import time

from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusSlaveContext)
from pymodbus.server.async_io import ModbusTcpServer


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
    print("receiving shutdown signal now")
    raise SystemExit


class TCPServer:
    def __init__(self):
        """Initialize the server"""
        self.server = None
        self.block = ModbusSequentialDataBlock(3000, [0]*100)  # 在這裡您可以設定您的資料點數量和初始值

    async def run(self):
        """Run the server"""
        server_port, server_ip = get_commandline()

        store = ModbusSlaveContext(hr=self.block)# di co ir hr
        context = ModbusServerContext(slaves=store, single=True)
        self.server = ModbusTcpServer(
            context,
            address=(server_ip, server_port),
        )
        await self.server.serve_forever()

    async def stop(self):
        """Stop the server"""
        if self.server:
            await self.server.shutdown()
            print("TCP server is down")


def get_commandline():
    """可輸入參數"""
    parser = argparse.ArgumentParser(description="Command line options")
    parser.add_argument("--server_port", help="server port", default=5020, type=int)
    parser.add_argument("--server_ip", help="server IP", default="127.0.0.1", type=str)
    args = parser.parse_args()
    return args.server_port, args.server_ip

def job(server, exit_signal):
    # 銜接氣象資料的地方
    while not exit_signal.is_set():
        float_value = random.uniform(10, 40)
        high_word, low_word = float_to_registers(float_value)
        server.block.setValues(3002, [high_word, low_word])
        time.sleep(1)


if __name__ == "__main__":
    server = TCPServer()
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
