from notion.client import NotionClient
class TaskHandler:
    def __init__(self, configs):
        self.configs = configs

    def print(self,message:str):
        print(message,flush=True)

    