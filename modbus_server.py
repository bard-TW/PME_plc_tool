import asyncio
import random
import signal
import struct
import threading
import time

from pymodbus import Framer
from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusSlaveContext)
from pymodbus.server import ModbusTcpServer


def float_to_registers(value):
    """Converts a float value to two 16-bit integer values."""
    int_value = struct.unpack('!I', struct.pack('!f', value))[0]
    return byte32_to_byte16(int_value)

def registers_to_float(high_word, low_word):
    """Converts two 16-bit integer values to a float value."""
    int_value = (high_word << 16) | low_word
    return struct.unpack('!f', struct.pack('!I', int_value))[0]

def uint32_to_registers(uint_val):
    # 使用位运算将uint_val转换为32位寄存器值
    register_val = uint_val & 0xFFFFFFFF
    return byte32_to_byte16(register_val)

def byte32_to_byte16(byte32):
    byte_1 = byte32 & 0xFFFF  # 低位元
    byte_2 = (byte32 >> 16) & 0xFFFF  # 高位元
    return byte_1, byte_2

def raise_graceful_exit(*_args):
    """Enters shutdown mode"""
    print("receiving shutdown signal now")
    raise SystemExit


class Manipulator:
    """Class for the Modbus server and data manipulation."""

    def __init__(self):
        self.server = None
        self.block = ModbusSequentialDataBlock(3000, [0] * 100)

    def server_request_tracer(self, request, *_addr):
        """Trace requests made to the server."""
        print(f"---> 追蹤: {request}")

    def server_response_manipulator(self, response):
        """Manipulate the server response."""
        return response, False

    async def setup(self):
        """Set up the Modbus server."""

        context = ModbusServerContext(slaves=ModbusSlaveContext(hr=self.block))
        self.server = ModbusTcpServer(
            context,
            Framer.SOCKET,
            None,
            ("127.0.0.1", 5020),
            request_tracer=self.server_request_tracer,
            response_manipulator=self.server_response_manipulator,
        )

    async def run(self):
        """Run the Modbus server."""
        await self.server.serve_forever()


def job(server, exit_signal):
    """Simulate value updates."""
    number = 0
    while not exit_signal.is_set():
        number += int(random.uniform(0, 20))
        high_word, low_word = uint32_to_registers(number)
        server.block.setValues(2, [low_word, high_word])
        time.sleep(1)


async def main():
    """Main function to run the Modbus server."""
    try:
        server = Manipulator()

        signal.signal(signal.SIGINT, raise_graceful_exit)
        exit_signal = threading.Event()
        t = threading.Thread(target=job, args=(server, exit_signal,))
        t.start()

        await server.setup()
        await server.run()
    finally:
        exit_signal.set()
        t.join()


if __name__ == "__main__":
    asyncio.run(main(), debug=False)  # pragma: no cover
