from notion_wrapper import NotionWrapper
import time
import traceback

def init():
    try:
        global notion
        notion = NotionWrapper("config.json")
    except FileNotFoundError:
        print("Local config file not found.")
        exit()


def subscribe_to_task_table():
    task_table = notion.get_table_ref("task_table")
    task_table.add_callback(task_row_callback, callback_id="task_row_callback")
    for row in task_table.collection.get_rows():
        row.add_callback(task_callback, callback_id="task_callback")


def task_row_callback(record, difference, changes):
    for item in difference:
        if item[0] == "add":
            for row in record.collection.get_rows():
                row.add_callback(task_callback, callback_id="task_callback")


def task_callback(record, changes):
    if changes[0][0] == "prop_changed":
        activate = record.activate
        record.activate = False
        if activate:
            record.status = notion.write_script(record.name, record.children)
            activate = False

        run = record.run
        record.run = False
        if run and (record.status == "Activated" or record.status == "Completed"):
            record.status = "Running"
            record.status = notion.run_script(record.name)
            run = False

        kill = record.kill
        record.kill = False
        if kill and record.status == "Running":
            record.status = notion.kill_script(record.name)
            kill = False

        time.sleep(10)


def main():
    try:
        init()
        subscribe_to_task_table()
        notion.print("Service ready.")

        command = ""
        while not notion.kill_now:
            time.sleep(60)

        notion.warn("End of the program.")
    except Exception as e:
        notion.error(traceback.format_exc())
    except KeyboardInterrupt as e:
        exit()


if __name__ == "__main__":
    main()
