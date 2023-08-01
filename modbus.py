import re
import time
from argparse import ArgumentParser
from multiprocessing import Pool, cpu_count, freeze_support

import pandas as pd
from pymodbus.client import ModbusTcpClient


def job(ip, port=502, device_id=1, address=6001, device_name='', modbus_point_type=3, number_of_polls=3, delay=1):
    NOT_CONNECTION = 0
    TIMEOUT = 0
    READ_VALUE_ERROR = 0
    SUCCESS = 0

    client = ModbusTcpClient(ip, port=port)

    if modbus_point_type == 1:
        memory_block = client.read_coils
    elif modbus_point_type == 2:
        memory_block = client.read_discrete_inputs
    elif modbus_point_type == 3:
        memory_block = client.read_holding_registers
    elif modbus_point_type == 4:
        memory_block = client.read_input_registers
    else:
        raise ValueError("Invalid modbus point type")

    for _ in range(number_of_polls):
        try:
            # 建立連線
            connection = client.connect()
            if not connection:
                print(f"{ip} {device_name} 無法建立連線")
                NOT_CONNECTION += 1
                continue

            result = memory_block(address, count=1, slave=device_id)

            if result.isError():
                print(f"{ip} {device_name} 讀取數據錯誤: {result}")
                READ_VALUE_ERROR += 1
            else:
                # 打印讀取到的數據
                value = result.registers[0]
                print(f"{ip} {device_name} 讀取到的數據: {value}")
                SUCCESS += 1

        except Exception as e:
            print(f"{ip} {device_name} 連線錯誤: {e}")
            TIMEOUT += 1

        finally:
            # 關閉客戶端連線 #TODO 常連結跑完才關閉
            client.close()
        time.sleep(delay)
    return {'ip': ip, 'device_id': device_id, 'NOT_CONNECTION': NOT_CONNECTION, 'TIMEOUT': TIMEOUT, 'READ_VALUE_ERROR': READ_VALUE_ERROR, 'SUCCESS': SUCCESS}

def main(file, modbus_point_type, number_of_polls, delay):
    df = pd.read_excel(file, sheet_name='modbus', dtype={'port': int, 'device_id': int, 'address': int})
    arg_list = []
    for row in df.itertuples():
        arg_list.append((row.ip, row.port, row.device_id, row.address, row.device_name, modbus_point_type, number_of_polls, delay))

    use_cpu_count = cpu_count()-1
    processes = use_cpu_count if use_cpu_count >= 1 else 1

    with Pool(processes=processes) as pool:
        results = pool.starmap(job, arg_list)

    for result in results:
        _factor_ip = df['ip']==result['ip']
        _factor_device_id = df['device_id']==result['device_id']
        dfIndex = df[_factor_ip & _factor_device_id].index
        df.loc[dfIndex, 'NOT_CONNECTION'] = result['NOT_CONNECTION']
        df.loc[dfIndex, 'TIMEOUT'] = result['TIMEOUT']
        df.loc[dfIndex, 'READ_VALUE_ERROR'] = result['READ_VALUE_ERROR']
        df.loc[dfIndex, 'SUCCESS'] = result['SUCCESS']
    df.to_excel(file, sheet_name='modbus', index=False)


def createArgumentParser():
    """解析參數"""
    parser = ArgumentParser()
    parser.add_argument("-u", "--url", help="192.168.1.1:502/1/6001 ip:port/device_id/address", dest="url")
    parser.add_argument("--device_name", help="設備名稱", dest="device_name", default='')
    parser.add_argument("--mpt", type=int, help="寄存器類型", dest="modbus_point_type", default=3)
    parser.add_argument("--nop", type=int, help="讀取次數", dest="number_of_polls", default=3)
    parser.add_argument("--delay", type=int, help="延遲秒數", dest="delay", default=1)
    parser.add_argument("-f", "--file", help="檔案", dest="file", default='')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    freeze_support() # 解決封裝exe後執行時，程序沒有被凍結的問題

    args = createArgumentParser()

    if args.url:
        pattern = r'(\d+\.\d+\.\d+\.\d+):(\d+)/(\d+)/(\d+)'
        match = re.match(pattern, args.url)

        if match:
            ip = match.group(1)
            port = int(match.group(2))
            device_id = int(match.group(3))
            address = int(match.group(4))
            result = job(ip, port, device_id, address, device_name=args.device_name, modbus_point_type=args.modbus_point_type, number_of_polls=args.number_of_polls, delay=args.delay)
            print(result)
        else:
            print('請填參數')
            exit()

    elif args.file:
        main(args.file, modbus_point_type=args.modbus_point_type, number_of_polls=args.number_of_polls, delay=args.delay)
    else:
        print('請填參數')
        exit()

