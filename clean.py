# DISCLAIMER : simplistic code to help with small daily automation
import subprocess

# Listing the directory to find the zip file
try:
    zip_file = subprocess.run(
        ["powershell", "script/list_zip.bat"],
        capture_output=True,
        text=True,
        check=True).stdout
except Exception as e:
    print(e.stderr)

print(zip_file)
folder = zip_file.split(".zip")[0]
print(zip_file.split(".zip")[0])

subprocess.run(
        ["powershell", "-Command", "rm" , "-r", folder],
        capture_output=True,
        text=True,
        check=True)

subprocess.run(
        ["powershell", "-Command", "rm" , zip_file],
        capture_output=True,
        text=True,
        check=True)