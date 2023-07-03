
import os
from argparse import ArgumentParser
from xml.etree import ElementTree as ET

import pandas as pd


def get_modbus_address_df(file_name, file_path):
    modbus_df = pd.read_csv(f'{file_path}\{file_name}.csv')
    modbus_df = modbus_df.fillna(0)
    modbus_df.set_index(keys=["id"], inplace=True)
    for column in modbus_df.columns:
        modbus_df[column] = pd.to_numeric(modbus_df[column], downcast='integer')
    return modbus_df

def get_th_value_df(file_name, file_path):
    if os.path.isfile(f'{file_path}\{file_name}_th.csv'):
        th_df = pd.read_csv(f'{file_path}\{file_name}_th.csv', encoding='big5')
        th_df = th_df.fillna(0)
        th_df.set_index(keys=["name"], inplace=True)

        for column in th_df.columns:
            th_df[column] = pd.to_numeric(th_df[column], downcast='integer')
    else:
        th_df = pd.DataFrame()
    return th_df

def get_format_df():
    if os.path.isfile(f'plc_format.csv'):
        format_df = pd.read_csv(f'plc_format.csv')
        format_df.set_index(keys=["name"], inplace=True)
    else:
        format_df = pd.DataFrame()
    return format_df

def get_value(df, row, column, default_value):
    try:
        value = df.at[row, column]
        if pd.notna(value):
            return value
    except KeyError:
        pass
    return default_value

def set_max_th_to_ion_summary_df(ion_detail_df, ion_summary_df, th_df):
    # 從現有的已分配的th值，比對預設最大的值，在總標中填入最大值
    for columns in th_df.columns[1:]:
        df = ion_detail_df[ion_detail_df['default_name'] == columns]
        if len(df):
            column = ion_summary_df[ion_summary_df['class_id'] == df.iloc[0].class_id].iloc[0]
            if ion_summary_df.loc[column.name, 'max_index'] <= th_df[columns].max():
                ion_summary_df.loc[column.name, 'max_index'] = th_df[columns].max()

def set_data_to_ion_xml(ion_root, ion_namespaces, th, class_id, mame, default_name):
    x = ion_root.find(f'.//t:ION[@t:H="{class_id}"]', ion_namespaces)
    ion = x.find(f'.//t:ION[@t:N="{default_name}"]', ion_namespaces)
    # print(ion.attrib)
    new_ion = ET.SubElement(x[0], 't:ION', attrib=ion.attrib) # 本身就會自己建立
    new_ion.set("{x-schemas:x-pmlsystem:/schemas/tree-ionobjs.0.4.xml}N", str(mame))
    new_ion.set("{x-schemas:x-pmlsystem:/schemas/tree-ionobjs.0.4.xml}H", str(th))
    # x[0].append(new_ion)
    # print(new_ion.attrib)

def set_data_to_xml(xml_root, format_df, mame, default_name, th, ModbusAddress):
    format_name = get_value(format_df, default_name, 'format', '')
    scale = get_value(format_df, default_name, 'Scale', '')
    element = ET.SubElement(xml_root, 'ModbusInfo', attrib={
        'IONHandle': str(th),
        'Name': mame,
        'ModbusAddress': str(ModbusAddress),
        'RequestType': 'R',
        'Format': format_name,
        })
    if scale:
        element.set('Scale', str(scale))

def save_ion_xml(ion_tree, fimename='lab1.xml'):
    ET.indent(ion_tree, space="\t")
    ion_tree.write(fimename, xml_declaration=True, encoding='utf-8')

    with open(fimename, 'r', encoding='utf-8') as f:
        data = f.read()
        data = data.replace('ns1:', 't:')
        data = data.replace('xmlns:ns0', 'xmlns')
        data = data.replace('xmlns:ns1', 'xmlns:t')
        data = data.replace(' /', '/')
        data = data.replace('ns0:XMLIONTree', 'XMLIONTree')

    with open(fimename, 'w', encoding='utf-8') as f:
        f.write(data)

def save_xml(xml_tree, fimename='xml1.xml'):
    ET.indent(xml_tree, space="\t")
    xml_tree.write(fimename, xml_declaration=True, encoding='utf-8')
    with open(fimename, 'r', encoding='utf-8') as f:
        data = f.read()
        data = data.replace('xmlns:ns0', 'xmlns')
        data = data.replace(' /', '/')
        data = data.replace('ns0:', '')

    with open(fimename, 'w', encoding='utf-8') as f:
        f.write(data)

def main(file_name, file_path):
    # 讀取資料
    ion_detail_df = pd.read_csv('PLC_data/ion_detail.csv')
    ion_summary_df = pd.read_csv('PLC_data/ion_summary.csv')
    modbus_df = get_modbus_address_df(file_name, file_path)
    th_df = get_th_value_df(file_name, file_path)
    format_df = get_format_df()
    set_max_th_to_ion_summary_df(ion_detail_df, ion_summary_df, th_df)

    # ion 的 xml 讀取
    ion_xmifile = 'PLC_data/ExampleDeviceType.ion.xml'
    ion_tree = ET.parse(ion_xmifile)
    ion_root = ion_tree.getroot()
    ion_namespaces = {'t': 'x-schemas:x-pmlsystem:/schemas/tree-ionobjs.0.4.xml'}

    # xml 讀取
    xml_xmifile = 'PLC_data/ExampleDeviceType.xml'
    xml_tree = ET.parse(xml_xmifile)
    xml_root = xml_tree.getroot()

    logic_text = '"Logical Device Name","Logical Device Type","Physical Device Name","Physical Device Type","Input Register","Output Measurement","Handle"\n'
    for index in modbus_df.index:
        for columns in modbus_df.columns:
            mame = f"{columns} ({index})"
            ModbusAddress = modbus_df.loc[index, columns]

            # tp 值
            df = ion_detail_df[ion_detail_df['default_name'] == columns]
            class_id = df.iloc[0].class_id # tp

            th = 0
            if pd.notna(ModbusAddress):
                # 已分配
                th = get_value(th_df, index, columns, 0) # th資料表 取值

                # 未分配
                if th == 0 and ModbusAddress !=0:
                    column = ion_summary_df[ion_summary_df['class_id'] == class_id].iloc[0]
                    ion_summary_df.loc[column.name, 'max_index'] += 1
                    th = ion_summary_df.loc[column.name, 'max_index']
                    th_df.loc[index, columns] = th

            output_Measurement = get_value(th_df, index, 'output_Measurement', '') # 取中文項目名稱

            set_data_to_ion_xml(ion_root, ion_namespaces, th, class_id, mame, columns)
            set_data_to_xml(xml_root, format_df, mame, columns, th, ModbusAddress)
            logic_text += f'"{index}","","","","{mame}","{output_Measurement}",{th}\n'

    th_df.index.name='name'
    th_df.to_csv(f'{file_path}\{file_name}_th.csv', encoding='big5') # 分配過的th值 存檔
    save_ion_xml(ion_tree, f"{file_path}\{file_name}.ion")
    save_xml(xml_tree, f"{file_path}\{file_name}.xml")
    with open(f'{file_path}\{file_name}_output_logic.csv', 'w', encoding='big5') as f:
        f.write(logic_text)


def createArgumentParser():
    """解析參數"""
    parser = ArgumentParser()
    parser.add_argument("-f", help="檔案名稱(不要含附檔名)", dest="file_name", default=None)
    parser.add_argument("-p", help="檔案路徑", dest="file_path", default='.')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = createArgumentParser()
    main(args.file_name, args.file_path)
    print('處理完成')
