# import subprocess
import time
from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from threading import Event, Thread

from engineio.async_drivers import \
    threading  # * 替代解決辦法 socketio使用threading 打包才能執行
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from ping3 import ping, verbose_ping
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
def update_point_data(datas, mode=''):
    if request.sid not in modbus_connect_room:
        return

    if mode == 'all':
        modbus_connect_room[request.sid].point_data = {}
    for data in datas:
        modbus_connect_room[request.sid].point_data[data['id']] = data

    point_list = []
    for key, value in modbus_connect_room[request.sid].point_data.items():
        data_type = value.get('data_type', 'int32')
        point = int(value.get('point', 3000))
        point_list.append(point)
        if data_type[-2:] == '32':
            point_list.append(point+2)
        elif data_type[-2:] == '64':
            point_list.append(point+4)
    grouped_numbers = group_nearby_numbers(point_list)
    modbus_connect_room[request.sid].grouped_numbers = grouped_numbers

def group_nearby_numbers(numbers: list):
    # 演算法, 變更請小心
    # 將list 根據數字 區分成多個list (ex: [3, 2, 70, 10, 50, 65, 1] >> [[1, 2, 3, 10], [50], [65, 70]])
    # threshold 閥值 數字超過多少 會換下一個list
    threshold = 10
    numbers.sort()

    result = []
    current_group = []
    for num in numbers:
        if not current_group:
            current_group.append(num)
        elif num - current_group[-1] <= threshold:
            current_group.append(num)
        else:
            result.append(current_group)
            current_group = [num]
    if current_group:
        result.append(current_group)
    return result


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
        self.grouped_numbers = []

    def test_connection(self, client:ModbusTcpClient):
        connection = client.connect()
        error_msg = ''
        if not connection:
            error_msg += 'step 1. modbus 連線失敗\n'
            with app.app_context():
                emit('connect_modbus', {'progress': "50%",  "msg": "ping測試"}, namespace='/', broadcast=True, room=self.room)
            
            time.sleep(1)
            is_ping = ping_ip(self.ip)
            if is_ping == True:
                error_msg += 'step 2. ping 成功\n'
            else:
                error_msg += 'step 2. ping 失敗\n'

            with app.app_context():
                emit('connect_modbus', {'progress': "75%",  "msg": "嘗試連線"}, namespace='/', broadcast=True, room=self.room)
            connection = client.connect()

        if not connection:
            with app.app_context():
                error_msg += 'step 3. modbus 第2次連線失敗'
                emit('connect_modbus_error', {'data': error_msg}, namespace='/', broadcast=True, room=self.room)
            return False
        return True


    def run(self):
        client = ModbusTcpClient(self.ip, port=int(self.port), timeout=10) # timeout 10 好像是Udp的設定??
        try:
            if self.test_connection(client) == False:
                return

            with app.app_context():
                emit('connect_modbus_success', {'data': 'modbus 連線成功'}, namespace='/', broadcast=True, room=self.room)

            while not self.exit_signal.is_set():
                for x in range(self.time_sleep, 0, -1):
                    time.sleep(1)
                    current_time = time.localtime()
                    if x > self.time_sleep or self.exit_signal.is_set():
                        break

                if self.point_type == '1':
                    read_funt = client.read_coils
                elif self.point_type == '2':
                    read_funt = client.read_discrete_inputs
                elif self.point_type == '4':
                    read_funt = client.read_input_registers
                else:
                    read_funt = client.read_holding_registers

                if len(self.point_data) == 0:
                    continue

                grouped_registers = []
                for numbers in self.grouped_numbers:
                    count = numbers[-1] - numbers[0]
                    count = 1 if count == 0 else count
                    result = read_funt(numbers[0]-1, count=count, slave=self.slave) # 修正為從0開始
                    grouped_registers.append(result.registers)

                print('點位分區:', self.grouped_numbers)
                print('分區資料:', grouped_registers)

                history_data = {}
                for key, value in self.point_data.items():
                    is_log = value.get('is_log', False)
                    # title = value.get('title', '')
                    point = int(value.get('point', 3000))
                    data_type = value.get('data_type', 'int32')

                    for i, array in enumerate(self.grouped_numbers):
                        if point not in array:
                            continue
                        registers = grouped_registers[i]
                        start_list_point1 = point - array[0]
                        break

                    if data_type[-2:] == '16':
                        count = 1
                    elif data_type[-2:] == '32':
                        count = 2
                    elif data_type[-2:] == '64':
                        count = 4

                    parser_list = registers[start_list_point1: start_list_point1+count]

                    data_sort = value.get('data_sort', "1")
                    if data_sort == "2":
                        parser_list = parser_list[::-1]
                    scale = int(value.get('scale', "1"))
                    decimal = int(value.get('decimal', "0"))

                    try:
                        decoder = BinaryPayloadDecoder.fromRegisters(parser_list, byteorder=Endian.BIG, wordorder=Endian.LITTLE)
                        if parser_list == []:
                            active_power = ''
                        elif data_type == 'int16':
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
                            active_power = decoder.decode_16bit_float()
                        elif data_type == 'float32':
                            active_power = decoder.decode_32bit_float()
                        elif data_type == 'float64':
                            active_power = decoder.decode_64bit_float()

                        active_power = active_power / scale
                        # active_power = round(active_power, decimal) # 無條件捨去

                        active_power = f"{active_power:.{decimal}f}"

                    except Exception as e:
                        # print(e)
                        active_power = "異常"
                    self.point_data[key]['now_value'] = active_power

                    if is_log:
                        history_data[key] = active_power

                with app.app_context():
                    emit('modbus_value', self.point_data, namespace='/', broadcast=True, room=self.room)
                    if history_data:
                        history_data['date_time'] = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
                        print(history_data)
                        emit('update_history', history_data, namespace='/', broadcast=True, room=self.room)

        finally:
            # print('斷開連線', self.room)
            client.close()
            del modbus_connect_room[self.room]
            print("剩餘modbus連線數:", len(modbus_connect_room))

def ping_ip(ip_address):
    response_time = ping(ip_address)
    if response_time is not None:
        return True
    else:
        return False

if __name__ == '__main__':
    socketio.run(app, debug=True)