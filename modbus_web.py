import time

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

# request.sid 連線房間


app = Flask(__name__)
socketio = SocketIO(app)

# 指定要发送数据的IP地址
target_ip = "192.168.1.100"  # 替换为你的目标IP地址

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
    print(ip, port, request.sid,  '-----------')
    # TODO 建立並執行連線

    # client = ModbusTcpClient(ip, port=int(port))
    # connection = client.connect()
    # if not connection:
    #     print(f"無法建立連線")


    # emit('status_response', {'data': data}, room=request.sid)

@socketio.on('disconnect_modbus')
def disconnect_modbus():
    print(request.sid,  '-----------')
    # TODO 斷開連線 刪除線程


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected', request.sid)
    # TODO 斷開連線 刪除線程




if __name__ == '__main__':
    socketio.run(app, debug=True)