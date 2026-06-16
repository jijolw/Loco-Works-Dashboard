import openpyxl

path = r"C:\Users\User\Downloads\LHB_POH_Data.xlsx"
try:
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    print(f"Sheet Name: {ws.title}")
    
    # Read first 10 rows
    rows = []
    for r in ws.iter_rows(max_row=10, values_only=True):
        if any(r):
            rows.append(r)
            
    print("\nFirst 10 rows:")
    for i, row in enumerate(rows):
        print(f"Row {i}: {row}")
except Exception as e:
    print("Error:", e)
