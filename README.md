# LW/PER Coach POH app

One codebase for the office PC and the online (Render) dashboard.

| | Office PC | Online (Render) |
|---|---|---|
| Start | double-click `Run_App.py` | start command `gunicorn app:app` |
| Mode | `APP_MODE=local` (.env) | `APP_MODE=online` (Render environment) |
| Data | `08_Claude_ERP_Export/data/erp_demands_latest.json` | snapshot in Supabase Storage (uploaded by the PC) |
| Update from ERP | button (also uploads the online snapshot) | hidden - view only |

Rules: `core/rules.py`. Coach groups: `coach_groups.csv` (edit freely; unknown types show as OTHERS on the Month Position page).
Passwords/keys live only in `.env` (PC) or the Render dashboard - never in code or Git.
`python -m core.erp_client` = same export as `Export_ERP_for_Claude` (read-only).
