# 🚀 Funnel-Forge: Tailscale Funnel Manager (PyQt6 GUI)

This project lets you expose a local web server (Flask, Django, Node.js,
etc.) running in Termux/PRoot or any Linux environment to the internet
using Tailscale Funnel — now from a structured PyQt6 GUI app.

---

## 📁 Project structure

```
funnel-forge/
├── main.py                    # App entry point
├── core/
│   ├── settings.py            # settings.json load/save logic
│   ├── funnel_controller.py   # tailscaled/tailscale process management (QProcess)
│   └── logger.py              # Rotating file logging
├── ui/
│   ├── main_window.py         # PyQt6 main window (tabs: Funnel + Tailscale + Setup Guide)
│   ├── tailscale_tab.py       # Install/update Tailscale, version check, path mode
│   └── setup_guide_tab.py     # Color-highlighted Tailscale website/Admin Console setup walkthrough
├── tests/                     # pytest suite (settings + controller logic)
├── .github/workflows/
│   ├── ci.yml                 # Lint + tests on Linux/Windows, Python 3.10-3.12
│   ├── build-linux.yml        # Linux binaries: x86_64 + arm64, on v* tags
│   └── build-windows.yml      # Windows binaries: x64 + arm64, on v* tags
├── requirements.txt
├── requirements-dev.txt        # pytest + ruff
├── requirements-lock.txt       # exact pinned versions for reproducible installs
├── pyproject.toml              # project metadata, ruff/pytest config
├── LICENSE                     # MIT
├── build.sh                   # Linux/Termux build script (venv + PyInstaller, auto-cleans)
├── build.bat                  # Windows build script (same behavior)
├── install.sh                 # Creates a Linux desktop entry only (no installs/build)
├── assets/
│   └── funnel-forge.png       # App icon used by the desktop entry
├── start-funnel.sh            # (optional) legacy CLI script, kept for manual use
├── stop-funnel.sh             # (optional) legacy CLI script
└── settings.json              # auto-created after the first run (git-ignored)
```

---

## 🛠️ Step 1: Install Tailscale

If Tailscale isn't installed in your Linux or PRoot environment yet, run:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

## 🌐 Step 2: Tailscale Admin Console configuration (one-time setup)

To expose a local server to the internet with Tailscale Funnel, a few
permissions need to be enabled from the admin dashboard.

1. **Log in:** go to the Tailscale Admin Console and log in with your
   Google/GitHub account.

2. **Enable DNS & HTTPS:**
   - Go to the **DNS** tab at the top.
   - Enable **"MagicDNS"**.
   - Scroll down and enable **"HTTPS Certificates"** (required for Funnel
     to work).
   - Optionally click **Rename tailnet** to give your domain a simpler
     name (e.g. `sumit-net.ts.net`).

3. **Grant Funnel permission (ACLs):**
   - Go to the **Access Controls** tab. You'll see a JSON editor.
   - Add a `nodeAttrs` section so your device gets funnel access.

   **Where to put it — step by step:**
   1. Scroll to the very bottom of the editor. You'll see a closing brace
      `}` — that's the end of the whole file.
   2. Click right before that final `}` (i.e. at the end of the line
      above it).
   3. Press **Enter** to create a new blank line.
   4. Paste the following exactly as-is:

```json
"nodeAttrs": [
    {
        "target": ["autogroup:member"],
        "attr":   ["funnel"]
    }
],
```

   5. Click **Save** below.

   > ⚠️ **Note:** JSON requires a comma after every item except the very
   > last one. If Save gives an error (e.g. "trailing comma" or
   > "unexpected token"), check that the line just before your pasted
   > block ends with a comma, and that the very last line has no extra
   > trailing comma.

## 💻 Step 3: Start your local server

Your web server needs to be running before you funnel it. For example,
with Flask on port 5000:

```bash
python app.py
```

## 🔑 Step 3.5: Disable key expiry (recommended for long-running Funnels)

By default, a device's Tailscale key expires after a while (180 days),
which would silently disconnect the Funnel. For a device that runs the
Funnel long-term, turn that off:

1. Open the Tailscale admin console: **Machines**.
2. For the device running the Funnel, open the three-dot menu on the
   right.
3. Select **Disable key expiry**.

## 🖥️ Step 4: Install and run the GUI

```bash
cd funnel-forge
pip install -r requirements.txt
python main.py
```

What you can do from the **Funnel** tab:

- Set **Hostname**, **Port**, **Socket path**, and whether to use `sudo`
- Clicking **Start Funnel** cleans up any old process, starts
  `tailscaled`, connects with `tailscale up`, and finally runs
  `tailscale funnel <port>` — all in the background, without freezing
  the UI
- The live **Log** panel shows the whole process's output, and the
  resulting public link is auto-detected and shown in the **Public URL**
  field (format: `https://share-forge.<your-tailnet-name>.ts.net`)
- **Stop Funnel** cleanly terminates all Tailscale processes and the
  socket file
- **Save Settings** persists hostname/port/etc. to `settings.json` for
  next time

> **Closing the window does not stop the Funnel.** The daemon and funnel
> processes are launched detached from the GUI, so they keep serving
> traffic in the background even after you close Funnel-Forge — the same
> way the original shell scripts left it running in a terminal. Reopen
> the app and press **Stop Funnel** whenever you want to shut it down; it
> will detect an already-running session and show it as "Running".

What you can do from the **Tailscale** tab:

- See the installed Tailscale **version**, with a **Refresh** button
- **Install Tailscale** — runs the official install script
  (`curl -fsSL https://tailscale.com/install.sh | sh`)
- **Check & Update** — runs `tailscale update --yes` to self-update to
  the latest release
- **Manual Upgrade** — re-runs the install script (useful as a forced
  reinstall/upgrade)
- **Automatically check for updates on startup** checkbox — when
  enabled, Funnel-Forge runs an update check once each time it starts
- **Path mode: Auto-detect / Manual** — Auto searches `PATH` plus common
  install directories (`/usr/sbin`, `/usr/local/sbin`, etc.); Manual lets
  you type or browse to exact `tailscale` / `tailscaled` binary paths,
  which the Funnel tab will then use instead of auto-detection

> **First-time authentication:** if this device hasn't been authenticated
> with Tailscale yet, pressing **Start Funnel** will pop up a dialog with
> a `login.tailscale.com` link (it also appears in the Log panel). Open
> that link in any browser, log in, and approve the device - Start Funnel
> then continues automatically once that's done. This only happens once;
> after that, the device stays authenticated. You can also authenticate
> ahead of time from a terminal instead: `sudo tailscale up`.

What you can do from the **Setup Guide** tab:

- A color-highlighted, in-app walkthrough of the whole one-time
  Tailscale website/Admin Console setup - installing Tailscale, enabling
  MagicDNS + HTTPS certs, and granting Funnel access via ACLs
- Headings, JSON/code snippets, and warning callouts are each colored
  differently so the important steps stand out without needing to
  cross-reference this README

## 📦 Step 5: Building a single binary (venv + PyInstaller)

The build runs inside its own isolated virtual environment and cleans
itself up afterward — only the final binary ends up in `dist/`. The
`.spec` file isn't committed; the build script generates a fresh one
every time it runs, then removes it when done.

**Linux / Termux / proot-Debian:**

```bash
./build.sh
```

**Windows:**

```bat
build.bat
```

What the script does:

1. Checks whether `python3 -m venv` (the venv module) is available — if
   not, it exits with a clear error (fix on Debian/Termux with
   `sudo apt install python3-venv`)
2. Creates a fresh `.build-venv` virtualenv and installs
   `requirements.txt` into it
3. Runs PyInstaller from inside that venv to build a `--onefile` binary
   (the `.spec` file is generated fresh at this step)
4. Removes the venv, `build/`, the generated `.spec`, and any
   `__pycache__` folders afterward

Output: `dist/funnel-forge` (Linux/Termux) or `dist/funnel-forge.exe`
(Windows) — a single executable file. Build on the platform/architecture
you want the binary for (no cross-compiling).

## 🖱️ Step 6: Desktop entry (Linux)

```bash
./install.sh
```

This only creates a desktop entry — it doesn't install any
dependencies or build anything. It writes
`~/.local/share/applications/funnel-forge.desktop` using the project's
icon (`assets/funnel-forge.png`), so Funnel-Forge shows up in your
application launcher/menu.

- If `dist/funnel-forge` already exists (i.e. you ran `build.sh`
  first), the entry launches that compiled binary.
- Otherwise it falls back to running `python3 main.py` directly from
  the project folder.

Re-run `install.sh` any time after building the binary to switch the
launcher over to it.

## 🔁 Alternative: legacy shell scripts (CLI)

If you'd rather run things from the terminal without the GUI, the
original scripts still work:

```bash
cd funnel-forge
./start-funnel.sh
./stop-funnel.sh
```

## 🧪 Development: tests, linting, logs

```bash
pip install -r requirements.txt -r requirements-dev.txt

# Run the test suite (settings persistence + controller pure-logic helpers)
pytest -v

# Lint
ruff check .
```

- **Reproducible installs:** `requirements.txt` uses open version ranges
  for day-to-day development; `requirements-lock.txt` pins exact,
  known-good versions for a reproducible build environment - use
  `pip install -r requirements-lock.txt` when you want that instead.
  Regenerate it after upgrading anything (see the comment at the top of
  that file).
- **CI:** `.github/workflows/ci.yml` runs `ruff` and `pytest` on every
  push/PR across Linux and Windows, Python 3.10-3.12.
  `build-linux.yml` and `build-windows.yml` each build single-binary
  artifacts for both architectures (Linux: x86_64 + arm64; Windows:
  x64 + arm64, on native Arm-hosted runners - no emulation or
  cross-compiling) whenever a `v*` tag is pushed, or on demand via
  "Run workflow" in the Actions tab.
- **Logs:** in addition to the on-screen log panels, everything is also
  written to a rotating log file so it survives after the app closes:
  `<system temp dir>/funnel-forge-logs/funnel-forge.log` (e.g.
  `/tmp/funnel-forge-logs/` on Linux/Termux).

## 📝 Notes

- On Windows, the "Use sudo" checkbox is automatically disabled since
  sudo doesn't apply there.
- If "Use sudo" is checked, Funnel-Forge checks that `sudo` can run
  without a password prompt before starting anything (the daemon/funnel
  processes run detached, so they can't show a password prompt). If
  passwordless sudo isn't configured, it fails fast with a clear message
  instead of hanging silently in the background.
- If the `tailscale` / `tailscaled` binaries can't be found, the GUI now
  checks common install locations (`/usr/sbin`, `/usr/local/sbin`, etc.)
  in addition to `PATH`, and shows a clear error if they're still
  missing.
