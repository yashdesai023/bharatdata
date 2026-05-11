from openpyxl import Workbook
import os
base = 'pipeline/tests/fixtures/census2011/raw'
if not os.path.exists(base): os.makedirs(base)
# merged headers sample
wb=Workbook()
ws=wb.active
ws.append(['State and District','Area Name','Population Totals'])
ws.append(['KA - 01','SampleMergedTown','TOT_P:1000;TOT_M:510;TOT_F:490'])
wb.save(os.path.join(base,'sample_merged_headers.xlsx'))
# alternate columns sample
wb2=Workbook()
ws2=wb2.active
ws2.append(['STATE','DIST','NAME','TOTAL_POP'])
ws2.append(['KA','01','AltTown','2000'])
wb2.save(os.path.join(base,'sample_alt_columns.xlsx'))
print('created samples')