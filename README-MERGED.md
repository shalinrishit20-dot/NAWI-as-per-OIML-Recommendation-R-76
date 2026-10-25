# NAWI LAB — Integrated Project

This version keeps the **original NAWI LAB frontend/design** and integrates the working functionality from **NAWI-TestPro 2.0**.

## Included functionality
- Original NAWI LAB dashboard / evaluation / reports visual design
- Login + role-based access
- Instrument registration + digital passport
- Test report creation
- OIML R 76 configurable observation workflow
- Environmental conditions
- Live camera evidence capture
- SHA-256 evidence hashing
- Manufacturer product-image upload
- Visual-search prototype
- Public report verification
- Audit log for Admin
- PDF and DOCX report generation
- SQLite demo database (no MySQL setup required for the demo backend)

## Run on Windows
1. Extract the ZIP.
2. Open the extracted `NAWI-Merged` folder in VS Code.
3. Open two terminals.
4. Terminal 1: `run_backend.bat`
5. Terminal 2: `run_frontend.bat`
6. Open the `Local:` URL printed by the frontend, normally `http://localhost:3000`.

## Demo accounts
- admin / admin123
- tester / tester123
- reviewer / reviewer123
- manufacturer / manufacturer123

The frontend proxies `/api/*` and `/media/*` to the Flask backend on `127.0.0.1:5000`.
