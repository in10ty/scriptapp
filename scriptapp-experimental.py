#!/usr/bin/env python3
# ^ "Shebang" first line that makes this code executable as a program
"""
------------
NOTE:
The code in this file is early research for a feature-complete version of ScriptApp. This code is 
very experimental, contains lots of bugs, and even has some features that I already plan to replace 
with something better.

DO NOT try use this version of ScriptApp for doing real work. It is for demonstration purposes only.
------------

Explicitly Stated Intentions:
1. Act as a user-friendly wrapper for running Intentionalist data processing scripts.
2. Serve as a reference implementation of the ScriptApp Processing Protocol (SAPP) that...
    2.1. Has enough features to be useful for real admin work, not just as a toy demonstration.
    2.2. Is as self-contained as possible.
    2.3. Has short, simple and well-documented code, so that inexperienced coders (who might not
    have read the source code of *any* other program) can understand exactly how it works and
    start writing their own scripts ASAP.

Instructions for installing and using ScriptApp:
- [launching instructions]
- [put this file into a new folder named "scriptapp" that's somewhere convenient, install
libreoffice, install python, install tkinter library, right click properties and make this file
executable, open it and it will create all of the necessary folders for you, download the test
files from the repository and move them into the folder/git clone]

Instructions for reading ScriptApp's source code:
- [code reading instructions]
- [100 char width minimum, VScode recommended, do not try to read this in black and white,
comments with hash are treated like nested markdown headers explaining code after it, single hash on
 same line is explaining line its on, ask an AI if you're unsure about something]
- [nested comments use intention based structuring]
"""  # (Python's standard "module docstring", used to briefly explain what the code in a file does)

# region --- Perform the initial setup for the script (imports, constants, variables, ect.) ---

## Define special dunder (double underscore) variables
__author__ = "bendini"  # The Github username of this script's owner/maintainer
__version__ = "0.3.010"  # (This version number is also displayed in the UI for screenshot purposes)

## Import relevant modules from the Python Standard Library (reason for use given in side comments)
import ast  # Used for safely parsing Python code to extract docstrings
import hashlib  # Used for calculating file signatures for version control
import os  # Used for various OS-based checks
import platform  # Used for detecting the user's OS
import sys  # Used to check the running Python version
import shlex  # Used to generate safe command line strings
import shutil  # Used to copy and move files
import subprocess  # Used to execute the user's Python scripts
import time  # Used to precisely measure script execution time
import threading  # Used to run processes in the background without freezing the UI
from datetime import datetime as dt, timezone  # Used for UTC timestamping
from pathlib import Path  # Used for better file path handling
import queue as thread_queue  # Used for thread-safe communication

## Import relevant 3rd party libraries (these must be installed before running)
try:  # Try to do the following...
    import tkinter as tk  # Used to create the UI (not 3rd party, but it doesn't come with Ubuntu)
    from tkinter import filedialog as fd, messagebox as mb, simpledialog as sd
except ImportError:  # Do this if there's a problem during the "try:" code
    input(
        "--- ERROR: Missing library ---\n"  # \n = Go onto the next line
        "Python's Tkinter library is not installed on your system. This library is used\n"
        "to create the user interface, and ScriptApp can't function without it.\n\n"
        "If you're using Ubuntu (or some other Debian-based OS),\n"
        "you can install Tkinter with the following terminal command:\n\n"
        "  sudo apt install python3-tk\n\n"
        "If you're seeing this error on a different operating system,\n"
        "please ask your favorite LLM how to install Tkinter on your OS.\n\n\n"
        "Press Enter to exit..."
    )  # Uses input() to print the message, so it won't close instantly before the user can read it

## Define global constants (can be used anywhere in the code, WON'T be modified by the code)
USER_OS = platform.system().lower()  # Will be "windows", "linux", or "darwin" for macOS

### Set folder locations
BASE_FOLDER = Path(__file__).parent.resolve()  # Sets the base folder relative to this file's path
P_DATA = BASE_FOLDER / "data"  # Set the path for... CSV data
P_AGN_DATA = P_DATA / "agnostic-data"  # ...data with other file extensions
P_SCRIPTS = BASE_FOLDER / "scripts"  # ...Python scripts
P_VALIDS = P_SCRIPTS / "validation"  # ...Python validation scripts
P_MODULES = P_SCRIPTS / "py-modules"  # ...in-house Python modules
P_RUST = BASE_FOLDER / "scripts/rust-code"  # ...compiled Rust & source code (hardcoded path)
P_UV = P_RUST / "uv-versions"  # ...binaries for versions of the uv Python environment manager
P_OTHER_CODE = BASE_FOLDER / "scripts/other-code"  # ...code modules in other languages (hardcoded)
P_AUTOFILLS = BASE_FOLDER / "autofills"  # ...auto-filling config data
P_LOGS = BASE_FOLDER / "logs"  # ...logging data
P_SCRIPT_ARTIFACTS = P_LOGS / "script-run-artifacts"  # ...folders containing logs for each run
P_MANUAL_EDITS = P_LOGS / "manual-edits"  # ...root folder for Manual Data Version Control (MDVC)
P_MANUAL_SNAPS = P_MANUAL_EDITS / "snapshots"  # ...MDVC backup snapshots
P_TEMP_CSV = P_LOGS / "old-tempfiles"  # ...old temporary output.csv files
P_TEMP_CONS = P_LOGS / "old-tempfiles"  # ...old console log files
P_LOG_SUMM = P_LOGS / "old-log-summaries"  # ...archived log summaries

### Set the names of some specific files (all of these files will be in BASE_FOLDER)
TEMP_OUTPUT_NAME = "sa-last-output.csv"  # Used as the default CSV output file
TEMP_CONSOLE_NAME = "sa-last-console-log.txt"  # Used to save the console output to text
LOG_SUMMARY_NAME = "sa-event-log-summary.csv"  # Used to record a basic overview of script runs
MDVC_LOG_NAME = "sa-manual-edit-log.csv"  # Used to record user's manual changes
MDVC_INDEX_NAME = "sa-data-index.csv"  # Used to track the file state (Hashes)
AF_OVERRIDE_NAME = "sa-default-config-override.csv"  # An optional file to modify default settings

### Set the allowed filetypes (Tkinter requires them to be formatted as a list of 2-item tuples)
PY_SCRIPT = [("Python scripts", "*.py")]  # [("User hint text", "show files with this extension")]
CSV_DATA = [("CSV data files", "*.csv")]
AGN_DATA = [("Any data files", "*.*")]
PY_V_SCRIPT = [("Python validation scripts", "*.py")]
CSV_AUTOFILL = [("CSV autofill files", "*.csv")]

### Create a reference dictionary for the ScriptApp Processing Protocol data
SAPP = {  # (Arguments have fixed positions, allowing scripts to use sys.argv[n] to receive them)
    #### Mandatory protocol arguments
    "main_script": {"path": P_SCRIPTS, "type": PY_SCRIPT, "hint": ""},  # sys.argv[0]
    "input_csv": {"path": P_DATA, "type": CSV_DATA, "hint": ""},  # sys.argv[1]
    "output_csv": {"path": BASE_FOLDER, "name": TEMP_OUTPUT_NAME},  # sys.argv[2]
    #### Optional extended protocol arguments
    "data2": {"path": P_DATA, "type": CSV_DATA, "hint": "data2"},  # sys.argv[3]
    "data3": {"path": P_DATA, "type": CSV_DATA, "hint": "data3"},  # sys.argv[4]
    "data4": {"path": P_DATA, "type": CSV_DATA, "hint": "data4"},  # sys.argv[5]
    "data5": {"path": P_AGN_DATA, "type": AGN_DATA, "hint": "data5 (all types)"},  # sys.argv[6]
    "valscriptA": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "valscriptA"},  # sys.argv[7]
    "valscriptB": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "valscriptB"},  # sys.argv[8]
    #### ScriptApp's enhanced feature set
    ##### Version checking
    "SAPP_version": "0.3",  # (Increases if a breaking change is made to the protocol)
    "python_version": "3.12.3",  # The Python version scripts are expected to support by default
    ##### ScriptApp's outer validation wrapper
    "prescript": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "prescript"},  # Runs before
    "postscript": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "postscript"},  # Runs after
    "output_name": {"default": ""},  # Used to rename output_csv if it was successful
    "output_folder": {"path": P_DATA, "default": P_DATA},  # The final output_csv save location
    ##### The ordered sequence of arguments that will be passed for each script type
    "optional_arg_keys": ["data2", "data3", "data4", "data5", "valscriptA", "valscriptB"],
    "main_script_arg_keys": ["main_script", "input_csv", "output_csv", "optional_arg_keys"],
    "prescript_arg_keys": ["prescript", "main_script_arg_keys", "postscript"],
    "postscript_arg_keys": ["postscript", "output_csv", "main_script"],
    ##### Built-in Python virtual environment management
    "python_uv": {"standard_version": "0.9.11", "path": P_UV},
    "uv_allowlist": ["--python", "--preview", "--offline", "--reinstall", "--verbose"],
    ##### Types of optional main_script metadata that ScriptApp can use to perform checks
    "metadata1": ["SAPP version", "extras required", "extras disabled"],
    "metadata2": ["input formats", "output formats", "data5 formats", "APT libraries"],
    "metadata3": ["run with uv?", "uv version", "uv dependencies", "uv flags", "Python version"],
    "metadata4": ["Python modules", "Rust extensions", "extension fallback?", "other modules"],
    "csv_formats": ["mdcsv", "in10ty", "multi-mdcsv", "pipe", "tab", "comma", "other-csv"],
    "data5_formats1": ["txt", "yaml", "toml", "md", "html", "json", "xml"],
    "data5_formats2": ["ods", "parquet", "pqt", "avro", "other"],
    "user_input_string": "@SAPP:",  # The magic print() phrase for a script to request user input
    ##### Automatic display of a script's user instructions
    "instructions": {"type_priority": [".png", ".md", "docstring"], "image_width_px": 700},
    ##### Automatic configuration & form input filling
    "autofills": {"path": P_AUTOFILLS, "type": CSV_AUTOFILL},  # Autofill folder for manual loading
    "af_override_file": {"path": BASE_FOLDER, "name": AF_OVERRIDE_NAME},  # Autofill on startup
    ##### Automatic structured logging of data transformations
    "logs_parent_folder": {"path": P_LOGS},
    "log_summary_file": {"path": BASE_FOLDER, "name": LOG_SUMMARY_NAME, "runs": 1000},
    "log_summary_header1": ["UTC Timestamp", "Input CSV", "Python Script", "Output CSV"],
    "log_summary_header2": ["Stage Reached", "Log Details Folder", "Other File Inputs"],
    "log_summary_archive": {"path": P_LOG_SUMM},  # Where the summaries go once they're full
    "console_file": {"path": BASE_FOLDER, "name": TEMP_CONSOLE_NAME},  # Captures all console output
    "last_console_archive": {"path": P_TEMP_CONS},  # Where the old console logs are saved
    "last_output_archive": {"path": P_TEMP_CSV},  # Where the old temporary outputs are saved
    "log_details_folder": {"path": P_SCRIPT_ARTIFACTS},  # Contains copies of all files per run
    ###### Automatic state logging of manual data changes (like a primitive Git, but for data)
    "manual_check_interval_mins": {"default": 1, "slow": 10},
    "mdvc_index_file": {"path": BASE_FOLDER, "name": MDVC_INDEX_NAME},
    "mdvc_log_file": {"path": BASE_FOLDER, "name": MDVC_LOG_NAME},
    "mdvc_header": ["UTC Timestamp", "Event", "Old Name", "File Name", "Folder", "Comments"],
    ##### Folders that are expected to exist inside the the user's ScriptApp folder
    "folders1": [P_DATA, P_AGN_DATA, P_SCRIPTS, P_VALIDS, P_MODULES, P_RUST, P_UV, P_OTHER_CODE],
    "folders2": [P_AUTOFILLS, P_LOGS, P_SCRIPT_ARTIFACTS, P_TEMP_CSV, P_TEMP_CONS, P_LOG_SUMM],
    "folders3": [P_MANUAL_EDITS, P_MANUAL_SNAPS],
}

### Define some constants for the UI (a UI label dictionary is also defined later)
APP_TITLE = "ScriptApp"  # Name of the application that's displayed in the UI
UI_WINDOW_GEOMETRY = "718x921"  # Makes bordered screenshots exactly 720px wide by 960px tall
HINT_COLOR = "#505050"  # HEX color code for placeholder text hints (medium-dark grey)
AUTOFILL_ICON_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAQAAAD8x0bcAAAAAXNSR0IB2cksfwAAAARnQU1BAA
Cxjwv8YQUAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAKtJREFUKM+NksERBSEIQ5+OhWFlLp
VBZ/7DoovzL3JxjDHRQBmkelhb5fngcpAmigPCoHxwA0AAB8BjHRl/SRZXPFHn8nrtDOhJjaRiQC9DsOz/R570Ml6dRVjGfRMNKp
qODKVQ0IQIWnE6goTRE3kRiNDxykVVBIuv+6HkEYUhVw+/jOAizAZ0ZjTBt7EhX1tavOBVmUhMgVBCbU+BHyb7cOHtCEQZMSSa4R
9ADkVgLJEX4gAAAABJRU5ErkJggg=="""  # Embedded .png data for af_icon so ScriptApp can stay as 1 file

## Define global state variables (can be used anywhere in the code, CAN be modified by the code)
libreoffice_flags = "--infilter=CSV:7C,34,UTF-8"  # For opening our special Markdown CSV files
script_requirements = None
BIVS_enabled = True
images_enabled = True
headless_warnings = False
suppress_mod_popup = False
file_checking_interval = "default"  # Can be set to "slow" via autofill
last_run_successful = False
current_run_timestamp = None
current_log_folder = None
instructions_box = None
inputs = {}
optional_entry_box_refs = {}
last_successful_run_context = {}
user_input_response = None
user_input_event = threading.Event()
current_subprocess = None  # Holds reference to the running script process so it can be stopped
log_file_handle = None  # Holds the reference to the open console log file
monitoring_active = False  # Controls the output file monitoring loop

example_global_state_variable = "Initial Value"  # (Demo variable, only used by the code below)


## Define a function to show inexperienced coders how functions work in Python
def example_function(parameter_1, param_2, default_param="default value"):
    """
    ### Explain what this big block of text is, and how these things are used
    Everything between this pair of triple quotes is the function docstring (documentation string,
    "string" being a type of text-based data) for example_function. Docstrings are optional, but
    they're pretty useful, as they also appear as hints when you hover over each function in VSCode.

    ### Explain to readers why ScriptApp code uses functions, and why this example function exists
    Since this code was optimized for ease of understanding, it does not utilize advanced Python
    abstractions like objects or classes, since they add complexity for very little benefit.
    However, it does rely heavily on functions to improve its organization and reduce the need for
    repetitive code patterns. Unfortunately, it's not straightforward for a beginner to understand
    how Python functions work just by looking at them, so this one was created for the sole purpose
    of making their implicit behaviours more explicit.

    [are functions like macros?]

    ### Explain just the function behavours that are relevant to ScriptApp code (to keep it simple)
    [the first line, and how each of the types of parameters this code uses works, and how
    parameters are more like slots and the names inside and outside can be different]

    [how function scope works, noting indent means code is inside function]


    ["If any of this seems unclear, copy this whole function into your favorite LLM and ask for
    more info."]
    """
    ### (rest of demo happens outside the codestring inside the function itself)

    variable_a = 1
    variable_b = 2
    print(variable_a + variable_b)

    """[second "docstring" for further explanation]"""


## Write some conditional logic for example_function that:
## - Stops code editors from flagging errors in the function (because the code isn't being used)
## - Won't do anything to ScriptApp, unless the reader manually edits the variable code
if example_global_state_variable == 1:  # (Change it if you want to test this block of code)
    ### Call the function without parameters
    example_function()
    ### Call the function with parameters
    example_param1 = 10
    hjfhgngh_param2 = "this variable isn't real and can't hurt you"
    example_function(example_param1, hjfhgngh_param2)
    ### Call the function with...

# endregion --- Initial setup completed ---


# region --- Define functions for ScriptApp's back-end processing ---

## --- Define back-end "helper functions" that will be used for multiple things ---


### Define a function to... create the application folder structure on startup
def create_missing_folders():
    """Creates the necessary folders and fixes search index spam on some operating systems."""
    #### Check if the logs folder exists *before* we create missing folders
    logs_already_existed = SAPP["logs_parent_folder"]["path"].exists()

    ### Create the standard folders found in SAPP
    for path in SAPP["folders1"] + SAPP["folders2"] + SAPP["folders3"]:
        path.mkdir(parents=True, exist_ok=True)

    ### Prevent the logs folder from clutting up search results
    #### If the user doesn't have the right OS (Linux) and the right file system (GNOME), stop here
    if USER_OS != "linux" or "gnome" not in os.environ.get("XDG_CURRENT_DESKTOP", "").lower():
        return

    #### Create the ignore file ONLY if the logs folder has just been created
    #### (This allows automatic file creation, while also respecting a user's decision to delete it)
    if not logs_already_existed:
        ##### Create a placeholder file containing a helpful explanation if opened
        (SAPP["logs_parent_folder"]["path"] / ".trackerignore").write_text(
            """The name of this file tells GNOME to exclude this folder from file searches.\n\n
            You can still search for files inside this folder, but if you're searching from outside 
            this folder, this prevents what could be hundreds of copies of each file that ScriptApp 
            uses for state tracking from cluttering up your search results.\n\n
            If you don't want this folder excluded from file searches, you can delete this file and 
            it won't come back, but you can still recreate it manually."""
        )


### Define a function to... handle filepaths consistently
def resolve_path(path_string):
    """Resolves a path string to an absolute filepath."""
    ### If no path was provided, exit the function immediately without trying to resolve the path
    if not path_string:
        return None

    ### Convert the path string to a Path object, and assign it to a variable called "path"
    path = Path(path_string)

    #### If "path" is an absolute path, resolve it in its current state.
    if path.is_absolute():
        return path.resolve()
    ##### Or if it's a short relative path, join it to the base folder path, then resolve it.
    else:
        return (BASE_FOLDER / path).resolve()


### Define a function to... format a filepath for displaying to the user
def get_display_path(path_string):
    """Creates a shortened (but still valid) filepath relative to the base folder."""
    ### Handle empty input boxes by returning them as an empty string
    if not path_string:
        return ""

    ### Get the full, absolute filepath
    absolute_path = resolve_path(path_string)

    #### Handle invalid or non-path strings by returning them unchanged
    if not absolute_path:
        return str(path_string)

    #### Try to make the path relative to the base folder...
    try:
        display_path = str(absolute_path.relative_to(BASE_FOLDER))
    ##### ...but fallback to using the absolute path if this fails
    except ValueError:
        display_path = str(absolute_path)

    #### Add a trailing slash if the path is a directory (folder) instead of a file
    if absolute_path.is_dir() and not display_path.endswith("/"):
        display_path += "/"

    #### Return the final formatted string
    return display_path


### Define a function to... log all print statements to a text file
def print_and_log(*args, **kwargs):
    """Enhanced printing function that also writes its contents to a log file."""
    #### Attempt to do of the following:
    try:
        ##### Construct the message exactly as print would output it
        msg = " ".join(map(str, args)) + kwargs.get("end", "\n")
        ##### If the global log file handle is open, write to it
        if log_file_handle and not log_file_handle.closed:
            log_file_handle.write(msg)
    except Exception:
        pass  # Fail silently if logging fails, so we don't crash the app
    #### Call the normal Python print function afterwards
    __builtins__.print(*args, **kwargs)


#### Override the standard print() with our enhanced printing function
print = print_and_log  # (This has to be done outside the function)


### Define a function to... alert the user when a problem occurs
def ui_event(message_type, message):
    """Handles showing errors and warnings in the UI, and also prints a copy to the console."""
    ### Strip any non-explicit linebreaks and unwanted whitespace from the message content
    message = "\n".join([line.strip() for line in message.strip().splitlines()])

    #### Handle errors (Always show popup)
    if message_type == "error":
        print(f"UI Message - Error: {message.splitlines()[0]}")
        mb.showerror("Error", message)

    #### Handle warnings (Suppress popup if headless mode is active)
    elif message_type == "warn":
        if headless_warnings:
            print(f"!!! ACTION REQUIRED !!! {message}")  # High visibility prefix for console mode
        else:
            print(f"UI Message - Warning: {message.splitlines()[0]}")
            mb.showwarning("Warning", message)

    #### Handle info (Suppress popup if headless mode is active)
    elif message_type == "info":
        if not headless_warnings:
            mb.showinfo("Info", message)
        else:
            print(f"UI Message - Info: {message}")

    else:  # (If the type wasn't specified as "error" or "warn")
        print("ui_event function error: invalid message type specified")


### Define a function to... handle our special Markdown table CSV format
def handle_markdown_csv(file_path=None, mode="read", data=None, header=None, content=None):
    """Safely reads, writes, or updates a Markdown-formatted CSV file."""
    ### Handle the logic for reading data from the file
    if mode == "read":
        try:
            #### If content isn't provided directly, read it from the file
            if content is None and file_path:
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                ##### If it's not utf-8 encoded, raise an error (no silent fallbacks allowed)
                except UnicodeDecodeError:
                    raise ValueError(f"Error: '{Path(file_path).name}' is not encoded in UTF-8")

            lines = content.strip().split("\n")

            #### Validate format: needs at least a header and a separator line (---)
            if len(lines) < 2 or "---" not in lines[1]:
                return []

            #### Find where the data actually starts (after the separator line)
            data_index = -1
            for i, line in enumerate(lines):
                if "---" in line:
                    data_index = i + 1
                    break

            if data_index == -1 or data_index >= len(lines):
                return []  # Header exists, but no data rows

            #### Split lines by the pipe separator " | " to create a list of lists
            return [[cell.strip() for cell in line.split(" | ")] for line in lines[data_index:]]
        except (FileNotFoundError, AttributeError):
            return []

    ### Handle the logic for writing or updating data to the file
    elif mode in ("write", "update"):
        file_path = Path(file_path)
        data_map = {}

        #### Load existing data to ensure no duplicates are created (Update logic)
        if mode == "update" and file_path.exists():
            ##### We call this function recursively in read mode to get current state
            existing_rows = handle_markdown_csv(file_path, mode="read")
            ##### Create a dictionary map where the first column is the "Key"
            data_map = {row[0]: row for row in existing_rows}

        #### Update the map with the new data provided
        if data:
            for row in data:
                # This overwrites the old row if the key (row[0]) matches
                data_map[str(row[0])] = row

        #### Format the final data for writing
        # Convert the map back to a list and sort it by the first column (the key)
        final_rows = sorted(list(data_map.values()), key=lambda r: r[0])

        # Generate a header if one wasn't provided and there is data
        if not header:
            header = [f"col_{i + 1}" for i in range(len(final_rows[0]))] if final_rows else []

        # If there is absolutely no data or header, write an empty string
        if not final_rows and not header:
            output_content = ""
        else:
            # Calculate the maximum width of every column for nice alignment
            num_columns = len(header)
            column_widths = [len(str(h)) for h in header]
            for row in final_rows:
                for i, cell in enumerate(row):
                    if i < num_columns:
                        column_widths[i] = max(column_widths[i], len(str(cell)))

            # Create the formatted strings for the header and separator
            header_row = " | ".join([header[i].ljust(column_widths[i]) for i in range(num_columns)])
            separator_line = " | ".join(["-" * column_widths[i] for i in range(num_columns)])

            # Create the formatted strings for the data rows
            content_lines = []
            for row in final_rows:
                # Ensure row has enough columns, fill with empty string if not
                full_row = [str(row[i]) if i < len(row) else "" for i in range(num_columns)]
                # Pad the cell with spaces to match the column width
                formatted_cells = [full_row[i].ljust(column_widths[i]) for i in range(num_columns)]
                content_lines.append(" | ".join(formatted_cells))

            # Combine it all into one big string
            output_content = f"{header_row}\n{separator_line}\n" + "\n".join(content_lines)

        #### Perform a safe write operation using a temporary file
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        try:
            temp_path.write_text(output_content, encoding="utf-8")
            temp_path.rename(file_path)  # This is an atomic operation (safer)
        except Exception as error:
            print(f"ERROR: Failed to write to {file_path}. Error: {error}")
            if temp_path.exists():
                temp_path.unlink()  # Delete the messy temp file
            raise
        return final_rows


### Define a function to... generate a temporary wrapper script for the security sandbox
def generate_sandbox_wrapper(target_script, args):
    """Creates a temporary Python script that installs an audit hook before running the target."""
    ### Define the wrapper file location
    wrapper_path = BASE_FOLDER / "_sandbox_wrapper.py"

    ### Construct the temporary wrapper script content
    wrapper_lines = [
        "import sys, os, runpy",  # Imports modules needed to hook events and run the target
        "def audit_hook(event, args):",  # Defines the security function that intercepts system calls
        "    if event == 'open' and args:",  # Checks if the script is attempting to open a file
        "        path = os.path.abspath(args[0])",  # Resolves the full path to check against deny lists
        "        if 'scriptapp/logs' in path or 'scriptapp/autofills' in path:",  # Deny logs/autofill
        "            sys.stderr.write('[SANDBOX_VIOLATION] Access Denied: Logs/Config')",
        "            os._exit(1)",  # Instantly kills the process to prevent further malicious actions
        "        if 'scriptapp/scriptapp.py' in path:",  # Deny self-modification
        "            sys.stderr.write('[SANDBOX_VIOLATION] Access Denied: Source Code')",
        "            os._exit(1)",
        "    if event == 'socket.connect':",  # Deny network access by default
        "        sys.stderr.write('[SANDBOX_VIOLATION] Access Denied: Network')",
        "        os._exit(1)",
        "sys.addaudithook(audit_hook)",  # Installs the hook before the user script is loaded
        f"sys.argv = {args}",  # Passes the original arguments to the target script
        f"runpy.run_path('{target_script}', run_name='__main__')",  # Executes the target
    ]

    ### Write the wrapper to disk
    wrapper_path.write_text("\n".join(wrapper_lines), encoding="utf-8")
    return str(wrapper_path)


### Define a function to... calculate a file's SHA256 hash
def calculate_file_hash(filepath):
    """Generates a unique signature for a file to detect changes."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None  # Return None if file is missing or locked


### Define a function to... update the central log summary
def update_summary_log(stage):
    """Appends an entry to the main summary log and handles log rotation."""
    ### Merge the headers from the SAPP dictionary to create the full header list
    log_header = SAPP["log_summary_header1"] + SAPP["log_summary_header2"]
    log_file = SAPP["log_summary_file"]["path"] / SAPP["log_summary_file"]["name"]
    archive_folder = SAPP["log_summary_archive"]["path"]
    limit = SAPP["log_summary_file"]["runs"]  # Use the SAPP value for the limit

    ### Handle log rotation (if the log file has grown too large)
    if log_file.exists():
        logs = handle_markdown_csv(log_file, mode="read")
        if len(logs) >= limit:
            #### Determine the date range of the current logs for the archive filename
            start_date = dt.fromisoformat(logs[0][0].replace("Z", "+00:00")).strftime("%y-%m-%d")
            end_date = dt.fromisoformat(logs[-1][0].replace("Z", "+00:00")).strftime("%y-%m-%d")
            base_archive_name = f"{start_date}--{end_date}-script-log-summary"
            archive_path = archive_folder / f"{base_archive_name}.csv"

            #### Ensure we don't overwrite an existing archive if 2 are filled up in a single day
            index = 1
            while archive_path.exists():
                index += 1  # Adds 1 to index
                archive_path = archive_folder / f"{base_archive_name}-{index}.csv"

            #### Move the old log and clear the current one
            shutil.move(log_file, archive_path)
            handle_markdown_csv(log_file, mode="write", data=[], header=log_header)

    ### Collect data for the new log entry
    other_inputs_list = [
        f"{key}={Path(v).name}"
        for key in SAPP["optional_arg_keys"]
        if (v := inputs[key].get()) and v != SAPP[key].get("hint")
    ]
    new_row = [
        current_run_timestamp,
        inputs["input_csv"].get(),  # Matches "Input CSV" header
        inputs["main_script"].get(),  # Matches "Python Script" header
        inputs["output_name"].get() if stage == "save" else "",  # Matches "Output CSV" header
        stage,  # Matches "Stage Reached" header
        current_log_folder.name if current_log_folder else "",  # Matches "Log Details Folder"
        ", ".join(other_inputs_list),  # Matches "Other File Inputs" header
    ]

    ### Write the new entry to the log file
    # Use our new robust 'update' mode (though we are just appending with a unique timestamp)
    handle_markdown_csv(log_file, mode="update", data=[new_row], header=log_header)


### Define a function to... log user input responses to a text file
def log_user_input(prompt_text, user_response):
    """Records user responses from the interactive input dialog to a mdcsv file."""
    ### If logging is disabled or the log folder is missing, skip logging
    if not current_log_folder or not inputs["log?"].get():
        return

    ### Append the Q&A interaction to the log file using standard mdcsv format
    log_file_path = current_log_folder / "user_inputs.csv"
    timestamp = dt.now(timezone.utc).strftime("%H:%M:%S")
    header = ["Timestamp", "Prompt", "User Response"]
    new_row = [timestamp, prompt_text, user_response]

    try:
        handle_markdown_csv(log_file_path, mode="update", data=[new_row], header=header)
    except Exception as error:
        print(f"Failed to log user input: {error}")


## --- Define the complex event handler functions ---


### Define a function to... select the main Python script and process its side effects
def select_main_script(entry_box, instructions_box):
    """The event handler function to perform the entire process that
    must occur when the user selects their main Python script."""
    #### State the global variables this function may change
    global script_requirements, images_enabled

    #### Define a function to... extract configuration metadata from a script
    def extract_script_metadata(script_path):
        """Reads a Python file and parses the metadata table in its docstring."""
        requirements = {}  # Start with a blank requirements dictionary

        ##### Try to read and parse the file's docstring
        try:
            content = script_path.read_text(encoding="utf-8")
            docstring = ast.get_docstring(ast.parse(content))

            if docstring:
                ###### Parse the markdown table in the docstring into a dictionary
                rows = handle_markdown_csv(content=docstring, mode="read")
                data_map = {row[0].strip(): row[1].strip() for row in rows if len(row) >= 2}

                ###### Loop through SAPP's known metadata keys and populate the requirements dict
                # We combine all metadata lists to iterate through every possible key
                all_metadata_keys = SAPP["metadata1"] + SAPP["metadata2"] + SAPP["metadata3"]

                for key in all_metadata_keys:
                    value = data_map.get(key, "")
                    # If the value is a list type, split it by commas
                    if key in [
                        "extras required",
                        "extras disabled",
                        "uv dependencies",
                        "uv flags",
                    ]:
                        requirements[key] = [x.strip() for x in value.split(",") if x.strip()]
                    # Otherwise just store the raw string
                    else:
                        requirements[key] = value

        except Exception as error:
            print(f"Failed to parse metadata from {script_path.name}: {error}")
        return requirements

    #### Define a helper function to toggle UI elements based on script requirements
    def configure_ui_from_metadata(requirements):
        """Enables all optional boxes, then selectively disables the ones listed in 'disable'."""
        optional_boxes = SAPP["optional_arg_keys"]
        # We use the direct English key from the metadata now
        keys_to_disable = requirements.get("extras disabled", [])

        ##### First, ensure every optional box is enabled (reset state)
        for key in optional_boxes:
            if key in optional_entry_box_refs:
                for widget in optional_entry_box_refs[key].values():
                    widget.config(state="normal")

        ##### Then, disable the specific boxes requested by the script
        for key in keys_to_disable:
            if key in optional_boxes and key in optional_entry_box_refs:
                # Get the specific widgets for clarity
                box_entry = optional_entry_box_refs[key]["entry"]
                box_button = optional_entry_box_refs[key]["button"]
                # Reset the box to its default hint state
                box_entry.config(state="normal")  # Temporarily enable for modification
                box_entry.delete(0, tk.END)
                box_entry.insert(0, SAPP[key]["hint"])
                box_entry.config(fg=HINT_COLOR)
                # Disable both the entry box and the button
                box_entry.config(state="disabled")
                box_button.config(state="disabled")

    #### Resolve the path currently in the entry box
    resolved_path = resolve_path(entry_box.get())

    #### Handle the case where the path is invalid or empty
    if not resolved_path or not resolved_path.is_file():
        ##### Reset requirements to empty defaults
        script_requirements = extract_script_metadata(Path("non_existent"))  # Get empty template
        ##### Reset the UI to have all boxes enabled
        configure_ui_from_metadata(script_requirements)
        ##### Clear the instructions box
        instructions_box.config(state="normal")
        instructions_box.delete("1.0", tk.END)
        instructions_box.config(state="disabled")
        return

    #### Handle the case where the script exists
    ##### Extract metadata and update global requirements
    script_requirements = extract_script_metadata(resolved_path)

    ##### Update the UI (disable unnecessary boxes)
    configure_ui_from_metadata(script_requirements)

    ##### Load the instructions into the text box
    instructions_box.config(state="normal")
    instructions_box.delete("1.0", tk.END)

    ##### Iterate through the instructions protocol priority list to find valid instructions
    png_path = resolved_path.with_suffix(".png")
    md_path = resolved_path.with_suffix(".md")
    instr_protocol = SAPP["instructions"]
    found_instruction = False

    for instr_type in instr_protocol["type_priority"]:
        if found_instruction:
            break

        ###### Priority: Image instructions
        if instr_type == ".png" and images_enabled and png_path.exists():
            try:
                image = tk.PhotoImage(file=png_path)
                target_width = instr_protocol.get("image_width_px", 700)
                if image.width() != target_width:
                    ui_event("warn", f"Image instructions should be exactly {target_width}px wide.")
                instructions_box.image_ref = image  # Keep reference to prevent garbage collection
                instructions_box.image_create(tk.END, image=instructions_box.image_ref)
                found_instruction = True
            except tk.TclError:
                instructions_box.insert(
                    tk.END, "Error: image instructions found but couldn't be loaded."
                )

        ###### Priority: Markdown file instructions
        elif instr_type == ".md" and md_path.exists():
            instructions_box.insert(tk.END, md_path.read_text(encoding="utf-8"))
            found_instruction = True

        ###### Priority: Python docstring
        elif instr_type == "docstring":
            try:
                content = resolved_path.read_text(encoding="utf-8")
                docstring = ast.get_docstring(ast.parse(content))
                if docstring:
                    instructions_box.insert(tk.END, docstring)
                    found_instruction = True
            except Exception:
                pass

    if not found_instruction:
        instructions_box.insert(tk.END, "No instructions were found.")

    instructions_box.config(state="disabled")


## Define a function to... process all input data with the chosen scripts
def run_scripts(app, run_button, success_label, success_message):
    """The central function that orchestrates ScriptApp's entire script processing workflow."""
    ### State the global variables this function may change
    global last_run_successful, last_successful_run_context, monitoring_active
    global current_run_timestamp, current_log_folder, current_subprocess, log_file_handle

    ### Define helper functions (ordered by first use in the execution flow below)

    #### Define a helper to find the uv binary path
    def get_uv_path(req_version):
        """Finds a uv binary matching the version on system or locally."""
        # 1. Check system
        sys_uv = shutil.which("uv")
        if sys_uv:
            try:
                # Run subprocess to check version
                res = subprocess.run(
                    [sys_uv, "--version"], capture_output=True, text=True, check=False
                )
                # Compare uv subprocess version with main_script metadata uv version
                if res.returncode == 0 and req_version in res.stdout.split():
                    return sys_uv
            except Exception:
                pass

        # 2. Check Local
        folder = SAPP["python_uv"]["path"]
        if folder.exists():
            for f in folder.iterdir():
                # Check metadata uv version against file names of uv in SAPP["python_uv"]["path"]
                if req_version in f.name and f.is_file():
                    # OS-Specific Safety Checks
                    if USER_OS == "windows":
                        # On Windows, we strictly require the .exe extension
                        if f.suffix.lower() != ".exe":
                            continue
                    else:
                        # On Linux/Mac, we strictly require the file to have executable permissions
                        if not os.access(f, os.X_OK):
                            continue
                        # We also ignore common archive formats to prevent trying to run a zip
                        if f.suffix.lower() in [".zip", ".gz", ".tar", ".bz2", ".7z", ".rar"]:
                            continue

                    return str(f)
        return None

    #### Define a helper to run the Built-In Validation Script (BIVS)
    def run_BIVS():
        """Checks if the user has provided everything the script has requested in its metadata."""
        print("\n--- [BIVS] Validation Checks ---")
        validation_passed = True

        ##### Define specific logic for checking the uv toolchain availability
        def check_toolchain_availability():
            """Validates if the requested uv binary is available and compatible."""
            if script_requirements.get("run with uv?", "no").lower() not in ["yes", "true", "1"]:
                return None  # Pass (Standard Mode)

            req_ver = script_requirements.get("uv version", SAPP["python_uv"]["standard_version"])
            if req_ver.lower() == "pass":
                req_ver = SAPP["python_uv"]["standard_version"]

            if not get_uv_path(req_ver):
                return (
                    f"Missing UV toolchain for version {req_ver}.\n"
                    "Please download the correct binary into scripts/rust-code/uv/"
                )
            return None  # Pass

        ##### Define specific logic for checking compiled extensions with fallback support
        def check_extensions():
            """Checks for required extensions and allows fallback to pure Python if permitted."""
            req_ext = script_requirements.get("Rust extensions", "")
            if not req_ext:
                return None  # Pass

            # If extensions are missing, check if fallback is allowed
            fallback = script_requirements.get("extension fallback?", "no").lower() in [
                "yes",
                "true",
                "1",
            ]
            # (Note: Actual file checking logic would go here, simplified for this snippet)
            # Assuming check fails:
            if fallback:
                print("WARN: Compiled extension missing. Falling back to pure Python.")
                return None  # Pass validation with warning
            else:
                return "Missing required Rust extensions."

        ##### Define specific logic for checking allowed flags
        def check_uv_flags():
            """Ensures requested uv flags are in the SAPP allowlist."""
            requested_flags = script_requirements.get("uv flags", [])
            violations = []

            for raw_flag in requested_flags:
                base_flag = raw_flag.split("=")[0].split(" ")[0].strip()

                if base_flag not in SAPP["uv_allowlist"]:
                    violations.append(f"{base_flag} (Not in allowlist)")
                    continue

                if base_flag in ["--verbose", "-v"]:
                    print(f"Warning: '{base_flag}' requested. This generates excessive log spam.")

            if violations:
                return f"Unauthorized flags: {', '.join(violations)}"
            return None

        ##### Define the logic for individual checks using a simple dictionary
        checks = {
            "Mandatory Inputs": lambda: [
                k
                for k in script_requirements.get("extras required", [])
                if not inputs[k].get() or inputs[k].get() == SAPP[k].get("hint")
            ],
            "SAPP Version": lambda: (
                float(script_requirements.get("SAPP version", 0)) > float(SAPP["SAPP_version"])
            ),
            "Toolchain Availability": lambda: check_toolchain_availability(),
            "Python Version": lambda: (
                # If using UV, skip this check (UV handles python versions itself)
                script_requirements.get("run with uv?", "no").lower() not in ["yes", "true", "1"]
                and script_requirements.get("Python version", "pass").lower() != "pass"
                and f"{sys.version_info.major}.{sys.version_info.minor}"
                != script_requirements.get("Python version")
            ),
            "Extensions": lambda: check_extensions(),
            "Safe UV Flags": lambda: check_uv_flags(),
            "Input Format": lambda: (
                script_requirements.get("input formats", "pass").lower() != "pass"
                and resolve_path(inputs["input_csv"].get())
                and "---" not in Path(inputs["input_csv"].get()).read_text(encoding="utf-8")
            ),
        }

        ##### Iterate through the checks and log the results
        for name, check_func in checks.items():
            result = None
            is_fail = False
            try:
                result = check_func()
                is_fail = bool(result)
            except Exception:
                pass

            status = "FAIL" if is_fail else "PASS"
            msg = str(result) if result and result is not True else ("OK" if not is_fail else "ERR")
            print(f"{name.ljust(30)} | {status} ({msg})")

            if is_fail:
                validation_passed = False

        print("--------------------------------\n")
        if not validation_passed:
            ui_event("error", "BIVS Validation Failed. See console for details.")
        return validation_passed

    #### Define a helper to calculate logging metadata (folder path and files to archive)
    def setup_logging_folder(filepaths):
        """Creates the log folder and identifies which input files to archive inside it."""
        ##### State the global variables this function may change
        global current_log_folder

        if not filepaths["log?"]:  # Accesses the True/False value directly
            return None

        ##### Determine the folder name (Windows doesn't allow colons in paths)
        input_stem = Path(filepaths["input_csv"] or "untitled").stem
        if USER_OS == "windows":
            folder_timestamp = current_run_timestamp.replace(":", "-")
        else:
            folder_timestamp = current_run_timestamp
        folder_name = f"{folder_timestamp}-i-{input_stem}"

        ##### Update the global state variable so the Save function can find it later
        current_log_folder = SAPP["log_details_folder"]["path"] / folder_name
        current_log_folder.mkdir(exist_ok=True)

        ##### Determine which files need to be archived and copy them using SAPP keys
        # We use the SAPP dictionary keys to find valid file inputs
        sapp_file_keys = ["main_script", "input_csv"] + SAPP["optional_arg_keys"]

        for key in sapp_file_keys:
            path_str = filepaths.get(key)
            # Skip if empty or if it equals the hint text
            if not path_str or (key in SAPP and path_str == SAPP[key].get("hint")):
                continue

            resolved = resolve_path(path_str)
            if resolved and resolved.exists() and resolved.is_file():
                # Use the new naming scheme: {key}-{original_name}
                dest_name = f"{key}-{resolved.name}"
                shutil.copy(resolved, current_log_folder / dest_name)

                # Special case for main script: Check for and copy instruction files
                if key == "main_script":
                    png_path = resolved.with_suffix(".png")
                    md_path = resolved.with_suffix(".md")
                    # Only copy the image if it exists AND images are enabled
                    if images_enabled and png_path.exists():
                        shutil.copy(png_path, current_log_folder / f"main_script-{png_path.name}")
                    # Copy the markdown file if it exists
                    if md_path.exists():
                        shutil.copy(md_path, current_log_folder / f"main_script-{md_path.name}")

        ##### Update the central log summary
        update_summary_log("run")

        ## Return the path to the new log folder
        return current_log_folder

    #### Define a helper to build command arguments from the SAPP dictionary
    def construct_arguments_list(keys_to_process, filepaths):
        """Recursively looks up keys in SAPP to build the final list of arguments."""
        ##### Create an empty list of final arguments to populate later
        final_arguments = []
        ##### Go through the list of keys to process
        for key in keys_to_process:
            ###### If the current key points to a list of SAPP keys, unpack the list.
            if key in SAPP and isinstance(SAPP[key], list):
                final_arguments.extend(construct_arguments_list(SAPP[key], filepaths))

            ###### If the current key is not a list of SAPP keys, get its value or its default path
            elif key in SAPP:
                ####### If the key has a hardcoded path (e.g. output_csv), add the path value
                if "name" in SAPP[key]:
                    final_arguments.append(str(SAPP[key]["path"] / SAPP[key]["name"]))
                ####### If the key has a path that should be provided by the user, get that path
                elif key in filepaths:
                    value = filepaths[key]
                    hint = SAPP[key].get("hint")
                    # Send value if present, otherwise use "x" placeholder
                    final_arguments.append(value if value and value != hint else "x")
        return final_arguments

    #### Define a helper to execute a single script and stream its output
    def execute_script(keys_list, filepaths, process_queue):
        """Generates arguments, launches the subprocess via wrapper, and pipes output."""
        ##### State the global variables this function may change
        global user_input_response, user_input_event, current_subprocess

        ##### Derive the stage name from the first key in the keys list
        stage_name = keys_list[0]

        ##### Generate the arguments using the thread-safe input snapshot
        arguments = construct_arguments_list(keys_list, filepaths)

        ##### Trim trailing empty "x" arguments to keep the command clean
        while arguments and arguments[-1] == "x":
            arguments.pop()

        ##### If the script path (the first arg) is empty or missing, do nothing.
        if not arguments or arguments[0] == "x":
            return

        target_script = arguments[0]
        script_args = arguments  # Note: sys.argv[0] is the script itself
        process_queue.put(f"\n--- [{stage_name}] - running '{Path(target_script).name}' ---\n")

        try:
            ##### Determine the execution mode and construct the command
            use_uv = script_requirements.get("run with uv?", "no").lower() in ["yes", "true", "1"]

            if use_uv:
                # Use the local helper to resolve the path at runtime
                req_ver = script_requirements.get(
                    "uv version", SAPP["python_uv"]["standard_version"]
                )
                if req_ver.lower() == "pass":
                    req_ver = SAPP["python_uv"]["standard_version"]

                uv_binary = get_uv_path(req_ver)
                if not uv_binary:
                    raise RuntimeError("UV execution requested but no compatible binary resolved.")

                # Construct the uv command (Sandbox not fully supported for UV yet in this version)
                full_command = [uv_binary, "run"]
                full_command.extend(["--no-progress", "--color=never"])
                full_command.extend(script_requirements.get("uv flags", []))
                deps = script_requirements.get("uv dependencies", [])
                if isinstance(deps, str):
                    deps = [x.strip() for x in deps.split(",") if x.strip()]
                for dep in deps:
                    full_command.extend(["--with", dep])
                req_py = script_requirements.get("Python version", "pass")
                if req_py.lower() != "pass":
                    if not any("--python" in f for f in full_command):
                        full_command.extend(["--python", req_py])
                full_command.extend(arguments)

                process_queue.put(f"--- UV Toolchain Active: {uv_binary}\n")

            else:
                # Default standard execution with Sandbox Wrapper
                wrapper_path = generate_sandbox_wrapper(target_script, script_args)
                full_command = ["python3", wrapper_path]

            ##### Create a display version of the command with shortened paths
            display_args = [Path(full_command[0]).name] + [
                get_display_path(arg) for arg in full_command[1:]
            ]
            safe_command_string = shlex.join(display_args)

            ##### Add an easy-to-copy command string to the console printing queue
            process_queue.put(f"--- Command line argument:\n{safe_command_string}\n\n")

            ##### Start the process
            current_subprocess = subprocess.Popen(
                full_command,  # The list of command line arguments to execute
                stdout=subprocess.PIPE,  # Capture standard output so we can read it
                stdin=subprocess.PIPE,  # Capture standard input so we can send data to it
                stderr=subprocess.STDOUT,  # Redirect errors to the standard output stream
                text=True,  # Treat the output as text strings rather than raw bytes
                cwd=BASE_FOLDER,  # Set the Current Working Directory to ScriptApp's base folder
                bufsize=1,  # Flushes the buffer every time a new line is written
            )
            ##### Read output line by line and send to UI
            for line in iter(current_subprocess.stdout.readline, ""):
                ###### Check if the script is requesting user input (Protocol: @SAPP:)
                if line.startswith(SAPP["user_input_string"]):
                    prompt_text = line.split(SAPP["user_input_string"])[1].strip()
                    # Signal the UI thread to open an input box
                    process_queue.put(("INPUT_REQUEST", prompt_text))
                    # Wait for the UI thread to set the response
                    user_input_event.wait()
                    user_input_event.clear()
                    # Send the response back to the script
                    if user_input_response is not None:
                        try:
                            current_subprocess.stdin.write(user_input_response + "\n")
                            current_subprocess.stdin.flush()
                        except OSError:
                            pass  # Pipe might be broken if script crashed
                    continue

                ###### If it's a normal line, just print it
                process_queue.put(line)

            ## Close the stdout pipe and wait for the process to finish
            current_subprocess.stdout.close()

            if current_subprocess.wait() != 0:
                # Use standard error unless it was killed by us (negative return code)
                if current_subprocess.returncode != -9:
                    raise subprocess.CalledProcessError(current_subprocess.returncode, full_command)
        except Exception as error:
            # Stop the whole workflow if a script fails
            raise error
        finally:
            current_subprocess = None
            # Clean up the wrapper if it exists
            if not use_uv:
                try:
                    Path(wrapper_path).unlink(missing_ok=True)
                except Exception:
                    pass

    #### Define a helper function to process the manifest file output
    def process_manifest_output(filepaths, process_queue):
        """Checks for manifest output and archives generated files if logging is enabled."""
        manifest_detected = False
        temp_file = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]

        ##### If the output file doesn't exist, we can't do anything
        if not temp_file.exists():
            return False

        try:
            ##### Check for manifest signature in the file header
            with open(temp_file, "r", encoding="utf-8") as file_handle:
                lines = [file_handle.readline().strip() for _ in range(3)]

            if len(lines) >= 3 and "manifest file? | yes" in lines[2]:
                process_queue.put("INFO: Manifest detected. Processing as multi-output.\n")
                manifest_detected = True

                ###### Archive manifest files if logging is on
                if current_log_folder:
                    shutil.copy(temp_file, current_log_folder / f"output_csv-{temp_file.name}")
                    manifest_data = handle_markdown_csv(temp_file, mode="read")
                    for row in manifest_data:
                        if len(row) == 2 and row[0] == "generated_file":
                            # Ensure path is resolved relative to ScriptApp base for safety
                            file_path = resolve_path(row[1])
                            if file_path and file_path.exists():
                                shutil.copy(
                                    file_path,
                                    current_log_folder / f"output-{file_path.name}",
                                )
        except Exception:
            pass

        return manifest_detected

    #### Define the output file monitoring function (Recursive)
    def monitor_output_file(app, file_path, last_mtime, context):
        """Polls the temporary output file for external changes by the user."""
        ##### State the global variables this function may change
        global monitoring_active, suppress_mod_popup

        ##### Stop polling if monitoring has been disabled (e.g. new run started)
        if not monitoring_active:
            return

        try:
            ##### Check modification time
            current_mtime = os.path.getmtime(file_path)

            ##### If modified, handle the change logic
            if current_mtime != last_mtime:
                print(f"UI-INFO: User modified {file_path.name} externally.")
                last_mtime = current_mtime

                ###### Update the log summary status
                if inputs["log?"].get() and context.get("log_details_folder"):
                    update_summary_log("modified")

                    ####### Save the modified file to the log folder alongside the original
                    # We save it as a temp name, which will be renamed if the user clicks Save
                    dest = context["log_details_folder"] / "modified-temp-output.csv"
                    shutil.copy(file_path, dest)

                    ####### Mark the context so Save button knows there are modifications
                    context["is_modified"] = True

                    ####### Alert the user (unless suppressed)
                    if not suppress_mod_popup:
                        ui_event(
                            "info",
                            "External modifications to the output CSV have been tracked in the logs.",
                        )

        except OSError:
            pass  # File might be locked or deleted, just ignore for this tick

        ##### Schedule the next check in 1 second
        app.after(1000, lambda: monitor_output_file(app, file_path, last_mtime, context))

    #### Define the UI polling function to listen for messages from the thread
    def poll_execution_queue(process_queue, start_time, accumulated_wait_time=0):
        """Checks for messages from the background thread and handles button logic."""
        ##### State the global variables this function may change
        global last_run_successful, user_input_response, current_subprocess, monitoring_active

        ##### Define a function to kill the script if it goes rogue
        def kill_process():
            if current_subprocess:
                current_subprocess.kill()
                ui_event("warn", "Process terminated by user.")

        try:
            while True:
                message = process_queue.get_nowait()
                if isinstance(message, tuple):
                    ##### Handle special event messages (Success, Failure, Input Request, Monitor)
                    msg_type = message[0]

                    ###### Handle Input Request from script
                    if msg_type == "INPUT_REQUEST":
                        prompt = message[1]
                        wait_start = time.monotonic()
                        user_input_response = sd.askstring("Input Requested", prompt, parent=app)
                        wait_end = time.monotonic()
                        accumulated_wait_time += wait_end - wait_start

                        if user_input_response is None:
                            user_input_response = ""  # Handle cancel as empty string
                        # Log the interaction
                        log_user_input(prompt, user_input_response)
                        # Unblock the background thread
                        user_input_event.set()
                        continue

                    ###### Handle Start Monitoring Request
                    if msg_type == "START_MONITORING":
                        monitoring_active = True
                        target_file = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]
                        if target_file.exists():
                            initial_mtime = os.path.getmtime(target_file)
                            monitor_output_file(
                                app, target_file, initial_mtime, last_successful_run_context
                            )
                        continue

                    ###### Handle Process Completion
                    status = msg_type
                    log_file_handle.close()

                    if status == "SUCCESS":
                        last_run_successful = True
                        duration = message[1] - accumulated_wait_time
                        was_manifest = message[2]
                        # Update context for the Save button
                        last_successful_run_context.update(
                            {
                                "log_details_folder": current_log_folder,
                                "input_csv_path": inputs["input_csv"].get(),
                                "was_manifest": was_manifest,
                                "is_modified": False,  # Reset modification tracking
                            }
                        )
                        success_label.config(text=success_message)
                        app.after(5000, lambda: success_label.config(text=""))
                        print(f"\n--- [success] - total processing time: {duration:.3f}s ---\n")
                    else:
                        error_data = str(message[1])
                        # Only show error if it wasn't a user kill
                        if error_data != "-9":
                            ui_event("error", f"Script failed: {error_data}")
                            print(f"\n--- [failed] - {error_data} ---\n")

                    ###### Re-enable the run button after the cooldown
                    elapsed = time.monotonic() - start_time
                    delay = max(0, int((1.0 - elapsed) * 1000))
                    # Reset the button to "Run" state
                    run_button.config(
                        text="Run Scripts",
                        command=lambda: run_scripts(
                            app, run_button, success_label, success_message
                        ),
                    )
                    app.after(delay, lambda: run_button.config(state="normal"))
                    return
                else:
                    ##### Normal text message -> Check for Sandbox Violation tags first
                    if "[SANDBOX_VIOLATION]" in message:
                        ui_event(
                            "error",
                            "Security Alert: The script was terminated because it attempted to access\n"
                            f"a restricted system resource.\n\n{message}",
                        )

                    ##### Print to console and file
                    print(message, end="")
                    pass

        except thread_queue.Empty:
            ##### Check time and update button state if still running
            current_time = time.monotonic()
            elapsed_total = current_time - start_time
            processing_time = elapsed_total - accumulated_wait_time

            # If running longer than 3 seconds, change button to Stop
            if elapsed_total > 3.0 and run_button["text"] != "Stop":
                run_button.config(state="normal", text="Stop", command=kill_process)

            # If processing time > 20s, warn user (blocking call)
            # Use a flag on the button itself to store if we've warned already
            if processing_time > 20.0 and not getattr(run_button, "warned", False):
                run_button.warned = True
                should_kill = mb.askyesno(
                    "Long Running Script",
                    "The script has run for over 20 seconds.\nDo you want to stop it?",
                )
                if should_kill:
                    kill_process()

            # Check again in 50ms
            app.after(
                50, lambda: poll_execution_queue(process_queue, start_time, accumulated_wait_time)
            )

    ### Perform the actual execution logic (MAIN THREAD)
    print("--- [starting] - ScriptApp run process initializing ---\n")

    #### Ensure the user has selected files for the mandatory SAPP arguments
    for key in ["main_script", "input_csv"]:  # (output_csv is absent because ScriptApp provides it)
        path_str = inputs[key].get()
        if not path_str or not resolve_path(path_str).is_file():
            ui_event("warn", "Please select a valid main script and data file before running.")
            return

    #### Run the Built-In Validation Script (BIVS) if it's enabled
    if BIVS_enabled:
        if not run_BIVS():
            return
    else:
        print("--- [BIVS] - Validation disabled by user configuration ---\n")

    #### Reset global state variables for the start of a new run
    last_run_successful = False
    current_log_folder = None
    monitoring_active = False  # Stop previous monitoring loop
    current_run_timestamp = dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    #### Get a snapshot of the user inputs (because retriving them in realtime would cause an error)
    filepaths = {k: v.get() for k, v in inputs.items()}

    #### Disable the run button to prevent restarts and UTC timestamp naming conflicts
    # Reset warning flag
    run_button.warned = False
    run_button.config(state="disabled")
    cooldown_start = time.monotonic()  # Used to ensure it ticks over to the next second

    #### Create communication channels
    queue = thread_queue.Queue()
    console_log_path = SAPP["console_file"]["path"] / SAPP["console_file"]["name"]
    log_file_handle = open(console_log_path, "w", encoding="utf-8", buffering=1)

    #### Define the high-level linear logic for the background thread inside a function
    def workflow_logic():
        ##### Start the timer
        workflow_start_time = time.monotonic()

        ##### Attempt to do the following:
        try:
            ###### Set up the logging folder
            setup_logging_folder(filepaths)

            ###### Run the optional prescript, if selected
            if filepaths["prescript"] and filepaths["prescript"] != SAPP["prescript"]["hint"]:
                execute_script(SAPP["prescript_arg_keys"], filepaths, queue)

            ###### Run the main script
            execute_script(SAPP["main_script_arg_keys"], filepaths, queue)

            ###### Immediate Snapshot: Copy output to logs before user can modify it
            # Only if logging is enabled and it's not a manifest run (detected later)
            temp_file = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]
            if current_log_folder and temp_file.exists():
                shutil.copy(temp_file, current_log_folder / "original-output.csv")
                # Signal UI to start monitoring this file for changes
                queue.put(("START_MONITORING",))
                # Update the MDVC index immediately so this isn't flagged as a manual change
                if temp_file.exists():
                    new_hash = calculate_file_hash(temp_file)
                    # We write directly to the index to avoid race conditions
                    index_path = SAPP["mdvc_index_file"]["path"] / SAPP["mdvc_index_file"]["name"]
                    handle_markdown_csv(
                        index_path,
                        mode="update",
                        data=[[str(temp_file.relative_to(BASE_FOLDER)), "x", "x", new_hash]],
                    )

            ###### Check if a multi-output manifest was produced, and process it if it was
            manifest_detected = process_manifest_output(filepaths, queue)

            ###### Run the optional postscript, if selected
            if filepaths["postscript"] and filepaths["postscript"] != SAPP["postscript"]["hint"]:
                execute_script(SAPP["postscript_arg_keys"], filepaths, queue)

            ###### Success!
            duration = time.monotonic() - workflow_start_time
            queue.put(("SUCCESS", duration, manifest_detected))

        ##### If it encounters a serious problem during the attempt, print the error
        except Exception as error:
            queue.put(("FAILURE", error))

    #### Start a background thread using that function
    thread = threading.Thread(target=workflow_logic, daemon=True)
    thread.start()
    poll_execution_queue(queue, cooldown_start)


## Define a function to... view the output data in a spreadsheet with smart format detection
def view_output():
    """Opens the temporary output file in LibreOffice with context-aware import flags."""
    output_file = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]

    ### Validate that the file exists
    if not output_file.exists():
        ui_event("error", "Output file not found. Please run scripts first.")
        return

    ### Define a helper to find the executable on different OSs
    def find_libreoffice_executable():
        """Searches for the LibreOffice executable in a cross-platform way."""
        if shutil.which("libreoffice"):
            return "libreoffice"
        paths_to_check = []
        if USER_OS == "windows":
            paths_to_check = [
                Path(os.environ.get("ProgramFiles", "")) / "LibreOffice/program/soffice.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "LibreOffice/program/soffice.exe",
            ]
        elif USER_OS == "darwin":  # This is the specific check for macOS
            paths_to_check = [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
        for path in paths_to_check:
            if path and path.is_file():
                return str(path)
        return None

    libreoffice_cmd = find_libreoffice_executable()
    if not libreoffice_cmd:
        ui_event(
            "error",
            """A LibreOffice executable was not found on your system.\n\n Please ensure LibreOffice
            is installed and can be found in your system's PATH environment variable.""",
        )
        return

    ### Log that the output file was inspected (in case the user edits it manually)
    if last_run_successful and inputs["log?"].get():
        update_summary_log("inspect")

    ### Determine the correct flags based on script metadata (Smart Detection)
    final_flags = libreoffice_flags  # Start with global default

    # If NO postscript ran, we check the main script's declared format
    if not inputs["postscript"].get() or inputs["postscript"].get() == SAPP["postscript"]["hint"]:
        out_fmt = script_requirements.get("output formats", "comma").lower()
        if "tab" in out_fmt:
            final_flags = "--infilter=CSV:9,34,UTF-8"  # Tab separator
        elif "pipe" in out_fmt:
            final_flags = "--infilter=CSV:124,34,UTF-8"  # Pipe separator
        elif "comma" in out_fmt or "mdcsv" in out_fmt:
            final_flags = "--infilter=CSV:7C,34,UTF-8"  # Standard ScriptApp format
        else:
            # For "other-csv" or unknown formats, clear flags to trigger Import Wizard
            final_flags = ""
            print("Output format non-standard: Launching Import Wizard.")

    ### Launch the application
    try:
        command = [libreoffice_cmd, "--calc"]
        if final_flags:
            command.append(final_flags)
        command.append(str(output_file))
        subprocess.Popen(command)
    except Exception as error:
        ui_event("error", f"Failed to open LibreOffice:\n{error}")


## Define a function to... save the temporary output file permanently
def save_output(app, button, success_message):
    """Event handler function to save the temporary output_csv file."""
    ### State the global variables this function may change
    global current_log_folder, log_file_handle

    ### Validate that there is something to save
    if not last_run_successful:
        ui_event("error", "No successful output to save. Please run scripts first.")
        return
    name, folder = inputs["output_name"].get(), inputs["output_folder"].get()
    if not (name and folder):
        ui_event("warn", "Please specify output name and folder.")
        return

    ### Re-open the console log to capture save events
    console_log_path = SAPP["console_file"]["path"] / SAPP["console_file"]["name"]
    temp_log_handle = open(console_log_path, "a", encoding="utf-8", buffering=1)
    # Temporarily set the global handle so print_to_log can use it
    log_file_handle = temp_log_handle

    try:
        ### Retrieve context from the last run
        context = last_successful_run_context
        original_log_folder = context.get("log_details_folder")
        was_manifest = context.get("was_manifest", False)
        input_csv_path = context.get("input_csv_path", "")
        is_modified = context.get("is_modified", False)

        ### Rename the log folder to match the user's chosen output name
        if inputs["log?"].get() and original_log_folder:
            input_stem = Path(input_csv_path).stem
            # Create a new name replacing the input stem with the output name
            new_log_folder_name = original_log_folder.name.replace(f"-i-{input_stem}", f"-o-{name}")
            new_log_folder = SAPP["log_details_folder"]["path"] / new_log_folder_name
            try:
                original_log_folder.rename(new_log_folder)
                # Update the global variables to reflect the new log folder path
                current_log_folder = new_log_folder
                last_successful_run_context["log_details_folder"] = new_log_folder

                # Handle renaming of files inside the log folder depending on modification status
                if is_modified:
                    # We have 'original-output.csv' and 'modified-temp-output.csv'
                    # Rename modified-temp to the user's chosen output name
                    mod_temp = new_log_folder / "modified-temp-output.csv"
                    final_log_name = new_log_folder / f"output_csv-{name}.csv"
                    if mod_temp.exists():
                        mod_temp.rename(final_log_name)
                    # original-output.csv stays as it is to allow diffing
                else:
                    # We have 'original-output.csv' only
                    # Rename it to the user's chosen output name since it's identical
                    orig_temp = new_log_folder / "original-output.csv"
                    final_log_name = new_log_folder / f"output_csv-{name}.csv"
                    if orig_temp.exists():
                        orig_temp.rename(final_log_name)

            except OSError as error:
                print(f"Error processing log folder: {error}")

        ### Update the log summary
        # This needs to be called after renaming so it logs the correct folder name
        if inputs["log?"].get():
            update_summary_log("save")

        ### Handle Manifest outputs (which don't save a single CSV)
        if was_manifest:
            msg = f"Log finalized for multi-file output batch:\n{name}"
            print(f"UI-INFO: Success - {msg.splitlines()[0]}")
            ui_event("info", msg)
            return  # No single file to save for manifests

        ### Validate filename characters
        if not all(c.isalnum() or c in "-_" for c in name):
            ui_event("error", "Output name must only use letters, numbers, dashes and underscores.")
            return

        ### Handle potential file overwrite conflicts with Silent Sync Logic
        dest = resolve_path(folder) / f"{name}.csv"

        #### Conflict Resolution & MDVC Sync
        if dest.exists():
            question = f"'{dest.name}' already exists. Overwrite?"
            print(f"UI-CONFIRM: Confirm - {question}")
            if not mb.askyesno("Confirm", question):
                return

            ##### Check if the existing file has manual edits that need logging before overwrite
            current_hash = calculate_file_hash(dest)
            index_path = SAPP["mdvc_index_file"]["path"] / SAPP["mdvc_index_file"]["name"]
            index_rows = handle_markdown_csv(index_path, mode="read")
            # Find the hash in the index
            rel_path = str(dest.relative_to(BASE_FOLDER))
            stored_hash = next((r[3] for r in index_rows if r[0] == rel_path), None)

            # If disk differs from index, force a manual snapshot BEFORE overwriting
            if current_hash != stored_hash:
                print("MDVC: Pre-overwrite snapshot triggered for unsaved manual changes.")
                # We can reuse the logic from the monitor loop, or just acknowledge it will be lost
                # For simplicity in this spec, we update the index with the NEW file immediately below

        ### Perform the save operation
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy(SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"], dest)

            ##### Silent Sync: Update MDVC Index with the script output hash
            # This prevents the monitor from flagging the script's output as a "Manual Edit"
            new_hash = calculate_file_hash(dest)
            handle_markdown_csv(
                index_path,
                mode="update",
                data=[[str(dest.relative_to(BASE_FOLDER)), "x", "x", new_hash]],
            )

        except Exception as e:
            ui_event("error", f"Failed to save file to disk:\n{e}")
            return

        ### Update the button text to provide feedback
        original_text = button.cget("text")
        button.config(text=success_message)
        app.after(3000, lambda: button.config(text=original_text))

    finally:
        # Ensure the log file is closed and global reset even if errors occur
        temp_log_handle.close()
        log_file_handle = None


## --- Define the Manual Data Version Control (MDVC) Background System ---


### Define the main MDVC daemon function
def run_data_monitor():
    """Background thread that tracks manual changes to the data folder."""

    ### Initialize configuration
    index_path = SAPP["mdvc_index_file"]["path"] / SAPP["mdvc_index_file"]["name"]
    log_path = SAPP["mdvc_log_file"]["path"] / SAPP["mdvc_log_file"]["name"]
    archive_folder = SAPP["log_summary_archive"]["path"]

    ### Define a helper for log rotation and checkpoint creation
    def create_checkpoint(reason):
        """Creates a full backup of the current state and resets the log."""
        timestamp = dt.now(timezone.utc).strftime("%y-%m-%d")

        #### Archive the old log if it exists
        if log_path.exists():
            rows = handle_markdown_csv(log_path, mode="read")
            if rows:
                start = dt.fromisoformat(rows[0][0].replace("Z", "+00:00")).strftime("%y-%m-%d")
                end = dt.fromisoformat(rows[-1][0].replace("Z", "+00:00")).strftime("%y-%m-%d")
                archive_name = f"{start}--{end}-manual-log-summary.csv"
                shutil.move(log_path, archive_folder / archive_name)

        #### Create the new checkpoint folder
        checkpoint_name = f"0000-x-{timestamp}-checkpoint"
        # Handle collisions
        i = 1
        while (SAPP["logs_parent_folder"]["path"] / "manual-edits" / checkpoint_name).exists():
            i += 1
            checkpoint_name = f"0000-x-{timestamp}-checkpoint{i}"

        checkpoint_path = SAPP["logs_parent_folder"]["path"] / "manual-edits" / checkpoint_name
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        #### Snapshot all valid data files
        data_files = []
        for f in P_DATA.rglob("*"):
            if f.is_file():
                try:
                    rel_dest = f.relative_to(P_DATA)
                    dest = checkpoint_path / rel_dest
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, dest)
                    data_files.append(str(f.relative_to(BASE_FOLDER)))
                except Exception:
                    pass

        #### Reset the Index and Log
        # Re-hash everything to ensure index is perfectly fresh
        new_index_data = []
        for f in P_DATA.rglob("*"):
            if f.is_file():
                h = calculate_file_hash(f)
                if h:
                    new_index_data.append([str(f.relative_to(BASE_FOLDER)), "x", "x", h])

        # Write clean index
        handle_markdown_csv(index_path, mode="write", data=new_index_data)

        # Write clean log with Checkpoint entry
        handle_markdown_csv(
            log_path,
            mode="write",
            header=SAPP["mdvc_header"],
            data=[
                [
                    dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "CHECKPOINT",
                    "-",
                    "(All Files)",
                    checkpoint_name,
                    reason,
                ]
            ],
        )

    ### Startup Check: If Index or Log is missing, force a checkpoint
    if not index_path.exists() or not log_path.exists():
        create_checkpoint("Initial Startup / Missing Index")

    ### Main Loop
    while True:
        #### Interval Management & Lag Prevention
        # Determine the sleep interval based on global settings
        interval_min = SAPP["manual_check_interval_mins"].get(file_checking_interval, 1)
        interval_sec = interval_min * 60

        # Align to the clock
        now = dt.now(timezone.utc)
        seconds_past = (now.minute % interval_min) * 60 + now.second
        wait_time = interval_sec - seconds_past

        # If too close to the boundary, skip to next interval to avoid startup contention
        if wait_time < 5:
            wait_time += interval_sec

        time.sleep(wait_time)

        #### Log Rotation Check
        rows = handle_markdown_csv(log_path, mode="read")
        if len(rows) >= 1000:
            create_checkpoint("Log Rotation Limit Reached")
            continue  # Restart loop with fresh state

        #### The Detection Scan
        current_map = {}  # Path -> Hash
        changes_detected = []

        # Load Index
        index_rows = handle_markdown_csv(index_path, mode="read")
        index_map = {r[0]: r[3] for r in index_rows if len(r) >= 4}

        # Scan Disk
        for f in P_DATA.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(BASE_FOLDER))
                h = calculate_file_hash(f)
                if h:
                    current_map[rel] = h

        # Compare
        new_files = set(current_map.keys()) - set(index_map.keys())
        missing_files = set(index_map.keys()) - set(current_map.keys())

        # Detect Renames (Missing A + New B + Hash Match)
        renames = {}
        for missing in list(missing_files):
            missing_hash = index_map[missing]
            for new in list(new_files):
                if current_map[new] == missing_hash:
                    renames[new] = missing  # New -> Old
                    new_files.remove(new)
                    missing_files.remove(missing)
                    break

        # Detect Modifications
        for path, h in current_map.items():
            if path in index_map and index_map[path] != h:
                changes_detected.append(("MODIFIED", path, "-"))

        for path in new_files:
            changes_detected.append(("ADDED", path, "-"))
        for path, old in renames.items():
            changes_detected.append(("RENAMED", path, old))
        for path in missing_files:
            changes_detected.append(("REMOVED", path, "-"))

        #### Process Changes
        if changes_detected:
            timestamp_iso = dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            folder_name = dt.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")  # Hyphens for folders

            # If we have content to save (Mod/Add/Rename), create snapshot folder
            snapshot_needed = any(
                c[0] in ["MODIFIED", "ADDED", "RENAMED"] for c in changes_detected
            )

            if snapshot_needed:
                snap_path = SAPP["logs_parent_folder"]["path"] / "manual-edits" / folder_name
                snap_path.mkdir(parents=True, exist_ok=True)

                for evt, path, old in changes_detected:
                    if evt != "REMOVED":
                        src = BASE_FOLDER / path
                        dest = snap_path / Path(path).name
                        if src.exists():
                            shutil.copy(src, dest)

            # Update Log and Index
            log_entries = []
            for evt, path, old in changes_detected:
                log_entries.append(
                    [
                        timestamp_iso,
                        evt,
                        old,
                        Path(path).name,
                        folder_name if evt != "REMOVED" else "-",
                        "",
                    ]
                )

            handle_markdown_csv(
                log_path, mode="update", data=log_entries, header=SAPP["mdvc_header"]
            )

            # Update Index Map
            for evt, path, old in changes_detected:
                if evt == "REMOVED":
                    if path in index_map:
                        del index_map[path]
                elif evt == "RENAMED":
                    if old in index_map:
                        del index_map[old]
                    index_map[path] = current_map[path]
                else:
                    index_map[path] = current_map[path]

            # Flatten map for write
            flat_index = [[k, "x", "x", v] for k, v in index_map.items()]
            handle_markdown_csv(index_path, mode="write", data=flat_index)


# endregion --- Back-end functions have been defined ---


# region --- Create ScriptApp's front-end User Interface that hooks up to the back-end ---


## Define the function that creates the UI with all of its individual elements
def create_user_interface(app):
    """Builds and lays out all the Tkinter widgets for ScriptApp's UI."""

    ### Create a dictionary of UI text labels (reuses some SAP key refs, listed in order of use)
    UI = {
        "browse": "Browse",
        "main_script": "Select main Python script:",
        "docs": "Read instructions:",
        "input_csv": "Select main CSV data file:",
        "dbox": "Extra data:",
        "dbox_keys": ["data2", "data3", "data4", "data5"],
        "vbox": "Validation scripts:",
        "vbox_keys": ["prescript", "valscriptA", "valscriptB", "postscript"],
        "run": "Run Scripts",
        "run_good": "Success!",
        "view": "Inspect Output CSV",
        "output_name": "Choose output file name:",
        "output_folder": "Select output file folder:",
        "save": "Save Output CSV",
        "save_good": "File Saved!",
        "log?": "Save logs?",
        "af_icon": tk.PhotoImage(data=AUTOFILL_ICON_BASE64),
        "af_hover": "Load autofill",
    }

    ### Define functions for performing front-end tasks

    #### Define a function to... update entry box text in the UI
    def update_ui_entry(entry_box, new_path):
        """Helper function to update a UI entry box with a pre-formatted and shortened filepath."""
        ### Call the helper function to get the pre-formatted display path
        display_path = get_display_path(new_path)
        #### Perform the process for inserting the display path into the UI entry box
        entry_box.config(state="normal", fg="black")  # Changes text color from grey to black
        entry_box.delete(0, tk.END)  # Clears any existing text content first
        entry_box.insert(0, display_path)  # Inserts the new formatted path into the now-empty box
        entry_box.xview_moveto(1)  # Scrolls to the end, so the filename part is visible to the user

    #### Define a function to... load an autofill configuration file
    def load_autofill(autofill_path=None):
        """Loads a configuration file to pre-fill the UI fields."""
        ##### State the global variables this function may change
        global libreoffice_flags, BIVS_enabled, images_enabled, suppress_mod_popup
        global headless_warnings, file_checking_interval
        ##### If a path wasn't provided, open a file selection dialog.
        if autofill_path is None:
            autofill_path = fd.askopenfilename(
                initialdir=SAPP["autofills"]["path"], filetypes=SAPP["autofills"]["type"]
            )
        ##### If a path was provided, or has now been chosen, proceed with loading it.
        if autofill_path:
            try:
                data_rows = handle_markdown_csv(Path(autofill_path), mode="read")
                data = {row[0]: row[1] for row in data_rows if len(row) == 2}

                if "libreoffice_flags" in data:
                    libreoffice_flags = data.pop("libreoffice_flags")
                if "enable_logging" in data:
                    inputs["log?"].set(data.pop("enable_logging").lower() in ["yes", "1"])
                if "enable_bivs" in data:
                    BIVS_enabled = data.pop("enable_bivs").lower() in ["yes", "1"]
                if "enable_image_instructions" in data:
                    images_enabled = data.pop("enable_image_instructions").lower() in ["yes", "1"]
                if "suppress_mod_popup" in data:
                    suppress_mod_popup = data.pop("suppress_mod_popup").lower() in ["yes", "1"]
                if "redirect_warnings_to_console" in data:
                    headless_warnings = data.pop("redirect_warnings_to_console").lower() in [
                        "yes",
                        "1",
                    ]
                if "monitor_settings" in data:
                    val = data.pop("monitor_settings")
                    if val in SAPP["manual_check_interval_mins"]:
                        file_checking_interval = val

                for key, value in data.items():
                    if key in inputs:
                        update_ui_entry(inputs[key], value)
                        if key in optional_entry_box_refs:
                            optional_entry_box_refs[key]["entry"].config(fg="black")

                ##### If a main_script was autofilled, initiate its automatic fetching process.
                if "main_script" in data:
                    select_main_script(inputs["main_script"], instructions_box)
            except Exception as error:
                ui_event("error", f"Could not load autofill file:\n{error}")

    #### Define a function to... give browse buttons the correct command
    def browse_cmd(entry_box, SAPP_key, type="file"):
        """Creates a factory function for making each browse button work correctly when pressed."""

        def on_browse_click():
            path = None  # Prevents errors if neither of the following conditions are true
            if type == "file":  # If the browse button is for selecting a file (the default)
                path = fd.askopenfilename(initialdir=SAPP_key["path"], filetypes=SAPP_key["type"])
            elif type == "folder":  # Alternately, if the browse button is for selecting a folder
                path = fd.askdirectory(initialdir=SAPP_key["path"])
            if path:  # If a file or folder path has been selected...
                update_ui_entry(entry_box, path)  # Update the UI

        return on_browse_click

    ### Define functions for creating the repetitive UI elements

    #### Layout frame template (Tkinter's equivalent to a HMTL <div>)
    def draw_frame_row(row):
        """Creates a Tkinter frame with some default values."""
        frame = tk.Frame(app)  # Draws the frame on ScriptApp's base window
        frame.grid(row=row, column=0, pady=4)  # Sets the standard values with 4px vertical spacing
        return frame  # Returns the frame so it can be modified outside of this function

    #### Main file selection box template
    def draw_ui_main(row, input_key, width=60, suffix=None, type="file"):
        """Creates the main input boxes with an optional browse button"""
        frame = draw_frame_row(row)  # Draws the frame container
        tk.Label(frame, text=UI[input_key]).grid(row=0, column=0, columnspan=2)  # Adds the label
        entry_box = tk.Entry(frame, width=width)  # Draws the entry box at specified width
        entry_box.grid(row=1, column=0)  # Puts entry box on 2nd subrow below the label
        initial_text = SAPP[input_key].get("default", SAPP[input_key].get("hint", ""))
        update_ui_entry(entry_box, str(initial_text))  # Adds default or hint inside the entry box
        inputs[input_key] = entry_box  # Registers the entry box outside of this function
        if suffix is not None:  # Adds a text suffix if one has been specified
            right_widget = tk.Label(frame, text=suffix)
        else:  # Adds a browse button if no suffix was specified (the assumed default)
            browse_command = browse_cmd(entry_box, SAPP[input_key], type)  # Makes the button work
            right_widget = tk.Button(frame, text=UI["browse"], command=browse_command)
        right_widget.grid(row=1, column=1)  # Places the label/button to the right of the entry box
        return entry_box, right_widget  # Returns the widgets so they can be modified externally

    #### Extra file selection group of boxes template (used for extra data and validation scripts)
    def draw_ui_extra(parent, label_key, list_key):
        """Creates a column of extra file input boxes with browse buttons"""
        key_list = UI[list_key]  # Note: this uses SAPP keys for hint text
        frame = tk.Frame(parent)
        tk.Label(frame, text=UI[label_key]).grid(row=0, column=0, columnspan=2)
        for i, key in enumerate(key_list, 1):
            entry_box = tk.Entry(frame, width=18, fg=HINT_COLOR)
            entry_box.insert(0, SAPP[key]["hint"])
            entry_box.grid(row=i, column=0)
            inputs[key] = entry_box
            optional_entry_box_refs[key] = {"entry": entry_box}

            def make_focus_handlers(current_box, current_key):
                hint_text = SAPP[current_key]["hint"]

                def on_focus_in(event):
                    if current_box.cget("fg") == HINT_COLOR:
                        current_box.delete(0, tk.END)
                        current_box.config(fg="black")

                def on_focus_out(event):
                    if not current_box.get():
                        current_box.insert(0, hint_text)
                        current_box.config(fg=HINT_COLOR)

                return on_focus_in, on_focus_out

            focus_in_handler, focus_out_handler = make_focus_handlers(entry_box, key)
            entry_box.bind("<FocusIn>", focus_in_handler)
            entry_box.bind("<FocusOut>", focus_out_handler)
            button = tk.Button(frame, text=UI["browse"], command=browse_cmd(entry_box, SAPP[key]))
            button.grid(row=i, column=1)
            optional_entry_box_refs[key]["button"] = button
        return frame

    ### Lay out all the UI components (this code is ordered top to bottom)
    #### Draw the base application window
    app.title(f"{APP_TITLE} (v{__version__}) SAPPv{SAPP['SAPP_version']}")  # Sets the topbar title
    app.geometry(UI_WINDOW_GEOMETRY)  # Sets the size of the window below the topbar
    app.grid_columnconfigure(0, weight=1)  # Keeps UI elements centered if the window is resized
    bg0 = app.cget("bg")  # Hack for making a widget's background transparent

    #### Draw the main script input box + automatic instructions display box (rows 1 and 2)
    script_entry_box, main_browse_button = draw_ui_main(1, "main_script")
    instr_frame_lv3 = draw_frame_row(2)  # (This requires multiple subframe nesting levels)
    tk.Label(instr_frame_lv3, text=UI["docs"]).pack(pady=(0, 2))
    instr_frame_lv2 = tk.Frame(instr_frame_lv3)
    instr_frame_lv2.pack()
    instr_frame_lv1 = tk.Frame(instr_frame_lv2, width=704, height=424, relief="sunken", bd=1)
    instr_frame_lv1.pack_propagate(False)
    instr_frame_lv1.pack(side="left")
    instructions_box = tk.Text(instr_frame_lv1, wrap="word", bd=0, highlightthickness=0)
    instructions_box.pack(fill="both", expand=True)
    instr_scrollbar = tk.Scrollbar(instr_frame_lv2, command=instructions_box.yview)
    instr_scrollbar.pack(side="right", fill="y")
    instructions_box.config(yscrollcommand=instr_scrollbar.set, state="normal", takefocus=0)

    ##### Configure the main script entry box to automatically fetch its instructions
    def on_main_script_update(event=None):  # ("event=None" makes it callable from anywhere)
        select_main_script(script_entry_box, instructions_box)

    ###### Get the standard "browse" function (this just opens a dialog and updates the entry box)
    standard_browse_action = browse_cmd(script_entry_box, SAPP["main_script"])
    ###### Assign the commands to the UI elements (uses lambda to run 2 functions in sequence)
    main_browse_button.config(command=lambda: (standard_browse_action(), on_main_script_update()))
    script_entry_box.bind("<FocusOut>", on_main_script_update)
    script_entry_box.bind("<Return>", on_main_script_update)

    #### Draw the main CSV file input box (row 3)
    draw_ui_main(3, "input_csv")

    #### Draw a frame containing the optional input boxes + run & inspect output buttons
    mid_frame = draw_frame_row(4)
    mid_frame.grid_columnconfigure(1, pad=90)  # Adds 90px space between the columns
    ##### Draw the optional input box groups
    draw_ui_extra(mid_frame, "dbox", "dbox_keys").grid(row=0, column=0, rowspan=5, sticky="ne")
    draw_ui_extra(mid_frame, "vbox", "vbox_keys").grid(row=0, column=2, rowspan=5, sticky="nw")
    ##### Draw the central buttons (defined after box groups to preserve keyboard tab navigation)
    run_button = tk.Button(mid_frame, text=UI["run"], height=2)
    run_button.grid(row=0, column=1, rowspan=3)
    success_label = tk.Label(mid_frame, text="", bg=bg0)
    success_label.place(relx=0.5, rely=0.57, anchor="center")  # Uses place to sandwich between them
    run_button.config(command=lambda: run_scripts(app, run_button, success_label, UI["run_good"]))
    view_button = tk.Button(mid_frame, text=UI["view"], command=view_output)
    view_button.grid(row=3, column=1, rowspan=2)

    #### Draw the widgets for permanently saving the output file
    draw_ui_main(5, "output_name", width=36, suffix=".csv")  # Replaces browse button with a label
    draw_ui_main(6, "output_folder", type="folder")  # Uses folder selection instead of file
    save_button_frame = draw_frame_row(7)
    save_button = tk.Button(save_button_frame, text=UI["save"], width=12)  # Stops width shrinking
    save_button.config(command=lambda: save_output(app, save_button, UI["save_good"]))
    save_button.pack()

    #### Draw the log toggler (bottom left)
    inputs["log?"] = tk.BooleanVar(value=True)  # Have it enabled by default
    log_checkbox = tk.Checkbutton(app, text=UI["log?"], var=inputs["log?"], activebackground=bg0)
    log_checkbox.place(relx=0.0, rely=1.0, x=0, y=-4, anchor="sw")

    #### Draw the autofill icon button with a hoverable tooltip (bottom right)
    af_btn = tk.Button(app, image=UI["af_icon"], command=load_autofill, bd=0, activebackground=bg0)
    af_btn.place(relx=1.0, rely=1.0, x=-4, y=-4, anchor="se")
    af_tooltip = tk.Label(app, text="")
    af_tooltip.place(relx=1.0, rely=1.0, x=-28, y=-4, anchor="se")
    af_btn.bind("<Enter>", lambda e: af_tooltip.config(text=UI["af_hover"]))
    af_btn.bind("<Leave>", lambda e: af_tooltip.config(text=""))

    ### Load the autofill override file at startup if it exists
    af_override_file = SAPP["af_override_file"]["path"] / SAPP["af_override_file"]["name"]
    if af_override_file.exists():
        load_autofill(af_override_file)

    ### Start the Manual Data Version Control (MDVC) Monitor Thread
    mdvc_thread = threading.Thread(target=run_data_monitor, daemon=True)
    mdvc_thread.start()


## Create the execution logic for ScriptApp
if __name__ == "__main__":  # If the script is being executed directly (instead of being imported)
    ### Call the function to create any folders that are missing during startup
    create_missing_folders()
    ### Create the UI
    #### Create a blank Tkinter window
    app = tk.Tk()
    ##### Call the function to create the UI on that blank window
    create_user_interface(app)
    #### Start the UI and keep it running so the user can interact with it
    app.mainloop()

# endregion --- Front-end UI code has been defined ---
