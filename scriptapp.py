#!/usr/bin/env python3
# ^ line for making this code executable as a program

# Import the relevant modules from the Python Standard Library
import csv, os, subprocess
# Import the relevant 3rd party libraries (must be installed by the user)
import tkinter as tk; from tkinter import filedialog, messagebox

# Set the default folder path to the folder ScriptApp is being run from
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define functions for...
## ...Selecting the main Python script and automatically displaying instructions when it's selected
def select_main_py_script():
    scripts_dir = os.path.join(current_dir, "scripts")
    file_path = filedialog.askopenfilename(
        initialdir = scripts_dir, filetypes = [("Python Files", "*.py")])
    py_script_entry.delete(0, tk.END); py_script_entry.insert(tk.END, file_path) ### Erase before insertion
    md_file_path = os.path.splitext(file_path)[0] + ".md"
    if os.path.exists(md_file_path):
        with open(md_file_path, "r") as file:
            md_content = file.read()
            textbox.delete("1.0", tk.END); textbox.insert(tk.END, md_content); textbox.xview_moveto(1)
    else:
        textbox.delete("1.0", tk.END); textbox.insert(tk.END, "No instructions found.")

## ...Selecting CSV data files
def select_csv(entry_widget, directory):
    data_dir = os.path.join(current_dir, directory)
    file_path = filedialog.askopenfilename(
        initialdir = data_dir, filetypes = [("CSV Files", "*.csv")])
    entry_widget.delete(0, tk.END); entry_widget.insert(tk.END, file_path); entry_widget.xview_moveto(1)

def select_main_csv_file(): select_csv(csv_file_entry, "data")
def select_data2_file(): select_csv(data2_entry, "data")
def select_data3_file(): select_csv(data3_entry, "data")
def select_data4_file(): select_csv(data4_entry, "data")
def select_data5_file(): select_csv(data5_entry, "data")

## ...Selecting additional Python scripts
def select_extra_py(entry_widget, directory):
    scripts_dir = os.path.join(current_dir, directory)
    file_path = filedialog.askopenfilename(
        initialdir = scripts_dir, filetypes = [("Python Files", "*.py")])
    entry_widget.delete(0, tk.END); entry_widget.insert(tk.END, file_path); entry_widget.xview_moveto(1)

def select_pre_py_script(): select_extra_py(pre_py_entry, "scripts/validation")
def select_mid1_py_script(): select_extra_py(mid1_py_entry, "scripts/validation")
def select_mid2_py_script(): select_extra_py(mid2_py_entry, "scripts/validation")
def select_post_py_script(): select_extra_py(post_py_entry, "scripts/validation")

## ...Processing the chosen data according to the chosen script (i.e. the main buisness logic)
output_file_name = "ScriptApp_temporary_data.csv" ### Default file name, gets overwritten each time
processing_complete = 0 ### Prevents old temp file from being saved

def process_data():
    global processing_complete
    py_main_script = py_script_entry.get()
    input_file_name = csv_file_entry.get()
    if not (py_main_script and input_file_name and output_file_name):
        messagebox.showwarning("Warning", "Please select a main Python script and main CSV data file.")
        return
    extra_entries = [data2_entry, data3_entry, data4_entry, data5_entry, mid1_py_entry, mid2_py_entry]
    extra_args = [] # Condenses a long list of command line arguments
    for entry in extra_entries:
        if os.path.isfile(entry.get()):
            extra_args.append(entry.get())
        else:
            extra_args.append("blank")  ### Add placeholder value if file not entered
    arg_protocol = [py_main_script, input_file_name, output_file_name] + extra_args
    try:
        prescript_returncode = 0
        if os.path.isfile(pre_py_entry.get()): ### Check it's a valid file and not the default text
            prescript = subprocess.Popen(["python3", pre_py_entry.get()] + arg_protocol)
            prescript.wait()
            prescript_returncode = prescript.returncode
        if prescript_returncode == 0: ### Main script won't run if the prescript runs and then fails
            processing = subprocess.Popen(["python3"] + arg_protocol)
            processing.wait()
            if os.path.isfile(post_py_entry.get()):
                subprocess.Popen(["python3", post_py_entry.get(), output_file_name]) ### Postscript
            processing_complete = 1 ### Allows user to save the new temp file
            messagebox.showinfo("Success", "Processing completed.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None

## ...Viewing the output data file
def view_output_csv():
    if processing_complete == 1:
        try:
            subprocess.Popen(["libreoffice", "--calc", current_dir, output_file_name])
        except Exception as e:
            messagebox.showerror("Error", str(e))
    else:
        messagebox.showwarning("Processing Incomplete", "Please run the script first. If you have already tried to run the script, check the console window for errors.")

## ...Navigating to the chosen subfolder
def select_subfolder():
	data_directory = os.path.join(current_dir, "data")
	subfolder_path = filedialog.askdirectory(initialdir=data_directory)
	subfolder_entry.delete(0, tk.END); subfolder_entry.insert(tk.END, subfolder_path)

## ...Saving the output data file
output_file_name_temp = output_file_name

def save_output_csv():
	output_file_name = output_file_name_entry.get()
	subfolder_path = subfolder_entry.get()
	if output_file_name and subfolder_path and processing_complete==1:
		try:
			output_file_path = os.path.join(subfolder_path, output_file_name + ".csv")
			with open(output_file_name_temp, 'r') as input_file, open(output_file_path, 'w', newline='') as output_file:
				reader = csv.reader(input_file, delimiter='\t')
				writer = csv.writer(output_file, delimiter='\t')
				writer.writerows(reader)
			messagebox.showinfo("Success", f"Output CSV saved as {output_file_name} in {subfolder_path}")
		except Exception as e:
			messagebox.showerror("Error", str(e))
	else:
		messagebox.showwarning("Warning", "Please enter the output file name, output folder and make sure you have processed the data before trying to save it.")

# Code for displaying the graphical user interface that makes use of the above functions
## Create the main window
window = tk.Tk(); window.title("ScriptApp")
window.grid_rowconfigure([0,1,2,3,4,5,6,7,8], pad=8) # Specifies which rows of the UI to space out

spacing_frame = tk.Frame(window).grid(row=0, column=0, columnspan=5) # Top padding

## Python main script selection box
py_script_frame = tk.Frame(window); py_script_frame.grid(row=1, column=0, columnspan=5)
py_script_label = tk.Label(py_script_frame, text="Select main Python script:").grid(row=0, column=0, columnspan=5)
py_script_entry = tk.Entry(py_script_frame, width=60); py_script_entry.grid(row=1, column=0)
py_script_button = tk.Button(py_script_frame, text="Browse", command=select_main_py_script, width=6).grid(row=1, column=1)

## Instructions box
instructions_frame = tk.Frame(window); instructions_frame.grid(row=2, column=0, columnspan=5)
instructions_label = tk.Label(instructions_frame, text="    Read instructions:").grid(row=0, column=0) # Hack to center text
textbox = tk.Text(instructions_frame, width=98, height=32)
scroll = tk.Scrollbar(instructions_frame, command=textbox.yview); scroll.grid(row=1, column=1, sticky="ns")
textbox.configure(state="normal", wrap="word", font=("Arial", 10), yscrollcommand=scroll.set); textbox.grid(row=1, column=0)

## CSV main file selection box
csv_file_frame = tk.Frame(window); csv_file_frame.grid(row=3, column=0, columnspan=5)
csv_file_label = tk.Label(csv_file_frame, text="Select main CSV data file:").grid(row=0, column=0, columnspan=5)
csv_file_entry = tk.Entry(csv_file_frame, width=60); csv_file_entry.grid(row=1, column=0)
csv_file_button = tk.Button(csv_file_frame, text="Browse", command=select_main_csv_file, width=6).grid(row=1, column=1)

## Frame for the extra input boxes and 2 buttons that sit between them
big_frame = tk.Frame(window); big_frame.grid(row=4, column=0, columnspan=5); big_frame.grid_columnconfigure(1, pad=96)
extra_data_frame = tk.Frame(big_frame); extra_data_frame.grid(row=0, column=0, rowspan=5)
process_button = tk.Button(big_frame, text="Run Scripts", command=process_data, height=2).grid(row=0, column=1, rowspan=3)
view_button = tk.Button(big_frame, text="Inspect Output CSV", command=view_output_csv).grid(row=3, column=1, rowspan=2)
extra_scripts_frame = tk.Frame(big_frame); extra_scripts_frame.grid(row=0, column=2, rowspan=5)

### Function for creating extra data and script input boxes
def extra_box(parent_frame, row, entry_text, button_command):
	frame = tk.Frame(parent_frame); frame.grid(row=row, column=0, columnspan=2)
	entry = tk.Entry(frame, width=16); entry.insert(0, entry_text); entry.grid(row=0, column=0)
	button = tk.Button(frame, text="Browse", command=button_command); button.grid(row=0, column=1)
	return entry # Allows the entry box to take user input

#### Extra data
extra_data_label = tk.Label(extra_data_frame, text="Extra data:").grid(row=0, column=0, columnspan=2)
data2_entry = extra_box(extra_data_frame, 1, "Data #2", select_data2_file)
data3_entry = extra_box(extra_data_frame, 2, "Data #3", select_data3_file)
data4_entry = extra_box(extra_data_frame, 3, "Data #4", select_data4_file)
data5_entry = extra_box(extra_data_frame, 4, "Data #5", select_data5_file)

#### Extra scripts
extra_scripts_label = tk.Label(extra_scripts_frame, text="Validation scripts:").grid(row=0, column=0, columnspan=2)
pre_py_entry = extra_box(extra_scripts_frame, 1, "Pre-script", select_pre_py_script)
mid1_py_entry = extra_box(extra_scripts_frame, 2, "Script #3", select_mid1_py_script)
mid2_py_entry = extra_box(extra_scripts_frame, 3, "Script #4", select_mid2_py_script)
post_py_entry = extra_box(extra_scripts_frame, 4, "Post-script", select_post_py_script)

## Output file name entry box
output_file_name_frame = tk.Frame(window); output_file_name_frame.grid(row=5, column=0, columnspan=5)
output_file_name_label = tk.Label(output_file_name_frame, text="Choose output file name:").grid(row=0, column=0, columnspan=5)
output_file_name_entry = tk.Entry(output_file_name_frame, width=36); output_file_name_entry.grid(row=1, column=0)
csv_suffix = tk.Label(output_file_name_frame, text=".csv").grid(row=1, column=1) # Adds .csv to reduce ambiguity for the user

## Subfolder selection box
subfolder_frame = tk.Frame(window); subfolder_frame.grid(row=6, column=0, columnspan=5)
subfolder_label = tk.Label(subfolder_frame, text="Select output file folder:").grid(row=0, column=0, columnspan=5)
subfolder_entry = tk.Entry(subfolder_frame, width=60); subfolder_entry.grid(row=1, column=0)
subfolder_button = tk.Button(subfolder_frame, text="Browse", command=select_subfolder, width=6).grid(row=1, column=1)

## Save output CSV button
save_button = tk.Button(window, text="Save Output CSV", command=save_output_csv).grid(row=7, column=0, columnspan=5)

spacing_frame = tk.Frame(window).grid(row=8, column=0, columnspan=5) # Bottom padding

# Start the graphical interface
window.mainloop()
