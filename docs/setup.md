# Run Pakistan Flood Monitor locally

This tutorial starts a labelled local demo. Use Python 3.12 to match the offline
CI environment. Python 3.11 is the lowest verified runtime. Python 3.10
fails on the canonical API's `datetime.UTC` import, even though package
metadata still advertises 3.10. See [compatibility evidence](testing.md#python-compatibility)
and the [configuration reference](configuration.md) for mode and database
settings.

## Install the project

From a shell with Git and Python 3.12 available:

```bash
git clone https://github.com/afaq-ahmad/pakistan-flood-monitor.git
cd pakistan-flood-monitor
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,dashboard]"
```

In PowerShell, activate with `.\.venv\Scripts\Activate.ps1` in place of
`source`. Run the remaining commands from the repository root. The dashboard
extra installs Streamlit and the dashboard's supporting libraries.

## Open the standalone demo

Run the dashboard with `API_BASE_URL` unset:

```bash
APP_MODE=demo python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

In PowerShell set `$env:APP_MODE = "demo"` before running the command without
the Bash assignment prefix. Open `http://127.0.0.1:8501`. Look for the demo
watermark and follow **Open My Area** to the corridor selector. The official
information and preparedness pages work independently of the event feed.

Local demo uses checked-in fixtures. It does not require satellite or rainfall
credentials. If your environment or untracked `.env` sets `API_BASE_URL`,
clear that setting to use local fixtures. See [troubleshooting](troubleshooting.md)
if the page instead says that flood information is unavailable.

## Connect to the canonical API

In a second terminal with the same environment active:

```bash
APP_MODE=demo python -m uvicorn pakistan_flood_monitor.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health` and confirm `app_mode` is `demo`. The
API reference UI is at `http://127.0.0.1:8000/docs`. Restart the first terminal's
Streamlit process with this connection:

```bash
APP_MODE=demo API_BASE_URL=http://127.0.0.1:8000 python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

For PowerShell set `$env:API_BASE_URL = "http://127.0.0.1:8000"` before running
Streamlit. With a fresh API, Home can show an empty published feed. An empty
feed and an unavailable source are separate states. The UI does not switch
to local fixture events after an API error.

For automated validation, follow [offline testing](testing.md). For a
persistent demo or Compose, follow [deployment](deployment.md).
