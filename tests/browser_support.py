from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def local_api(*, proxy_key=""):
    with tempfile.TemporaryDirectory() as tmp:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = dict(os.environ, PYTHONPATH=str(ROOT / "server"), DATABASE_URL="sqlite:///" + str(Path(tmp) / "qa.db"),
                   STEADYDAY_MODE="local", PROXY_KEY=proxy_key, DEMO_ACCESS_CODE="", APP_ORIGIN="",
                   DEMO_SESSION_LIMIT="300")
        with subprocess.Popen(
            [sys.executable,"-m","uvicorn","steadyday.main:app","--host","127.0.0.1","--port",str(port),"--no-access-log","--log-level","warning"],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,
        ) as process:
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError("API could not start: " + (process.stderr.read() if process.stderr else "")[-1800:])
                    try:
                        with urlopen(url+"/healthz", timeout=0.3) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError("API health check timed out")
                yield url
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def launch(playwright):
    binary = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
    return playwright.chromium.launch(
        headless=True, **({"executable_path":binary} if binary else {}),
        args=["--no-sandbox","--disable-dev-shm-usage"],
    )
