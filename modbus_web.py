import time
from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from threading import Event, Thread

from engineio.async_drivers import \
    threading  # * 替代解決辦法 socketio使用threading 打包才能執行
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

# request.sid 連線房間

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")

modbus_connect_room = {} # sid: obj

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected', request.sid)

    # # 模拟获取数据，实际情况中可以替换为获取实际数据的逻辑
    # data = f"Data for {target_ip}"
    # time.sleep(3)
    # emit('status_response', {'data': data}, room=request.sid)
    return jsonify(
        {"response": "ok"}
    )


@socketio.on('connect_modbus')
def connect_modbus(ip, port):
    modbusThread = ModbusThread(ip, port, request.sid)
    modbusThread.start()
    modbus_connect_room[request.sid] = modbusThread
    print(modbus_connect_room)
    # emit('status_response', {'data': data}, room=request.sid)

@socketio.on('disconnect_modbus')
def disconnect_modbus():
    if request.sid in modbus_connect_room:
        modbus_connect_room[request.sid].exit_signal.set()

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in modbus_connect_room:
        modbus_connect_room[request.sid].exit_signal.set()

@socketio.on('modbus_point_data')
def handle_point_data(data):
    if request.sid in modbus_connect_room:
        modbus_connect_room[request.sid].point_data = data

class ModbusThread(Thread):
    def __init__(self, ip, port, room):
        super(ModbusThread, self).__init__()
        self.ip = ip
        self.port = port
        self.room = room
        self.exit_signal = Event()
        self.point_data = {}

    def run(self):
        client = ModbusTcpClient(self.ip, port=int(self.port))
        connection = client.connect()

        try:
            if not connection:
                with app.app_context():
                    emit('connect_modbus_error', {'data': 'modbus 無法建立連線'}, namespace='/', broadcast=True, room=self.room)
            else:
                with app.app_context():
                    emit('connect_modbus_success', {'data': 'modbus 連線成功'}, namespace='/', broadcast=True, room=self.room)

                while not self.exit_signal.is_set():
                    point_type = self.point_data.get('point_type', '3')
                    slave = int(self.point_data.get('slave', '1'))
                    if point_type == '1':
                        read_funt = client.read_coils
                    elif point_type == '2':
                        read_funt = client.read_discrete_inputs
                    elif point_type == '4':
                        read_funt = client.read_input_registers
                    else:
                        read_funt = client.read_holding_registers

                    point_data = self.point_data.get('point_data', {})
                    if len(point_data):
                        for key, value in point_data.items():
                            # print(key, value)
                            log = value.get('log', 0)
                            title = value.get('title', '')
                            address = int(value.get('address', 3000))
                            data_type = value.get('data_type', 'int32')
                            if data_type[-2:] == '16':
                                count = 1
                            elif data_type[-2:] == '32':
                                count = 2
                            elif data_type[-2:] == '64':
                                count = 4

                            result = read_funt(address, count=count, slave=slave)
                            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Big)
                            if data_type == 'int16':
                                active_power = decoder.decode_16bit_int()
                            elif data_type == 'int32':
                                active_power = decoder.decode_32bit_int()
                            elif data_type == 'int64':
                                active_power = decoder.decode_64bit_int()
                            elif data_type == 'uint16':
                                active_power = decoder.decode_16bit_uint()
                            elif data_type == 'uint32':
                                active_power = decoder.decode_32bit_uint()
                            elif data_type == 'uint64':
                                active_power = decoder.decode_64bit_uint()
                            elif data_type == 'float16':
                                active_power = '{:f}'.format(decoder.decode_16bit_float())
                            elif data_type == 'float32':
                                active_power = '{:f}'.format(decoder.decode_32bit_float())
                            elif data_type == 'float64':
                                active_power = '{:f}'.format(decoder.decode_64bit_float())

                            with app.app_context():
                                emit('modbus_value', {'key': key, 'data': active_power}, namespace='/', broadcast=True, room=self.room)


                        # TODO 目前進度



                    time.sleep(1)

        finally:
            # print('斷開連線', self.room)
            del modbus_connect_room[self.room]
            print("剩餘modbus連線數:", len(modbus_connect_room))
            



if __name__ == '__main__':
    socketio.run(app, debug=True)