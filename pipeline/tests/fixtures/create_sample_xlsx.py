from openpyxl import Workbook
import os
wb=Workbook()
ws=wb.active
ws.append(['State','District','Area Name','TOT_P','TOT_M','TOT_F'])
ws.append(['KA','01','SampleTown',1000,510,490])
os.makedirs('pipeline/tests/fixtures/census2011/raw', exist_ok=True)
wb.save('pipeline/tests/fixtures/census2011/raw/sample.xlsx')
print('saved')