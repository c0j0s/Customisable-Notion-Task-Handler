from notion_wrapper import NotionWrapper
import time
import traceback
import threading
import sys
import os


def init():
    try:
        global notion
        notion = NotionWrapper("config.json")

        cv = notion.get_table("task_table")
        if len(cv.get_rows(search="Main")) == 0:
            row = cv.add_row()
            row.name = "Main"
            row.status = "Running"

    except FileNotFoundError:
        print("Local config file not found.")
        sys.exit()


def subscribe_to_task_table():
    task_table = notion.get_table_ref("task_table")
    task_table.add_callback(task_row_callback, callback_id="task_row_callback")
    # initial subscription
    for row in task_table.collection.get_rows():
        if row.autorun:
            x = threading.Thread(target=start_script, args=(row,)).start()
        row.remove_callbacks("task_callback")
        row.add_callback(task_callback, callback_id="task_callback")


def task_row_callback(record, difference, changes):
    for item in difference:
        if item[0] == "add":
            # resubscribe when new row added
            for row in record.collection.get_rows():
                row.remove_callbacks("task_callback")
                row.add_callback(task_callback, callback_id="task_callback")


def task_callback(record, changes):
    if changes[0][0] == "prop_changed":
        if str(changes[0][2][1]) == "True":

            activate = record.activate
            record.activate = False
            if activate and record.status != "Running":
                record.status = notion.write_script(record.name, record.children)
                activate = False

            run = record.run
            record.run = False
            if run:
                if record.name == "Main":
                    notion.warn("Clearing Log Table")
                    notion.clear_table("log_table")
                else:
                    if record.status == "Activated" or record.status == "Completed":
                        start_script(record)
                run = False

            kill = record.kill
            record.kill = False
            if kill and record.status == "Running":
                if record.name == "Main":
                    notion.warn("Terminating [Main]")
                    notion.end_service(None,None)
                else:
                    record.status = notion.kill_script(record.name)
                kill = False

            time.sleep(10)

def start_script(record):
    record.status = "Running"
    record.status = notion.run_script(record.name)

def main():
    try:
        init()
        subscribe_to_task_table()
        notion.print("Service ready.")

        command = ""
        
        while not notion.kill_now:
            pass

        sys.exit()
    except Exception as e:
        notion.error(traceback.format_exc())
    except KeyboardInterrupt as e:
        sys.exit()

if __name__ == "__main__":
    main()
