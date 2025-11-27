#!/usr/bin/env python3
# ^ "Shebang" first line that makes this code executable as a program
"""
Explicitly Stated Intentions:
1. Act as a user-friendly wrapper for running Intentionalist data processing scripts.
2. Demonstrate a minimal implementation of the ScriptApp Processing Protocol (SAPP) that...
    2.1. Has just enough features to be useful.
    2.2. Is as self-contained as possible.
    2.3. Has short, simple and well-documented code, so that inexperienced coders (who might not
    have read the source code of *any* other program) can understand exactly how it works and
    start writing their own scripts ASAP.
"""  # (Python's standard "module docstring", used to briefly explain what the code in a file does)

# region --- Perform the initial setup for the script (imports, constants, variables, ect.) ---

## Define special dunder (double underscore) variables
__author__ = "bendini"  # The Github username of this script's owner/maintainer
__version__ = "0.1.001"  # (This version number is also displayed in the UI for screenshot purposes)

## Import relevant modules from the Python Standard Library (reason for use given in side comments)
import ast  # Used for safely parsing Python code to extract docstrings
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
    input("ERROR: Tkinter must be installed first for ScriptApp to work. (Press Enter to exit...)")

## Define global constants (can be used anywhere in the code, WON'T be modified by the code)
### Set folder locations
BASE_FOLDER = Path(__file__).parent.resolve()  # Sets the base folder relative to this file's path
P_DATA = BASE_FOLDER / "data"  # Set the path for... CSV data
P_AGN_DATA = P_DATA / "agnostic-data"  # ...data with other file extensions
P_SCRIPTS = BASE_FOLDER / "scripts"  # ...Python scripts
P_VALIDS = P_SCRIPTS / "validation"  # ...Python validation scripts
P_MODULES = P_SCRIPTS / "py-modules"  # ...Python modules written for our ecosystem
P_RUST = P_SCRIPTS / "rust-code"  # ...compiled Rust extensions & source code
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
    "SAPP_version": "0.2",  # (Increases if a breaking change is made to the protocol)
    "python_version": "3.12.3",  # The Python version that scripts should expect by default
    ##### ScriptApp's outer validation wrapper
    "prescript": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "prescript"},  # Runs before main
    "postscript": {"path": P_VALIDS, "type": PY_V_SCRIPT, "hint": "postscript"},  # Runs after main
    "output_name": {"default": ""},  # Used to rename output_csv if it was successful
    "output_folder": {"path": P_DATA, "default": P_DATA},  # The final output_csv save location
    "metadata": ["SAPP version", "Python version", "extras disabled"],  # Found in script docstring
    ##### The ordered sequence of arguments that will be passed for each script type
    "optional_arg_keys": ["data2", "data3", "data4", "data5", "valscriptA", "valscriptB"],
    "main_script_arg_keys": ["main_script", "input_csv", "output_csv", "optional_arg_keys"],
    "prescript_arg_keys": ["prescript", "main_script_arg_keys", "postscript"],
    "postscript_arg_keys": ["postscript", "output_csv", "main_script"],
    ##### Automatic form input filling and folder creation
    "autofills": {"path": P_AUTOFILLS, "type": CSV_AUTOFILL},  # Autofill folder for manual loading
    "af_override_file": {"path": BASE_FOLDER, "name": AF_OVERRIDE_NAME},  # Autofill on startup
    "folders": [P_DATA, P_AGN_DATA, P_SCRIPTS, P_VALIDS, P_MODULES, P_RUST, P_AUTOFILLS, P_TEMP],
    ##### Automatic saving of output data and console logs from previous runs
    "console_file": {"path": BASE_FOLDER, "name": TEMP_CONSOLE_NAME},  # Captures all console output
    "last_outputs_archive": {"path": P_TEMP},  # Where the old logs and output CSVs are saved
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
script_requirements = None
headless_warnings = False
suppress_mod_popup = False
last_run_successful = False
current_run_timestamp = None
instructions_box = None
inputs = {}
optional_entry_box_refs = {}
last_successful_run_context = {}
log_file_handle = None  # Holds the reference to the open console log file

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
def print(*args, **kwargs):
    """Enhances Python's default print() function so it also writes print messages to a log file."""
    #### Attempt to do all of the following things:
    try:
        ##### Construct the message exactly as print would output it
        msg = " ".join(map(str, args)) + kwargs.get("end", "\n")
        ##### If the global log file handle is open, write to it
        if log_file_handle and not log_file_handle.closed:
            log_file_handle.write(msg)
    ##### ...And if any of those things fail:
    except Exception:
        pass  # Do nothing about it, so that ScriptApp won't crash
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
        messagebox.showerror("Error", message)
    elif message_type == "warn":
        print(f"UI Message - Warning: {message}")
        messagebox.showwarning("Warning", message)
    elif message_type == "info":
        print(f"UI Message - Info: {message}")
        messagebox.showinfo("Info", message)       
    else:  # (If the type wasn't specified as "error", "warn" or "info")
        print("ui_event function error: invalid message type specified")


### Define a function to... handle our special Markdown table CSV format
def read_markdown_csv(file_path=None, mode="read", data=None, header=None, content=None):
    """Safely reads, writes, or updates a Markdown-formatted CSV file."""
    ### Handle the logic for reading data from the file

    try:
        #### If content isn't provided directly, read it from the file
        if content is None and file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
            ##### If it's not in utf-8, reject it instead of solving the user's incorrect encoding
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


## --- Define the complex event handler functions (listed in order of use) ---


### Define a function to... select the main Python script and process its side effects
def select_main_script(entry_box, instructions_box):
    """Event handler for selecting the main script and updating UI options."""
    global script_requirements

    def extract_script_metadata(script_path):
        """Simple parser for script requirements."""
        reqs = {}
        try:
            content = script_path.read_text(encoding="utf-8")
            docstring = ast.get_docstring(ast.parse(content))
            if docstring:
                rows = read_markdown_csv(content=docstring)
                data_map = {row[0].strip(): row[1].strip() for row in rows if len(row) >= 2}

                # Only check for the specific keys we care about in Simple Mode
                if "extras disabled" in data_map:
                    reqs["extras disabled"] = [
                        x.strip() for x in data_map["extras disabled"].split(",")
                    ]
        except Exception:
            pass
        return reqs

    def configure_ui_from_metadata(requirements):
        """Disables UI boxes based on metadata."""
        keys_to_disable = requirements.get("extras disabled", [])

        # 1. Enable everything first
        for key in SAPP["optional_arg_keys"]:
            if key in optional_entry_box_refs:
                optional_entry_box_refs[key]["entry"].config(state="normal", fg="black")
                optional_entry_box_refs[key]["button"].config(state="normal")

        # 2. Disable requested boxes
        for key in keys_to_disable:
            if key in optional_entry_box_refs:
                entry = optional_entry_box_refs[key]["entry"]
                entry.delete(0, tk.END)
                entry.insert(0, SAPP[key]["hint"])
                entry.config(state="disabled", fg=HINT_COLOR)
                optional_entry_box_refs[key]["button"].config(state="disabled")

    # Logic Start
    resolved_path = resolve_path(entry_box.get())

    if not resolved_path or not resolved_path.is_file():
        script_requirements = {}
        return

    script_requirements = extract_script_metadata(resolved_path)
    configure_ui_from_metadata(script_requirements)

    # Simple Instructions: Just read the Docstring
    instructions_box.config(state="normal")
    instructions_box.delete("1.0", tk.END)

    try:
        content = resolved_path.read_text(encoding="utf-8")
        docstring = ast.get_docstring(ast.parse(content))
        if docstring:
            instructions_box.insert(tk.END, docstring)
        else:
            instructions_box.insert(tk.END, "No instructions found.")
    except Exception:
        instructions_box.insert(tk.END, "Error reading script.")

    instructions_box.config(state="disabled")


## Define a function to... process all input data with the chosen scripts
def run_scripts(app, run_button, success_label, success_message):
    """Central function that executes the script processing pipeline."""
    global last_run_successful, last_successful_run_context

    # 1. Validation
    if not inputs["main_script"].get() or not resolve_path(inputs["main_script"].get()).is_file():
        ui_event("warn", "Please select a main script.")
        return

    # 2. Prep
    print("\n--- [starting] - ScriptApp Simple run ---\n")
    run_button.config(state="disabled")
    app.update()  # Force a UI update right now since it will freeze during processing
    start_time = time.monotonic()
    filepaths = {k: v.get() for k, v in inputs.items()}

    # 3. Execution Helper
    def run_this_script(key_list):
        script_key = key_list[0]
        script_path = filepaths.get(script_key)
        # Skip if empty or hint
        if not script_path or script_path == SAPP[script_key]["hint"]:
            return True

        print(f"--- Running {script_key}: {Path(script_path).name} ---")

        # (Simplified arg construction logic for brevity)
        def build_args_recursive(keys):
            res = []
            for k in keys:
                if isinstance(SAPP.get(k), list):
                    res.extend(build_args_recursive(SAPP[k]))
                elif k in SAPP:
                    if "name" in SAPP[k]:
                        res.append(str(SAPP[k]["path"] / SAPP[k]["name"]))
                    else:
                        val = filepaths.get(k)
                        res.append(val if val and val != SAPP[k]["hint"] else "x")
            return res

        cmd_args = build_args_recursive(key_list)
        # Clean trailing 'x'
        while cmd_args and cmd_args[-1] == "x":
            cmd_args.pop()

        # Run
        full_cmd = ["python3", cmd_args[0]] + cmd_args[1:]
        print(f"Command: {shlex.join([Path(x).name for x in full_cmd])}\n")

        try:
            result = subprocess.run(
                full_cmd, cwd=BASE_FOLDER, capture_output=True, text=True
            )  # Note: running scripts on the shared main thread like this causes the UI to freeze
            print(result.stdout)
            if result.returncode != 0:
                ui_event("error", f"Script failed:\n{result.stderr}")
                return False
            return True
        except Exception as e:
            ui_event("error", f"Execution error: {e}")
            return False

    # 4. Pipeline
    try:
        # Pre-script
        if not run_this_script(SAPP["prescript_arg_keys"]):
            return
        # Main
        if not run_this_script(SAPP["main_script_arg_keys"]):
            return
        # Post-script
        if not run_this_script(SAPP["postscript_arg_keys"]):
            return

        # Success
        last_run_successful = True
        # Save context for "Save Output" button
        last_successful_run_context = {"input_csv_path": inputs["input_csv"].get()}

        duration = time.monotonic() - start_time
        print(f"\n--- [success] - time: {duration:.3f}s ---\n")
        success_label.config(text=success_message)
        app.after(3000, lambda: success_label.config(text=""))

        # Archive previous logs (Simple Rename)
        log_src = SAPP["console_file"]["path"] / SAPP["console_file"]["name"]
        if log_src.exists():
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            shutil.copy(log_src, P_TEMP / f"{timestamp}_console.txt")

    finally:
        run_button.config(state="normal")


## Define a function to... view the output data in a spreadsheet
def view_output():
    """Opens the temporary output file in LibreOffice & autoconfigures mdcsv files if detected."""
    ### Construct the full output file path from the SAPP dictionary
    output_file_path = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]

    ### Check if an output file exists
    if not output_file_path.exists():
        ui_event("error", "Output file not found. Please run scripts first.")
        return

    ### Determine if the file is our special Markdown format
    is_markdown = False
    try:
        with open(output_file_path, "r", encoding="utf-8") as f:
            # Check the first 5 lines for the table separator signature
            for _ in range(5):
                if "---" in f.readline():
                    is_markdown = True
                    break
    except Exception:
        pass  # If we can't read it (e.g. binary), assume it's not Markdown

    ### Launch the application
    try:
        command = ["libreoffice", "--calc"]
        
        #### Apply the Markdown CSV config flags if the file is mdcsv format
        if is_markdown:
            command.append("--infilter=CSV:7C,34,UTF-8")
            
        command.append(str(output_file_path))
        subprocess.Popen(command)
    except Exception as error:
        ui_event("error", f"Failed to open LibreOffice:\n{error}")


## Define a function to... save the temporary output file permanently
def save_output(app, button, success_message):
    """Saves the output file to the user's chosen location."""
    if not last_run_successful:
        ui_event("warn", "Run scripts first.")
        return

    name, folder = inputs["output_name"].get(), inputs["output_folder"].get()
    if not (name and folder):
        ui_event("warn", "Select name and folder.")
        return

    src = SAPP["output_csv"]["path"] / SAPP["output_csv"]["name"]
    dest = resolve_path(folder) / f"{name}.csv"

    if dest.exists():
        if not messagebox.askyesno("Confirm", f"Overwrite {dest.name}?"):
            return

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)

        # UI Feedback
        orig_text = button.cget("text")
        button.config(text=success_message)
        app.after(3000, lambda: button.config(text=orig_text))

    except Exception as e:
        ui_event("error", f"Save failed: {e}")


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
        ##### If a path wasn't provided, open a file selection dialog.
        if autofill_path is None:
            autofill_path = fd.askopenfilename(
                initialdir=SAPP["autofills"]["path"], filetypes=SAPP["autofills"]["type"]
            )
        ##### If a path was provided, or has now been chosen, proceed with loading it.
        if autofill_path:
            try:
                data_rows = read_markdown_csv(autofill_path)
                data = {row[0]: row[1] for row in data_rows if len(row) == 2}

                for key, value in data.items():
                    if key in inputs:
                        update_ui_entry(inputs[key], value)
                        if key in optional_entry_box_refs:
                            optional_entry_box_refs[key]["entry"].config(fg="black")

                ##### If a main_script was autofilled, call its automatic fetching process.
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

    #### Layout frame template (Tkinter's equivalent of a HMTL <div>)
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


## Create the execution logic for ScriptApp
if __name__ == "__main__":  # If the script is being executed directly (instead of being imported)
    ### Create any required folders that are missing during application startup
    for path in SAPP["folders"]:
        path.mkdir(parents=True, exist_ok=True)
    ### Create the UI
    #### Create a blank Tkinter window assigned to "app"
    app = tk.Tk()
    ##### Call the function to create the UI on that blank window
    create_user_interface(app)
    #### Start the UI and keep it running so the user can interact with it
    app.mainloop()

# endregion --- Front-end UI code has been defined ---
