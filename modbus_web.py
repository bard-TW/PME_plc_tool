import time
from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from threading import Event, Thread

from engineio.async_drivers import \
    threading  # * 替代解決辦法 socketio使用threading 打包才能執行
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from pymodbus.client import ModbusTcpClient, ModbusUdpClient
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
    if ip == '' or port == '':
        emit('connect_modbus_error', {'data': '輸入錯誤'}, room=request.sid)
        return
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

@socketio.on('update_point_data')
def update_point_data(datas):
    if request.sid in modbus_connect_room:
        for data in datas:
            print(data)
            modbus_connect_room[request.sid].point_data[data['id']] = data

@socketio.on('del_point_data')
def del_point_data(data):
    if request.sid in modbus_connect_room:
        if data['id'] in modbus_connect_room[request.sid].point_data:
            del modbus_connect_room[request.sid].point_data[data['id']]


@socketio.on('update_basic_data')
def update_basic_data(data):
    if request.sid in modbus_connect_room:
        ModbusObj:ModbusThread = modbus_connect_room[request.sid]
        ModbusObj.time_sleep = int(data.get('time_sleep', 1))
        ModbusObj.point_type = data.get('point_type', "3")
        ModbusObj.slave = int(data.get('slave', 1))
        modbus_connect_room[request.sid].basic_data = data


class ModbusThread(Thread):
    def __init__(self, ip, port, room):
        super(ModbusThread, self).__init__()
        self.ip = ip
        self.port = port
        self.room = room
        self.exit_signal = Event()
        self.time_sleep = 1
        self.point_type = '3'
        self.slave = 1
        self.point_data = {}

    def run(self):
        client = ModbusTcpClient(self.ip, port=int(self.port), timeout=3)
        # client = ModbusUdpClient(self.ip, port=int(self.port))
        connection = client.connect()

        try:
            if not connection:
                with app.app_context():
                    emit('connect_modbus_error', {'data': 'modbus 無法建立連線'}, namespace='/', broadcast=True, room=self.room)
            else:
                with app.app_context():
                    emit('connect_modbus_success', {'data': 'modbus 連線成功'}, namespace='/', broadcast=True, room=self.room)

                while not self.exit_signal.is_set():
                    if self.point_type == '1':
                        read_funt = client.read_coils
                    elif self.point_type == '2':
                        read_funt = client.read_discrete_inputs
                    elif self.point_type == '4':
                        read_funt = client.read_input_registers
                    else:
                        read_funt = client.read_holding_registers


                    if len(self.point_data):
                        for key, value in self.point_data.items():
                            log = value.get('log', 0)
                            title = value.get('title', '')
                            point = int(value.get('point', 3000))
                            data_type = value.get('data_type', 'int32')

                            if data_type[-2:] == '16':
                                count = 1
                            elif data_type[-2:] == '32':
                                count = 2
                            elif data_type[-2:] == '64':
                                count = 4

                            result = read_funt(point, count=count, slave=self.slave)

                            data_sort = value.get('data_sort', 1)
                            if data_sort == 2:
                                registers = result.registers[::-1]
                            else:
                                registers = result.registers

                            decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Big)
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
                            self.point_data[key]['now_value'] = active_power

                        with app.app_context():
                            emit('modbus_value', self.point_data, namespace='/', broadcast=True, room=self.room)

                    for x in range(self.time_sleep, 0, -1):
                        if x > self.time_sleep:
                            break
                        time.sleep(1)

        finally:
            # print('斷開連線', self.room)
            del modbus_connect_room[self.room]
            print("剩餘modbus連線數:", len(modbus_connect_room))


if __name__ == '__main__':
    socketio.run(app, debug=True)