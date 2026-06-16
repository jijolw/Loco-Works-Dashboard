import os

pdf_path = r"D:\Information backup\Drive\Drive\deskktop\2026-27\login\Claude\DailyPosition05062026.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found")
    exit(1)

try:
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    # Search for page containing AC Loco details
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if "details of ac loco" in text.lower() or "details of ac locos" in text.lower():
            print(f"Found AC Loco details on Page {i+1}:")
            # Write to a file with utf-8 to avoid console encoding issues
            out_path = r"C:\Users\User\.gemini\antigravity\scratch\ERP\scratch\acloco_page_text.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Written text to {out_path}")
            
            # Print first few lines using repr to avoid console issues
            lines = text.split("\n")
            for line in lines[:20]:
                print(repr(line))
            break
except Exception as e:
    print(f"Error: {e}")
