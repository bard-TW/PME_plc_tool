# PME_tool

為施耐德的PME所寫的方便小工具

建議使用powershell，含有中文字使用CMD會出問題

## make_plc

透過提供設備名與測量值對應填入modbus address，產生出"Device Type Editor"所需要的檔案，和導入邏輯設備的檔案，  
PLC設備數量很多，常常修修改改，這會是一個很棒的工具。

> 注意: 建議在使用此工具之前，已熟知原先軟體的作業流程。

### 如何使用

1. 請下載執行檔
2. 請將 帶有 PLC_data 的資料夾，下載並放置在執行檔相同目錄
3. 請按照範例 [點位表.csv](PLC_data/example/點位表.csv)，
   欄位名稱填入測量值
   列名填入裝置名稱
4. [plc_format.csv](PLC_data/plc_format.csv) 填入format格式
5. 執行以下指令

```bash
# 參數 -h : 查看參數介紹

# 參數 -f : 檔案名稱(不含副檔名)
# 參數 -p : 檔案位置

# 使用執行檔
.\make_plc.exe -f '點位表' -p '.\PLC_data\example'

# 使用原始檔
python .\make_plc.py  -f '點位表' -p '.\PLC_data\example'
```

檔案介紹
   點位表.csv : 必須提供，紀錄設備與測量值對應的modbus點位
   點位表_th.csv : 初次建立會自行產生，紀錄在ION裡的th值，防止產生資料與PME無法對應
   點位表.ion : measurement tree
   點位表.xml : modbus map
   點位表_output_logic.csv : 導入邏輯設備(需自行再加工)
   plc_format.csv: 需提供，與點位表.csv相同位置
   檔案編碼，utf-8 或 big5


## atypical

透過 sql 把指定時間區間內和指定測量值的PME資料取出，進行資料分析。

### 如何使用

1. 請下載執行檔
2. 透過sql把資料篩選並輸出CSV存到本機(語法請看-h)
3. 執行以下指令

```bash
# 參數 -h : 查看參數介紹

# 參數 -f : 檔案名稱(含副檔名)
# 參數 -p : 檔案位置
# 參數 -m : 過濾模式
# 參數 -t : 篩選設備

# 使用執行檔
.\atypical.exe -f 'yourdata.csv' -p '.\your\path'

# 使用原始檔
python .\atypical.py  -f 'yourdata.csv' -p '.\your\path'
```


## 打包指令

```bash
pyinstaller -F .\make_plc.py
pyinstaller -F .\atypical.py
pyinstaller -F .\modbus.py

pyinstaller -F modbus_web.py --add-data 'templates;templates' --add-data 'static;static' --name modbus_web
```
