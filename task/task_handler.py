from notion.client import NotionClient
import json

class TaskHandler:
    """ A simple helper class for custom scripts. """

    def __init__(self, configs):
        self.configs = json.loads(configs)

    def print(self, message: str):
        print(message, flush=True)

