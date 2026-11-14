# Simple Lab Helper

A small local Flask app for comparing instructor and student lab programs.

## Run it

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Open the local address printed by Flask (normally `http://127.0.0.1:5000`).

## Grade a submission

1. In **Solutions & settings**, choose the instructor solution ZIP and select **Extract solution**.
2. In **Student workspace**, enter the student's name and ID, choose their ZIP, and select **Extract student ZIP**.
3. Add comparison rows. Each row pairs a runnable `.py` file from the solution with a `.py` file from the student's submission. Tester files can be selected here too.
4. Select **Save settings**, then **Run comparisons**.

Use **Clean workspace** to remove the current student's extracted files and details before moving on. Student files are displayed by their question filename (for example, `q1a.py`); any enclosing ZIP folder remains hidden in the label.

The solution and student archives are extracted into the top-level `solutions/` and `workspace/` folders. Comparison settings and the current student details are stored in `settings/`. Uploading a new student ZIP replaces the current workspace contents. Settings are remembered for each solution ZIP and can be adjusted when a student's file paths differ.

Each selected Python file runs from its own containing directory. The app captures stdout and compares the raw bytes exactly; spaces, line endings, and blank lines affect the result. Stderr and nonzero exit codes are shown as run errors.
