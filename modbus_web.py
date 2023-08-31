from threading import Thread, Event
import time

from engineio.async_drivers import threading # * 替代解決辦法 socketio使用threading 打包才能執行
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
    modbus_connect_room[request.sid].point_data = data

class ModbusThread(Thread):
    def __init__(self, ip, port, room):
        super(ModbusThread, self).__init__()
        self.ip = ip
        self.port = port
        self.room = room
        self.exit_signal = Event()
        self.point_data = {'point_type': '3', 'slave': '1', 'point_data': {'1': {'log': 0, 'title': '', 'address': '3000', 'data_type': '1', 'bit_num': '64'}}}

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

                point_type = self.point_data.get('point_type', '3')
                slave = self.point_data.get('slave', '1')
                if point_type == '1':
                    read_funt = client.read_coils
                elif point_type == '2':
                    read_funt = client.read_discrete_inputs
                elif point_type == '4':
                    read_funt = client.read_input_registers
                else:
                    read_funt = client.read_holding_registers


                while not self.exit_signal.is_set():
                    point_data = self.point_data.get('point_data', {})
                    if len(point_data):

                        result = read_funt(1, count=10, slave=int(slave))
                        # TODO 目前進度



                    time.sleep(1)

        finally:
            # print('斷開連線', self.room)
            del modbus_connect_room[self.room]
            print("剩餘連線數:", len(modbus_connect_room))
            



if __name__ == '__main__':
    socketio.run(app, debug=True)