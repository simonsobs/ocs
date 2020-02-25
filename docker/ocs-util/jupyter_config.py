import os
from notebook.auth import passwd

c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = int(os.environ.get("JUPYTER_PORT", 8888))

c.NotebookApp.allow_root = True
c.NotebookApp.open_browser = False

c.NotebookApp.password = passwd(os.environ.get("JUPYTER_PW", 'password'))
c.NotebookApp.password_required = True