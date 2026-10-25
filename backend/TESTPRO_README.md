# NAWI-TestPro 2.0.1 — React Edition

A redesigned Flask + React application for the **Development of a Software Program/Application for Generation of Test Reports for Non-Automatic Weighing Instruments (NAWI)**.

## What's new
- Full React + Vite frontend (HTML templates removed from the application UI)
- Attractive responsive laboratory dashboard
- Digital Passport for each instrument
- Live browser camera test recording
- SHA-256 hash stored for uploaded test evidence
- Manual reference/indication readings linked to each report
- Manufacturer product photo gallery
- AI-assisted visual search prototype using lightweight perceptual image hashing
- Public report authenticity verification API/page
- Report PDF + Word export
- Role-aware Admin / Tester / Reviewer / Manufacturer demo accounts
- SQLite default for easy setup; MySQL supported with `DATABASE_URL`
- Audit trail

## Demo accounts
- admin / admin123
- tester / tester123
- reviewer / reviewer123
- manufacturer / manufacturer123

## Run on Windows
### 1. Create virtual environment
```powershell
py -m venv venv
```

### 2. Install backend packages
```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install React packages
```powershell
cd frontend
npm install
npm run build
cd ..
```

### 4. Start Flask
```powershell
venv\Scripts\python.exe app.py
```

Open: **http://127.0.0.1:5000**

> Camera access works on localhost after the browser asks for permission.

## Development mode
Terminal 1:
```powershell
venv\Scripts\python.exe app.py
```
Terminal 2:
```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API requests only if you add a proxy in `vite.config.js`; for the easiest demo, use the production build above.

## MySQL
Set:
```text
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost/nawi_testpro
```
Then start Flask. Tables are created automatically.

## Important OIML note
The existing observation calculation intentionally uses a **demonstration MPE function**. It is not an official implementation of OIML R 76. Before operational or legal use, the applicable OIML revision, national requirements, instrument class, verification interval, test procedure and permissible errors must be reviewed and implemented as versioned rules.

## Visual search note
The visual search feature is an academic/hackathon prototype. It ranks registered product photos using a lightweight perceptual hash. A photo alone should not be treated as conclusive proof of the exact physical instrument because identical models can look alike. For definitive verification, use the instrument serial number and/or QR/report verification.


## 2.0.1 stability fix
- Fixed React `useEffect` lifecycle bug caused by returning Promises from async data-loading callbacks.
- Added a React Error Boundary so unexpected UI errors show a recovery screen instead of a blank page.
- Added Vite React configuration and pinned frontend dependency versions for more reproducible builds.
- Build the frontend again after replacing the project files.
