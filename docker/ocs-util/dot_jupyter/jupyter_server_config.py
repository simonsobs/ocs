import os
from notebook.auth import passwd

c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = int(os.environ.get("JUPYTER_PORT", 8888))

c.ServerApp.allow_root = True
c.ServerApp.open_browser = False

c.ServerApp.password = passwd(os.environ.get("JUPYTER_PW", 'password'))
c.ServerApp.password_required = True
