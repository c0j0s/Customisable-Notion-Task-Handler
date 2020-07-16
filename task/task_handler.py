from notion.client import NotionClient
import json


class TaskHandler:
    """ A simple helper class for custom scripts. """

    def __init__(self, configs):
        if configs != "":
            self.configs = json.loads(configs)
        else:
            self.configs = None

    def print(self, message: str):
        self.__write(message, "Info")

    def debug(self, message: str):
        self.__write(message, "Debug")

    def warn(self, message: str):
        self.__write(message, "Warning")

    def error(self, message: str):
        self.__write(message, "Error")

    def __write(self, message: str, level: str):
        assert message is not None, "Message empty"
        assert level is not None, "Invalid log level"
        print(json.dumps({"message": message, "level": level}), flush=True)

