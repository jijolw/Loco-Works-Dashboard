# Standalone Type-Wise Holding & POH Report Generator

This lets you generate just the **Type-Wise Holding & POH Performance Report**
Excel file without needing your full Flask app to be working.

## 1. Folder setup

Put `generate_daily_report.py` and `run_report.bat` in the **same folder**
as your existing project root — i.e. next to `config.py` and the `services`
folder:

```
<project_root>/
    config.py                          <- your existing ERP settings (already have this)
    generate_daily_report.py           <- NEW, place here
    run_report.bat                     <- NEW, place here
    services/
        __init__.py                    <- must exist (create an empty file if missing)
        erp_service.py                 <- already have this
        decoders.py                    <- already have this
        type_wise_holding_service.py   <- already have this
```

You do **not** need `db_service.py`, `performance_service.py`, or your Flask
`app.py` for this report — only the three files above plus `config.py`.

## 2. Check `services/__init__.py` exists

If your `services` folder doesn't already have an `__init__.py` file, create
an empty one:

```
services/__init__.py     (can be a completely empty file)
```

## 3. Run it

**Windows (easiest):** double-click `run_report.bat`. A console window opens,
generates the report for the current month, and saves it into a new
`reports/` folder next to the script.

**Command line (more control):**
```
python generate_daily_report.py
python generate_daily_report.py --month July --year 2026
python generate_daily_report.py --outdir "D:\JIJO\Reports"
```

## 4. Output

Each run saves a timestamped file like:
```
reports/TypeWise_Holding_POH_JULY_2026_20260723_143012.xlsx
```

## Troubleshooting

- **"Could not import services.type_wise_holding_service"** — the script
  isn't in the right folder, or `services/__init__.py` is missing.
- **"A required file was not found"** — almost certainly the Google
  service-account `credentials.json`. `type_wise_holding_service.py` has this
  hardcoded:
  ```python
  CREDENTIALS_PATH = "D:\\JIJO\\information\\Coach Position\\credentials.json"
  ```
  Make sure that exact file exists at that exact path, or edit the path in
  `type_wise_holding_service.py` to point to wherever your credentials file
  actually lives.
- **Any other error** — the script prints the full Python traceback so you
  can see exactly which line/module failed (usually a live ERP fetch or
  Google Sheets read timing out).
