# DISCLAIMER : simplistic code to help with small daily automation
import subprocess

questions = ["1a", "1b", "4"]

# Listing the directory to find the zip file
zip_file = subprocess.run(
    ["./script/list_zip.bat"],
    capture_output=True,
    text=True,
    check=True).stdout

print(zip_file)

# Extract it
subprocess.run(
    ["powershell", "-Command", "Expand-Archive", f"{zip_file}"],
    capture_output=True,
    text=True,
    check=True).stdout

# Find the recursively
root_find = subprocess.run(
    ["./script/find_root.bat"],
    capture_output=True,
    text=True,
    check=True).stdout.split("\\")[:-1]

root_path = "\\".join(root_find)
print(repr(root_path))

for q in questions:
        result = subprocess.run(
            [r"./script/run_testcase.bat", root_path, q],
            capture_output=True,
            text=True,)
        print(result.stdout)
