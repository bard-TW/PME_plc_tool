from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent

import openpyxl
import pandas as pd


def filter_detector(data):
    if data.loc['max'] > 5 and data.loc['99%']*2 < data.loc['max']:
        return 1
    if data.loc['min'] < 0:
        return 1
    return 0


class ModeInterface(ABC):
    @abstractmethod
    def mode(self, describe_df:pd.DataFrame):
        pass


class OutlierDetectorMode(ModeInterface):
    def mode(self, describe_df):
        # 取出異常值模式
        describe_df.loc[:, 'threshold'] = describe_df.apply(filter_detector, axis=1)
        problem_describe_df = describe_df[describe_df['threshold'] == 1 ]
        return problem_describe_df


class AllOutoutMode(ModeInterface):
    def mode(self, describe_df):
        return describe_df


# ------------------------

def filter_data(data, list_data):
    if data.name in list_data:
        print(data.name)
        return 1
    return 0


class FilterInterface(ABC):
    @abstractmethod
    def filter(self, describe_df:pd.DataFrame, filter_text:str):
        pass


class TextFilter(FilterInterface):
    def filter(self, describe_df, filter_text):
        list_data = filter_text.split(',')

        describe_df.loc[:, 'filter'] = describe_df.apply(filter_data, axis=1, args=(list_data,))
        problem_describe_df = describe_df[describe_df['filter'] == 1 ]
        return problem_describe_df


class NotFilter(FilterInterface):
    def filter(self, describe_df, filter_text):
        return describe_df

# ------------------------

class Atypical(ABC):
    def __init__(self, mode_behavior:ModeInterface, filter_behavior:FilterInterface):
        self._mode_behavior = mode_behavior
        self._filter_behavior = filter_behavior

    def do_mode(self, describe_df:pd.DataFrame):
        return self._mode_behavior.mode(describe_df)

    def do_filter(self, describe_df:pd.DataFrame, filter_text:str):
        return self._filter_behavior.filter(describe_df, filter_text)

    def set_mode(self, mode_behavior):
        self._mode_behavior = mode_behavior

    def set_filter(self, filter_behavior):
        self._filter_behavior = filter_behavior


class DefaultAtypical(Atypical):
    def __init__(self):
        super().__init__(mode_behavior=OutlierDetectorMode(), filter_behavior=NotFilter())


def main(file_name, file_path, mode, filter_text):
    # ---- 計算差值 並取出有異常的電錶 ----
    df = pd.read_csv(f'{file_path}\{file_name}')

    # 樞紐處理
    pivot_df = df.pivot(index='TimestampUTC', columns='DisplayName', values='Value')

    # 計算每一列與其上一列之間的差值
    diff_df = pivot_df.diff()

    # 平均數、標準差、四分位數以及最大值與最小值
    describe_df = diff_df.describe(percentiles=[.99])

    # 轉置 橫向變直向
    describe_df = describe_df.transpose()

    # 策略模式
    atypical = DefaultAtypical()

    if mode == 2:
        atypical.set_mode(AllOutoutMode())
    if filter_text:
        atypical.set_filter(TextFilter())

    problem_describe_df = atypical.do_mode(describe_df)
    problem_describe_df = atypical.do_filter(problem_describe_df, filter_text)
    problem_diff_df = diff_df[problem_describe_df.index]
    problem_pivot_df = pivot_df[problem_describe_df.index]

    problem_describe_df.to_excel(f'{file_path}\describe.xlsx')
    problem_diff_df.to_excel(f'{file_path}\diff.xlsx')
    problem_pivot_df.to_excel(f'{file_path}\pivot.xlsx')


def createArgumentParser():
    """解析參數"""
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
        description=dedent(
            '''\
            PME SQL語法
            SELECT DataLog.ID, DataLog.Value, 
            DataLog.TimestampUTC,
            [Source].ID as SourceID , [Source].DisplayName, 
            Quantity.ID as QuantityID , Quantity.Name
            FROM ION_Data.dbo.DataLog2 as DataLog
            JOIN ION_Data.dbo.[Source] as [Source] ON DataLog.SourceID = [Source].ID
            JOIN ION_Data.dbo.Quantity as Quantity ON DataLog.QuantityID = Quantity.ID
            WHERE DataLog.TimestampUTC BETWEEN '2023-06-30 08:00:00' AND '2023-07-02 08:00:00'
            AND Quantity.ID = 129
            ORDER BY DataLog.TimestampUTC DESC
            -----------------------------------------------------------------------
            過濾模式說明
            -m 1: 有負數或有4分位數99%的2倍以上的異常值，挑取出來(預設模式)
            -m 2: 全部顯示

            篩選設備
            -t '設備A,設備B,設備C'
            '''
        ))
    parser.add_argument("-f", required=True, help="檔案名稱(含附檔名)", dest="file_name")
    parser.add_argument("-p", required=True, help="檔案路徑", dest="file_path")
    parser.add_argument("-m", help="過濾模式", dest="mode", type=int, default=1, choices=[1, 2])
    parser.add_argument("-t", help="篩選設備，用','分割的設備 ex:'設備A,設備B,設備C'，預設為不篩選", default='', dest="filter_text")
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = createArgumentParser()
    main(args.file_name, args.file_path, args.mode, args.filter_text)
    print('處理完成')



