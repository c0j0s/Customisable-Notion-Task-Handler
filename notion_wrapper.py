from notion.client import NotionClient
from notion.block import CodeBlock
from datetime import datetime
import traceback
import json
import re
import subprocess
import os
import signal
import time


class NotionWrapper:
    """ A wrapper object for easy interation with remote notion control page. """

    child_process = {}
    kill_now = False

    def __init__(self, local_config_file_path):
        self.__config = json.load(open(local_config_file_path))
        self.__client = NotionClient(
            token_v2=self.get_config("token"), monitor=True, start_monitoring=True
        )
        self.load_global_configs()

        # signal.signal(signal.SIGINT, self.end_service)
        signal.signal(signal.SIGTERM, self.end_service)

    def get_client(self):
        return self.__client

    def load_global_configs(self):
        """ Retrieve remote config """
        cv = self.get_table("global_configs")
        for row in cv.get_rows():
            self.set_config(row.name, row.data_type, row.value)
            row.add_callback(self.config_callback, callback_id="config_callback")

    def config_callback(self, record, changes):
        if changes[0][0] == "prop_changed":
            self.warn(
                "Config changed: {}({})={}".format(
                    str(record.name), str(record.data_type), str(record.value)
                )
            )
            self.set_config(record.name, record.data_type, record.value)
            time.sleep(10)

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
        return self.get_table_ref(table_name).collection

    def get_table_ref(self, table_name: str):
        assert (
            self.get_config(table_name) is not None
        ), "Table name not found in config."
        return self.get_client().get_collection_view(self.get_config(table_name))

    def debug(self, message: str, host: str = "Main", level: str = "Debug"):
        self.__log(message, host, level)

    def print(self, message: str, host: str = "Main", level: str = "Info"):
        self.__log(message, host, level)

    def warn(self, message: str, host: str = "Main", level: str = "Warning"):
        self.__log(message, host, level)

    def error(self, message: str, host: str = "Main", level: str = "Error"):
        self.__log(message, host, level)

    def __log(self, message: str, host: str, level: str):
        """ Prints log to local console and remote notion log table """
        try:
            if self.get_config("debug"):
                print("[{}][{}]: {}".format(datetime.now(), level, message))
                cv = self.get_table("log_table")
                row = cv.add_row()
                row.name = host
                row.level = level
                row.log_on = str(datetime.now())
                row.message = message
        except KeyError:
            """ Raised due to config not loaded """
            pass
        except AssertionError as ae:
            print(str(ae))

    def write_script(self, file_name: str, script_content: str):
        try:
            status = "Error"
            write_mode = "w"
            with open("task/" + file_name + ".py", write_mode) as f:
                for block in script_content:
                    if type(block) == CodeBlock:
                        f.write(block.title)
                        if write_mode == "a":
                           f.write("\n\n#Second Code Block\n\n")
                        if write_mode == "w":
                            write_mode = "a"
                f.close()
            status = "Activated"
            self.print(file_name + " task activated.")
            return status
        except Exception as e:
            self.error(traceback.format_exc())

    def run_script(self, file_name: str):
        try:
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
            self.child_process[file_name] = process.pid
            host = "[" + str(process.pid) + "] " + file_name
            self.print("Running: " + host)

            while True:
                realtime_output = process.stdout.readline()

                if realtime_output == "" and process.poll() is not None:
                    break

                if realtime_output:
                    try:
                        output = json.loads(realtime_output.strip())
                        if output["level"] == "Debug":
                            self.debug(output["message"], host)
                        elif output["level"] == "Warning":
                            self.warn(output["message"], host)
                        elif output["level"] == "Error":
                            self.error(output["message"], host)
                        else:
                            self.print(output["message"], host)
                    except Exception:
                        self.error(realtime_output.strip(), host)
                        
        except FileExistsError as e:
            self.error("Task script not found, Reactivate the script again.")
        except Exception as e:
            self.error(traceback.format_exc())
        finally:
            return "Completed"

    def kill_script(self, file_name: str):
        self.print(
            "Terminating script: "
            + file_name
            + " -> "
            + str(self.child_process[file_name])
        )
        try:
            os.kill(int(self.child_process[file_name]), signal.SIGTERM)
            if self.child_process[file_name] is not None:
                del self.child_process[file_name]
        except Exception as e:
            self.error(traceback.format_exc())
        finally:
            return "Completed"

    def end_service(self, signum, frame):
        if len(self.child_process.values()) > 0:
            self.print("Ending service, terminating all child processes..")
            for process in self.child_process.values():
                try:
                    os.kill(int(process), signal.SIGTERM)
                except Exception:
                    continue

        cv = self.get_table("task_table")
        for row in cv.get_rows():
            if row.status == "Running":
                row.status = "Completed"

            if row.name == "Main":
                row.remove()
                
        self.warn("End of the program.")
        self.kill_now = True
