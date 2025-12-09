#!/usr/bin/env python3
# ^ "Shebang" first line that makes this code executable as a program
"""
Explicitly Stated Intentions:
1. Act as a user-friendly wrapper for running Intentionalist data processing scripts.
2. Demonstrate a minimal implementation of the ScriptApp Processing Protocol (SAPP) that...
    2.1. Has enough features to be useful for real admin work, not just as a toy demonstration.
    2.2. Is as self-contained as possible.
    2.3. Has short, simple and well-documented code, so that inexperienced coders (who might not
    have read the source code of *any* other program) can understand exactly how it works and
    start writing their own scripts ASAP.
"""  # (Python's standard "module docstring", used to briefly explain what the code in a file does)

# region --- Perform the initial setup for the script (imports, constants, variables, ect.) ---

## Define special dunder (double underscore) variables
__author__ = "bendini"  # The Github username of this script's owner/maintainer
__version__ = "0.2.011"  # (This version number is also displayed in the UI for screenshot purposes)

## Import relevant modules from the Python Standard Library (reason for use given in side comments)
import ast  # Used for safely parsing Python code to extract docstrings
import os  # Used for more robust cross platform support
import platform  # Used for detecting the user's OS
import shlex  # Used to print a safe command line argument for use outside ScriptApp
import shutil  # Used to copy and move files
import subprocess  # Used to execute the user's Python scripts
import time  # Used to precisely measure script execution time
from datetime import datetime, timezone  # Used for UTC timestamping
from pathlib import Path  # Used for better file path handling

## Import relevant 3rd party libraries (these must be pre-installed before running)
try:  # Try to do the following...
    import tkinter as tk  # Used to create the UI (not 3rd party, but it doesn't come with Ubuntu)
    from tkinter import filedialog as fd, messagebox
except ImportError:  # Do this if there's a problem during the "try:" code
    ### If importing fails, print a console message (using input() so it won't close instantly)
    input("ERROR: Tkinter must be installed first for ScriptApp to work.\n\nPress Enter to exit...")

## Define global constants (can be used anywhere in the code, **won't** be modified by the code)
### Set folder locations
BASE_FOLDER = Path(__file__).parent.resolve()  # Sets the base folder relative to this file's path
P_DATA = BASE_FOLDER / "data"  # Set the path for... CSV data
P_AGN_DATA = P_DATA / "agnostic-data"  # ...data with other file extensions
P_SCRIPTS = BASE_FOLDER / "scripts"  # ...Python scripts
P_VALIDS = P_SCRIPTS / "validation"  # ...Python validation scripts
P_MODULES = P_SCRIPTS / "py-modules"  # ...Python modules written for our ecosystem
P_RUST = P_SCRIPTS / "rust-code"  # ...compiled Rust extensions & source code
P_TOOLS = BASE_FOLDER / "tools"  # ...tools that enhance ScriptApp
P_UV = P_TOOLS / "uv-versions"  # ...non-system versions of the uv virtual environment manager
P_AUTOFILLS = BASE_FOLDER / "autofills"  # ...auto-filling config data
P_LOGS = BASE_FOLDER / "logs"  # ...logging data
P_TEMP = P_LOGS / "old-tempfiles"  # ...old console logs and output.csv files

### Set the names of some specific files (all of these files will be in BASE_FOLDER)
TEMP_OUTPUT_NAME = "sa-last-output.csv"  # Used as the default CSV output file
TEMP_CONSOLE_NAME = "sa-last-console-log.txt"  # Used to save the console output to text
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
    "main_script": {"path": P_SCRIPTS,   "type": PY_SCRIPT, "hint": ""},  # sys.argv[0]
    "input_csv":   {"path": P_DATA,      "type": CSV_DATA,  "hint": ""},  # sys.argv[1]
    "output_csv":  {"path": BASE_FOLDER, "name": TEMP_OUTPUT_NAME},       # sys.argv[2]
    #### Optional extended protocol arguments
    "data2": {"path": P_DATA,     "type": CSV_DATA, "hint": "data2"},              # sys.argv[3]
    "data3": {"path": P_DATA,     "type": CSV_DATA, "hint": "data3"},              # sys.argv[4]
    "data4": {"path": P_DATA,     "type": CSV_DATA, "hint": "data4"},              # sys.argv[5]
    "data5": {"path": P_AGN_DATA, "type": AGN_DATA, "hint": "data5 (all types)"},  # sys.argv[6]
    "valscriptA": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "valscriptA" },  # sys.argv[7]
    "valscriptB": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "valscriptB" },  # sys.argv[8]
    #### ScriptApp's enhanced feature set
    "SAPP_version": "0.3",  # (Increases if a breaking change is made to the protocol)
    "python_version": "3.12.3",  # The Python version that scripts should expect by default
    ##### ScriptApp's outer validation wrapper
    "prescript":  {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "prescript" },  # Runs before main
    "postscript": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "postscript"},  # Runs after main
    "output_name":   {"default": ""},  # Used to rename output_csv if it was successful
    "output_folder": {"path": P_DATA, "default": P_DATA},  # The final output_csv save location
    "metadata": ["SAPP version", "Python version", "extras disabled", "run with uv?", "uv version",
                 "uv flags"],  # Optional metadata that ScriptApp can make use of
    ##### The ordered sequence of arguments that will be passed for each script type
    "optional_arg_keys":    ["data2", "data3", "data4", "data5", "valscriptA", "valscriptB"],
    "main_script_arg_keys": ["main_script", "input_csv", "output_csv", "optional_arg_keys"],
    "prescript_arg_keys":   ["prescript", "main_script_arg_keys", "postscript"],
    "postscript_arg_keys":  ["postscript", "output_csv", "main_script"],
    ##### Built-in Python virtual environment management
    "python_uv": {"standard_version": "0.9.16", "path": P_UV},
    "uv_allowed_flags": ["--python", "--preview", "--offline", "--reinstall", "--verbose"],
    ##### Automatic actions taken on behalf of the user (fetching, form-filling, logging, creating)
    "script_instructions": {"format_priority": [".md", "docstring"]},  # Displays documentation
    "autofills": {"path": P_AUTOFILLS, "type": CSV_AUTOFILL},  # Autofill folder for manual loading
    "af_override_file": {"path": BASE_FOLDER, "name": AF_OVERRIDE_NAME},  # Autofill on startup file
    "console_file": {"path": BASE_FOLDER, "name": TEMP_CONSOLE_NAME},  # Captures all console output
    "last_outputs_archive": {"path": P_TEMP},  # Where the old logs and output CSVs are saved
    "folders": [P_DATA, P_AGN_DATA, P_SCRIPTS, P_VALIDS, P_MODULES, P_RUST, P_TOOLS, P_UV,
                P_AUTOFILLS, P_TEMP]  # The list of folders to create inside the BASE_FOLDER
}  # fmt: skip
#     ^ "# fmt: skip" tells Ruff not to apply its formatting rules to this dictionary

### Define some constants for the UI (a UI label dictionary is also defined later)
APP_TITLE = "ScriptApp"  # Name of the application that's displayed in the UI
UI_WINDOW_GEOMETRY = "718x921"  # Makes bordered screenshots exactly 720px wide by 960px tall
HINT_COLOR = "#505050"  # HEX color code for placeholder text hints (medium-dark grey)
AUTOFILL_ICON_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAQAAAD8x0bcAAAAAXNSR0IB2cksfwAAAARnQU1BAA
Cxjwv8YQUAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAKtJREFUKM+NksERBSEIQ5+OhWFlLp
VBZ/7DoovzL3JxjDHRQBmkelhb5fngcpAmigPCoHxwA0AAB8BjHRl/SRZXPFHn8nrtDOhJjaRiQC9DsOz/R570Ml6dRVjGfRMNKp
qODKVQ0IQIWnE6goTRE3kRiNDxykVVBIuv+6HkEYUhVw+/jOAizAZ0ZjTBt7EhX1tavOBVmUhMgVBCbU+BHyb7cOHtCEQZMSSa4R
9ADkVgLJEX4gAAAABJRU5ErkJggg=="""  # Embedded .png data for af_icon so ScriptApp can stay as 1 file

## Define global state variables (can be used anywhere in the code, **can** be modified by the code)
inputs = {}  # Used to store inputs made into the UI by the user
last_run_successful = False  # Used to check if the last run was successfully completed
log_file = None  # Holds the reference to the open console log file
optional_entry_box_refs = {}  # Used for toggling optional input boxes
metadata = {}  # Used to store the metadata settings from the currently selected script


# endregion --- Initial setup completed ---

# region --- Define functions for ScriptApp's back-end processing ---

## --- Define back-end "helper functions" that will be used for multiple things ---


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
    ##### ...Or if it's a short relative path, join it to the base folder path, then resolve it.
    else:
        return (BASE_FOLDER / path).resolve()


### Define a function to... format a filepath for displaying to the user
def get_display_path(path_string, is_folder=False):
    """Creates a shortened (but still valid) filepath relative to the base folder."""
    #### Handle empty input boxes by returning them as an empty string
    if not path_string:
        return ""
    #### Get the full, absolute filepath
    absolute_path = resolve_path(path_string)
    #### Handle invalid or non-path strings by returning them unchanged
    if not absolute_path:
        return str(path_string)
    #### Try to make the path relative to the base folder
    try:
        display_path = str(absolute_path.relative_to(BASE_FOLDER))
    ##### ...but fallback to using the absolute path if this fails
    except ValueError:
        display_path = str(absolute_path)
    #### Add a trailing slash if the path is (or will be) a directory (folder) instead of a file
    if (is_folder or absolute_path.is_dir()) and not display_path.endswith("/"):
        display_path += "/"
    #### Return the final formatted string
    return display_path


### Define a function to... log a copy of all print statements to a file when it's open
def print(*args, **kwargs):
    """Enhances Python's default print() function so that it saves them to a log file if open."""
    #### Try to write the print message to the log file, if the log file exists and it's open
    try:
        if log_file and not log_file.closed:
            log_file.write(" ".join(map(str, args)) + kwargs.get("end", "\n"))
    ##### ...And if this try code fails, do nothing so that ScriptApp won't crash
    except Exception:
        pass
    #### Call Python's normal print function afterwards
    __builtins__.print(*args, **kwargs)


### Define a function to... alert the user when a problem occurs
def ui_event(message_type, message):
    """Handles showing errors and warnings in the UI, and also prints a copy to the console."""
    ### Strip any non-explicit linebreaks and unwanted whitespace from the message content
    message = "\n".join([line.strip() for line in message.strip().splitlines()])
    ### Handle each type of message appropriately
    if message_type == "error":
        print(f"UI Message - Error: {message}")
        messagebox.showerror("Error", message, parent=scriptapp)
    elif message_type == "warn":
        print(f"UI Message - Warning: {message}")
        messagebox.showwarning("Warning", message, parent=scriptapp)
    #### If the type wasn't specified or wasn't a valid type, print an error to the console
    else:
        print("ui_event function error: invalid message type specified")


### Define a function to... read our special Markdown table CSV format
def read_markdown_csv(filepath=None, content=None):
    """Safely reads a Markdown-formatted CSV file."""
    #### If content isn't provided as raw data, read it from the file provided
    if content is None and filepath:
        content = Path(filepath).read_text(encoding="utf-8")
    #### If we still don't have content (e.g. filepath was None), return an empty list
    if not content:
        return []
    #### Once we have the data content...
    ##### Split the content into lines
    lines = content.strip().splitlines()
    ##### Find the index of the separator line (---) to determine where data begins
    start = next((i + 1 for i, y in enumerate(lines) if "---" in y), -1)
    ##### If no separator is found or the index is invalid, return an empty list
    if start <= 0 or start >= len(lines):
        return []
    ##### Otherwise, return the lines spit at the pipe separator with any space padding removed
    return [[c.strip() for c in y.split("|")] for y in lines[start:]]


### Define a function to... extract metadata from a script file
def load_script_metadata(path):
    """Parses the script's docstring to load or update its metadata."""
    #### State the global variables this function may change
    global metadata
    #### Reset the metadata dictionary (so this function will live-reload when called)
    metadata = {}
    #### Attempt to read the metadata from the Python script
    try:
        content = path.read_text(encoding="utf-8")
        docstring = ast.get_docstring(ast.parse(content))
        if docstring:
            rows = read_markdown_csv(content=docstring)
            metadata.update({r[0].strip(): r[1].strip() for r in rows if len(r) >= 2})
        ##### Return the docstring so the UI can use it for instructions if necessary
        return docstring
    #### If it fails due to absence or a parsing error, return no metadata
    except Exception:
        return None


## --- Define the complex event handler functions (listed in order of use) ---


### Define a function to... select the main Python script and process its side effects
def select_main_script(entry_box, instructions_box):
    """Event handler for selecting the main script and updating UI options."""
    #### Validate the selected path and exit if it isn't a valid file
    path = resolve_path(entry_box.get())
    if not path or not path.is_file():
        return

    #### Extract the docstring and metadata using the helper function
    docstring = load_script_metadata(path)

    #### Process specific UI-affecting metadata (disabled keys)
    disabled_keys = []
    if "extras disabled" in metadata:
        disabled_keys = [x.strip() for x in metadata["extras disabled"].split(",")]

    #### Update the optional UI boxes based on the metadata that was found
    for key in SAPP["optional_arg_keys"]:
        if key in optional_entry_box_refs:  # (This condition seperates the protocol from the UI)
            entry = optional_entry_box_refs[key]["entry"]
            button = optional_entry_box_refs[key]["button"]
            ##### Disable the box if this is requested by the metadata
            if key in disabled_keys:
                entry.delete(0, tk.END)
                entry.insert(0, SAPP[key]["hint"])
                entry.config(state="disabled", fg=HINT_COLOR)
                button.config(state="disabled")
            ###### Otherwise, enable the box and ensure the text color is set correctly
            else:
                is_hint = entry.get() == SAPP[key]["hint"]
                entry.config(state="normal", fg=HINT_COLOR if is_hint else "black")
                button.config(state="normal")

    #### Load the instructions
    ##### Clear any existing text from the instructions box first
    instructions_box.config(state="normal")
    instructions_box.delete("1.0", tk.END)
    ##### Go through the list of formats in the SAPP dictionary in order of priority
    try:
        for format in SAPP["script_instructions"]["format_priority"]:
            ###### If the listed format is Markdown, check if "script-path/script-name.md" exists
            if format == ".md":
                md_path = path.with_suffix(".md")
                if md_path.exists():
                    ####### Load the Markdown file into the instructions box and stop the search
                    instructions_box.insert(tk.END, md_path.read_text(encoding="utf-8"))
                    break
            ###### If the listed format is docstring, check if the script contains a docstring
            elif format == "docstring":
                if docstring:
                    ####### Load the docstring into the instructions box and stop the search
                    instructions_box.insert(tk.END, docstring)
                    break
        ##### If the loop finished without finding any instructions, write this in the box
        if not instructions_box.get("1.0", "end-1c"):
            instructions_box.insert(tk.END, "No instructions found.")
    ##### If there was an error instead of a mere absence, write an error message in the box
    except Exception:
        instructions_box.insert(tk.END, "Error reading instructions.")
    #### Prevent the user from editing the box contents once loaded (to improve tab navigation)
    instructions_box.config(state="disabled")


### Define a function to... process all input data with the chosen scripts
def run_scripts(app, run_button, success_label, success_message):
    """Central function that executes the script processing pipeline."""
    #### State the global variables this function may change
    global last_run_successful, log_file

    #### Capture user inputs once so we don't need to retreive them for each script
    filepaths = {key: value.get() for key, value in inputs.items()}

    #### Define a helper function to... locate the correct uv executable
    def find_uv_executable():
        """Finds the correct uv executable."""
        ##### [intention comment goes here]
        target_version = metadata.get("uv version", SAPP["python_uv"]["standard_version"])

        ##### Check for a system-installed version of uv
        system_uv = shutil.which("uv")
        if system_uv:
            ###### If uv was found in the system folder, check which version it is
            try:
                result = subprocess.check_output([system_uv, "--version"], text=True)
                ####### If it's the requested version, use that
                if target_version in result:
                    return "uv"  # Return just the command name so it will print nicely
            except subprocess.CalledProcessError:
                pass
        ##### If uv wasn't found or was the wrong version, check the ScriptApp folder
        extension = ".exe" if platform.system() == "Windows" else ""
        local_uv = SAPP["python_uv"]["path"] / f"uv-{target_version}{extension}"  # e.g. uv-0.9.14
        return get_display_path(local_uv) if local_uv.exists() else None

    #### Define a helper function to... run each of the 3 external script types (pre/main/post)
    def run_this_script(key_list):
        """Helper to run each individual script in the pipeline."""
        ##### Identify the specific script type and the path provided by the user
        key = key_list[0]
        script_path = filepaths.get(key)
        ##### Skip it if the provided script path was empty or just the hint text
        if not script_path or script_path == SAPP[key]["hint"]:
            return True  # (returning as True prevents errors when a script is absent)
        ##### Announce the start of this specific script's execution in the console log
        print(f"""--- [{key}] - starting "{Path(script_path).name}" ---""")
        ##### Start the timer for this specific script
        script_start_time = time.monotonic()

        ##### Define a helper function to... recursively unpack SAPP keys into arguments
        def unpack_keys(keys):
            ###### Go through the list of keys one by one
            for key in keys:
                value = SAPP[key]
                ####### If the current key is a list of keys, unpack it
                if isinstance(value, list):
                    yield from unpack_keys(value)
                ####### If the key is not a list, add it to the arguments, otherwise add an "x"
                else:
                    if "name" in value:  # If it's a hardcoded value, convert to a display path
                        path = get_display_path(value["path"] / value["name"])
                    else:  # If it's user-provided
                        path = filepaths.get(key)  # (It's already pre-converted to a display path)
                    yield path if path and path != value.get("hint") else "x"

        ##### Construct the command line argument for the subprocess and print a copy for the user
        arguments = list(unpack_keys(key_list))
        while arguments and arguments[-1] == "x":
            arguments.pop()

        ##### Check whether we should be running the main_script command with uv
        if key == "main_script" and metadata.get("run with uv?") == "yes":
            ###### Locate the uv executable
            uv_executable = find_uv_executable()
            if not uv_executable:
                return ui_event("error", "A version of uv was requested but it couldn't be found.")
            ###### Build the uv command with anti-spam flags and permitted user flags
            command = [uv_executable, "run", "--no-progress"]
            raw_flags = metadata.get("uv flags", "")
            for flag in shlex.split(raw_flags):
                if flag.split("=")[0] in SAPP["uv_allowed_flags"]:
                    command.append(flag)
                else:
                    return ui_event("error", f"Security Error: The flag '{flag}' is not allowed.")
            command.extend(arguments)
        ###### Fallback to the standard python3 command if uv was not requested
        else:
            command = ["python3", *arguments]

        print(f"--- Command line argument:\n{shlex.join(command)}\n")
        ##### Execute the script and handle errors
        try:
            ###### Run the script as a subprocess and capture its output
            result = subprocess.run(command, cwd=BASE_FOLDER, capture_output=True, text=True)
            print(result.stdout)
            ###### If the script returned an error code, alert the user and stop
            if result.returncode != 0:
                return ui_event("error", f"Script failed:\n{result.stderr}")
            ###### Calculate the execution time for this specific script
            script_duration = time.monotonic() - script_start_time
            print(f"--- [{key}] - Finished in {script_duration:.3f}s ---\n")
            ###### Return True to indicate the script finished successfully
            return True
        ###### Handle any unexpected system errors during execution
        except Exception as error:
            return ui_event("error", f"Execution error: {error}")

    #### Check if the user has selected the mandatory input files, and that they actually exist
    for key, label in [("main_script", "main script"), ("input_csv", "main CSV")]:
        path = inputs[key].get()
        if not path:  # Did the user leave the box empty?
            return ui_event("warn", f"Please select a {label}.")
        if not resolve_path(path).is_file():  # Does the file actually exist?
            return ui_event("warn", f"The selected {label} could not be found:\n{path}")

    #### Force a metadata refresh from the file on disk
    main_path = resolve_path(inputs["main_script"].get())
    if main_path and main_path.is_file():
        load_script_metadata(main_path)

    #### Perform the initial setup for the run
    ##### Disable the Run Scripts button in the UI to prevent interference during processing
    run_button.config(state="disabled")
    ##### Force the app to update its UI immediately (since it will freeze during processing)
    app.update()
    ##### Start the total execution timer
    start_time = time.monotonic()
    ##### Create a fresh console log file if logging is enabled
    if inputs["log?"].get():
        log_filepath = SAPP["console_file"]["path"] / SAPP["console_file"]["name"]
        log_file = open(log_filepath, "w", encoding="utf-8")
    ##### Announce the start of the run in the console
    start_utc = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC"
    print(f"--- [start] - ScriptApp run started at: {start_utc} ---\n")

    ##### Check SAPP and Python versions and print a console message if there's a mismatch
    checks = [("SAPP version", SAPP["SAPP_version"])]
    if metadata.get("run with uv?") != "yes":  # Only check Python version if uv isn't handling it
        checks.append(("Python version", SAPP["python_version"]))
    for key, SAPP_ver in checks:
        script_ver = metadata.get(key)
        if script_ver and script_ver != SAPP_ver:
            print(f"{key} mismatch: script wants {script_ver} but SAPP specifies {SAPP_ver}\n")

    #### Attempt to execute the script pipeline
    try:
        ##### Run the scripts in sequence, and stop immediately if any provided script crashes
        pipeline_completed = (
            run_this_script(SAPP["prescript_arg_keys"])
            and run_this_script(SAPP["main_script_arg_keys"])
            and run_this_script(SAPP["postscript_arg_keys"])
        )
        ##### Handle a successful run completion
        if pipeline_completed:
            last_run_successful = True
            ##### Calculate the total execution time and print it with a success message
            duration = time.monotonic() - start_time
            print(f"--- [success] - Total time: {duration:.3f}s ---\n")
            ##### Display the success message to the user
            success_label.config(text=success_message)
            app.after(3000, lambda: success_label.config(text=""))

    #### Perform remaining tasks after the script pipeline execution has been attempted
    finally:
        ##### If the log file was recording, close it so it stops recording
        if log_file:
            log_file.close()
            log_file = None
        ##### Calculate an ISO 8601 UTC timestamp for archiving and replace the colons on Windows
        timestamp = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
        if platform.system() == "Windows":  # (Because Windows can't handle filenames with colons)
            timestamp = timestamp.replace(":", "-")  # Replaces any colons with dashes
        ##### Archive the files if the user has enabled logging
        if inputs["log?"].get():
            ###### Archive the console log
            archive_folder = SAPP["last_outputs_archive"]["path"]
            if log_filepath.exists():  # (Prevents errors if it doesn't exist)
                shutil.copy(log_filepath, archive_folder / f"{timestamp}-console.txt")
            ###### Archive the output CSV if the run was successful
            output_file = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]
            archive_csv = archive_folder / f"{timestamp}-last-output.csv"
            if last_run_successful and output_file.exists():
                shutil.copy(output_file, archive_csv)
            ###### If the last run failed, create an empty file to indicate no output
            else:
                archive_csv.touch()
        ##### Re-enable the button after a minimum 1 sec delay (to prevent UTC timestamp conflicts)
        delay = max(0, 1000 - int((time.monotonic() - start_time) * 1000))  # (1000 milliseconds)
        app.after(delay, lambda: run_button.config(state="normal"))


### Define a function to... view the output data in a spreadsheet
def view_output():
    """Opens the temporary output file in LibreOffice & autoconfigures mdcsv files if detected."""
    #### Prevent the user from inadvertently opening the output of an old run if this one failed
    if not last_run_successful:
        return ui_event("warn", "Run Scripts must succeed before trying to view its output.")
    #### Construct the full output file path from the SAPP dictionary
    output_filepath = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]
    #### Check if an output file exists
    if not output_filepath.exists():
        return ui_event("error", "Output file not found. Please run scripts first.")
    #### Check if the file is already open
    lock_file = output_filepath.parent / f".~lock.{output_filepath.name}#"
    if lock_file.exists():
        return ui_event("warn", "The output file is already open, please close it first.")
    #### Attempt to launch the application
    try:
        ##### Determine the executable command (Default to Linux "libreoffice" command)
        executable = "libreoffice"
        system = platform.system()
        ##### Override the command with the absolute path for Windows or macOS
        if system == "Windows":
            prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            executable = str(Path(prog_files) / "LibreOffice/program/soffice.exe")
        elif system == "Darwin":  # (The back-end name for macOS)
            executable = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        ##### Create the starting command to open LibreOffice Calc
        command = [executable, "--calc"]
        ##### If the file uses our mdcsv format, add flags that will allow a 1-click import
        try:
            if read_markdown_csv(content=output_filepath.read_text(encoding="utf-8")[:2048]):
                command.append("--infilter=CSV:124,34,76")
        except Exception:
            pass  # If the file can't be read, it will just fall back to the standard CSV import
        ##### Add the file path to the command
        command.append(str(output_filepath))

        ##### Launch LibreOffice Calc using the joined-up command
        kwargs = {}
        if system != "Windows":  # Does this on MacOS and Linux
            kwargs["start_new_session"] = True
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)

    ##### If the launch attempt fails, inform the user and provide relevant details
    except Exception as error:
        ui_event("error", f"Failed to open LibreOffice Calc:\n{error}")


### Define a function to... save the temporary output file permanently
def save_output(app, button, default_text, success_text):
    """Saves the output file to the user's chosen location."""
    #### Verify that a successful run has occurred and exit if it hasn't
    if not last_run_successful:
        return ui_event("warn", "You must Run Scripts before attempting to save its output file.")
    #### Validate the user input
    name = inputs["output_name"].get()
    folder = inputs["output_folder"].get()
    if not (name and folder):
        return ui_event("warn", "Select a file name and output folder.")
    #### Attempt to perform the entire save operation
    try:
        ##### Ask the user to confirm the overwrite if the file already exists
        new_filepath = resolve_path(folder) / f"{name}.csv"
        if new_filepath.exists():  # (This is inside the try block to catch file permission errors)
            if not messagebox.askyesno("Confirm", f"Overwrite {new_filepath.name}?"):
                return
        ##### Create the target folder if it's missing and then save the output file
        new_filepath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"], new_filepath)
        ##### If successful, inform the user without generating a popup they would have to dismiss
        button.config(text=success_text)
        app.after(3000, lambda: button.config(text=default_text))  # Resets back to normal after 3s
    ##### If the save failed, inform the user and provide diagnostic details
    except Exception as error:
        ui_event("error", f"Save failed: {error}")


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

    ### --- Define functions for performing front-end tasks ---

    #### Define a function to... update entry box text in the UI
    def update_ui_entry(entry_box, new_path, is_folder=False):
        """Helper function to update a UI entry box with a pre-formatted and shortened filepath."""
        ### Call the helper function to get the pre-formatted display path
        display_path = get_display_path(new_path, is_folder)
        #### Perform the process for inserting the display path into the UI entry box
        entry_box.config(state="normal", fg="black")  # Changes text color from grey to black
        entry_box.delete(0, tk.END)  # Clears any existing text content first
        entry_box.insert(0, display_path)  # Inserts the new formatted path into the now-empty box
        entry_box.xview_moveto(1)  # Scrolls to the end, so the filename part is visible to the user

    #### Define a function to... load an autofill configuration file
    def load_autofill(autofill_path=None):
        """Loads a configuration file to pre-fill the UI fields."""
        ##### If a path wasn't provided, open a file selection dialog.
        if autofill_path is None:
            autofill_path = fd.askopenfilename(
                initialdir=SAPP["autofills"]["path"], filetypes=SAPP["autofills"]["type"]
            )
        ##### If a path was provided, or has now been chosen, attempt to load it.
        if autofill_path:
            try:
                ###### Parse the file's data into a dictionary (filtering for valid 2-column rows)
                data_rows = read_markdown_csv(autofill_path)
                data = {row[0]: row[1] for row in data_rows if len(row) == 2}
                ###### Check if data was actually found
                if not data:
                    return ui_event("warn", "No valid autofill settings were found.")
                ###### Iterate through the loaded data and update the matching UI fields
                for key, value in data.items():
                    ####### Handle the special "Save logs?" checkbox (converts text to boolean)
                    if key == UI["log?"] or key == "log?":
                        if value:  # This prevents blank values from changing the setting
                            inputs["log?"].set(value.lower() in ["yes", "true", "1"])
                        continue
                    ####### Update the UI entry box if the key matches a known input
                    if key in inputs:
                        update_ui_entry(inputs[key], value, is_folder=(key == "output_folder"))
                        ######## Change the loaded text to black if it's a box with grey hint text
                        if key in optional_entry_box_refs:
                            optional_entry_box_refs[key]["entry"].config(fg="black")
                ###### If a main_script was autofilled, call its automatic fetching process.
                if "main_script" in data:
                    select_main_script(inputs["main_script"], instructions_box)
            ##### If the loading process failed for some reason, inform the user
            except Exception as error:
                ui_event("error", f"Could not load autofill file:\n{error}")

    #### Define a function to... give each browse button the correct command
    def browse_cmd(entry_box, SAPP_key, type="file"):
        """Creates a factory function for making each browse button work correctly when pressed."""

        ##### Define the specific command function that runs when clicked
        def on_browse_click():
            ###### Open the correct type of selection dialog based on the button type
            if type == "file":  # If the browse button is for selecting a file (the default)
                path = fd.askopenfilename(initialdir=SAPP_key["path"], filetypes=SAPP_key["type"])
            elif type == "folder":  # Alternately, if the browse button is for selecting a folder
                path = fd.askdirectory(initialdir=SAPP_key["path"])
            ###### Update the entry box in the UI (not providing a path will clear the box)
            update_ui_entry(entry_box, path, is_folder=(type == "folder"))

        ###### Return the internal function to be assigned to the button
        return on_browse_click

    ### --- Define functions for creating the repetitive UI elements ---

    #### Layout frame template (Tkinter's equivalent of a HMTL <div>)
    def draw_frame_row(row):
        """Creates a Tkinter frame with some standardized values."""
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
        if suffix is not None:  # Adds a text suffix if it was provided
            right_widget = tk.Label(frame, text=suffix)
        else:  # Adds a browse button if no suffix was provided (the assumed default)
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

            ##### Define a factory function to create unique focus event handlers each box
            def make_focus_handlers(current_box, current_key):
                ###### Capture the specific hint text for this key (closure capture)
                hint_text = SAPP[current_key]["hint"]

                ###### Define the behaviour when the user clicks inside the box (remove hint)
                def on_focus_in(event):
                    if current_box.cget("fg") == HINT_COLOR:
                        current_box.delete(0, tk.END)
                        current_box.config(fg="black")

                ###### Define the behaviour when the user clicks away (restore hint if empty)
                def on_focus_out(event):
                    if not current_box.get():
                        current_box.insert(0, hint_text)
                        current_box.config(fg=HINT_COLOR)

                ###### Return the configured handlers
                return on_focus_in, on_focus_out

            ##### Create and bind the focus handlers to the entry box
            focus_in_handler, focus_out_handler = make_focus_handlers(entry_box, key)
            entry_box.bind("<FocusIn>", focus_in_handler)
            entry_box.bind("<FocusOut>", focus_out_handler)
            ##### Create the browse button and place it next to the entry box
            button = tk.Button(frame, text=UI["browse"], command=browse_cmd(entry_box, SAPP[key]))
            button.grid(row=i, column=1)
            optional_entry_box_refs[key]["button"] = button
        return frame  # Returns the frame so it can be modified outside of this function

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
    instr_frame_lv1.pack_propagate(False)  # (This makes instructions_box exactly 700px wide)
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
    save_button.config(command=lambda: save_output(app, save_button, UI["save"], UI["save_good"]))
    save_button.pack()

    #### Draw the toggler to enable/disable logging (bottom left)
    inputs["log?"] = tk.BooleanVar(value=True)  # Makes it enabled by default
    log_checkbox = tk.Checkbutton(app, text=UI["log?"], var=inputs["log?"], activebackground=bg0)
    log_checkbox.place(relx=0.0, rely=1.0, x=0, y=-4, anchor="sw")

    #### Draw the autofill icon button with a hoverable text label (bottom right)
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


## Create the execution logic for ScriptApp
if __name__ == "__main__":  # If the script is being executed directly (instead of being imported)
    ### Create any required folders that are missing during application startup
    for path in SAPP["folders"]:
        path.mkdir(parents=True, exist_ok=True)
    ### Launch the UI
    scriptapp = tk.Tk()  # Creates a blank Tkinter window assigned to a variable named "scriptapp"
    create_user_interface(scriptapp)  # Calls the function to create the UI on that blank window
    scriptapp.mainloop()  # Starts the UI and keeps it running so the user can interact with it

# endregion --- Front-end UI code has been defined ---
