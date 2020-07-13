import subprocess
import os 

file_name="Schedule Task Demo"
cmd = "python3 '{}' ".format("task/" + file_name + ".py")
print(cmd)
process = subprocess.Popen(
    ["python3","task/" + file_name + ".py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=False,
    encoding='utf-8',
    errors='replace'
)
print(process.pid)
while True:
    realtime_output = process.stdout.readline()

    if realtime_output == '' and process.poll() is not None:
        break

    if realtime_output:
        print(realtime_output.strip())