import openpyxl
files = [r'data\\raw\\census-2011\\PC11_PCA_MISC08.xlsx', r'data\\raw\\census-2011\\PC11_PCA_MISC09.xlsx']
for f in files:
    print('\n--- FILE:', f)
    try:
        wb = openpyxl.load_workbook(f, data_only=True)
        sh = wb.active
        for i,row in enumerate(sh.iter_rows(values_only=True), start=1):
            print(i, [str(c) if c is not None else None for c in row])
            if i >= 20:
                break
    except Exception as e:
        print('ERROR reading', f, e)
