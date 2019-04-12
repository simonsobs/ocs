import ipywidgets as wd

class TaskWidget(wd.Box):
    def __init__(self, client, task, params=None):
        super().__init__()
        self.client = client
        self.task = task
        self.params = params
        self.label = wd.Label("{}: {}".format(client.agent_addr, task))

        self.start = wd.Button(description="Start")
        self.start.on_click(self.cb)

        self.layout.border = "4px solid black"

        self.children = [wd.VBox([self.label, self.start])]

    def cb(self, b):
        self.client.request('start', self.task, self.params)

class ProcessWidget(wd.Box):
    def __init__(self, client, process, params=None):
        super().__init__()
        self.client = client
        self.process = process
        self.params = params

        self.label = wd.Label("{}: {}".format(client.agent_addr, process))
        self.label.layout.

        self.start = wd.Button(description="Start")
        self.start.on_click(self.cb)
        self.stop = wd.Button(description="Stop")
        self.stop.on_click(self.cb)
        self.buttons = wd.HBox([self.start, self.stop])
        self.children = [wd.VBox([self.label, self.buttons])]
        self.layout.border = "4px solid black"

    def cb(self, b):
        if b is self.start:
            self.client.request('start', self.process, self.params)
        if b is self.stop:
            self.client.request('stop', self.process, self.params)
