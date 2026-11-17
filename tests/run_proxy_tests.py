from os import environ
import secrets
import subprocess
from browser_support import local_api, ROOT

key = secrets.token_urlsafe(32)
with local_api(proxy_key=key) as url:
    subprocess.run(["node","--disable-warning=ExperimentalWarning","--test","tests/proxy.test.mjs"],
                   cwd=ROOT, env=dict(environ,TEST_API_URL=url,TEST_PROXY_KEY=key),check=True)
