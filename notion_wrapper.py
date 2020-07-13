from notion.client import NotionClient
from notion.block import CodeBlock
from datetime import datetime
import json
import re
import subprocess
import os
import signal


class NotionWrapper:
    """ A wrapper object for easy interation with remote notion control page. """

    def __init__(self, local_config_file_path):
        self.__config = json.load(open(local_config_file_path))
        self.__client = NotionClient(
            token_v2=self.get_config("token"), monitor=True, start_monitoring=True
        )
        self.load_global_configs()
        self.process = {}

    def get_client(self):
        return self.__client

    def load_global_configs(self):
        """ Retrieve remote config """
        cv = self.get_table("global_configs")
        for row in cv.get_rows():
            self.set_config(row.name, row.data_type, row.value)

    def set_config(self, key: str, data_type: str, value: str):
        """ Stores remote config in local memory """
        if data_type == "int":
            self.__config[key] = int(value)
        elif data_type == "bool":
            if value.lower() == "true":
                self.__config[key] = True
            else:
                self.__config[key] = False
        else:
            if value.startswith("["):
                self.__config[key] = re.findall(r"(?<=\().*(?=\))", value)[0]
            else:
                self.__config[key] = value

    def get_config(self, key: str):
        """ Retrieve local stored global configs """
        return self.__config[key]

    def get_table(self, table_name: str):
        """ Retrieve notion table """
        return (
            self.get_client()
            .get_collection_view(self.get_config(table_name))
            .collection
        )

    def get_table_ref(self, table_name: str):
        return self.get_client().get_collection_view(self.get_config(table_name))

    def log(self, message: str, host: str = "Main"):
        """ Prints log to local console and remote notion log table """
        try:
            if self.get_config("debug"):
                print("[{}]: {}".format(datetime.now(), str(message)))
                cv = self.get_table("log_table")
                row = cv.add_row()
                row.name = host
                row.log_on = str(datetime.now())
                row.message = message
        except KeyError:
            """ Raised due to config not loaded """
            pass

    def write_script(self, file_name: str, script_content: str):
        try:
            status = "Error"
            with open("task/" + file_name + ".py", "w") as f:
                for block in script_content:
                    if type(block) == CodeBlock:
                        f.write(block.title)
                        f.close()
                        status = "Activated"
                        self.log(file_name + " task activated.")
            return status
        except Exception as e:
            self.log(str(e))

    def run_script(self, file_name: str):
        try:
            self.log("Starting " + file_name + " task.")

            process = subprocess.Popen(
                [
                    "python3",
                    os.getcwd() + "/task/" + file_name + ".py",
                    json.dumps(self.__config),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                encoding="utf-8",
                errors="replace",
            )
            self.process[file_name] = process.pid
            host = file_name + " [" + str(process.pid) + "]"
            self.log("Running: " + host)

            while True:
                realtime_output = process.stdout.readline()

                if realtime_output == "" and process.poll() is not None:
                    break

                if realtime_output:
                    self.log(realtime_output.strip(), host)

            del self.process[file_name]
            return "Completed"
        except FileExistsError as e:
            self.log("Task script not found, Reactivate the script again.")

    def kill_script(self, file_name: str):
        self.log("Killing script: " + file_name + " -> " + str(self.process[file_name]))
        try:
            os.kill(int(self.process[file_name]), signal.SIGTERM)
            del self.process[file_name]
            return "Completed"
        except Exception as e:
            self.log("Task script unable to be killed.")

    def kill_all_script(self):
        for process in self.process.values():
            result = os.kill(int(process), signal.SIGTERM)
