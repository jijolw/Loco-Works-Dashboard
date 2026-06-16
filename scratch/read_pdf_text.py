import os

pdf_path = r"D:\Information backup\Drive\Drive\deskktop\2026-27\login\Claude\DailyPosition05062026.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    # Let's search in D:\Information backup if we can
    d_dir = r"D:\Information backup"
    if os.path.exists(d_dir):
        print(f"D:\\Information backup exists. Searching inside it...")
        for root, dirs, files in os.walk(d_dir):
            if "DailyPosition05062026.pdf" in files:
                print(f"Found it at: {os.path.join(root, 'DailyPosition05062026.pdf')}")
                pdf_path = os.path.join(root, "DailyPosition05062026.pdf")
                break
else:
    print(f"File exists at: {pdf_path}")

try:
    import pypdf
    print("pypdf is installed")
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        print(f"--- PAGE {i+1} ---")
        lines = text.split("\n")
        # Print lines containing loco or AC
        for line in lines:
            if any(k in line.lower() for k in ["loco", "ac", "wap", "wag", "30587", "30570", "22342"]):
                print(f"  {line}")
except Exception as e:
    print(f"Error reading PDF: {e}")
