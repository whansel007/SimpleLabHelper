@echo off
cd %i
for /r %%i in (*_test.py) do (
    echo %%i
    exit 0
)