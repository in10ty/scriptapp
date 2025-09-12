# Prerequisite code
## Import the relevant Python libraries
### Modules from the Python Standard Library:
import datetime, sys, csv
### 3rd party libraries: (Which will need to be installed first)
#### None (No 3rd party libraries are needed for this script)

## Get the input and output file names that were entered by the user
input_file_name = sys.argv[1]
output_file_name = sys.argv[2]

## Read the input CSV file that's formatted as a Markdown table
with open(input_file_name, 'r') as file:
    spreadsheet = list(csv.reader(file, delimiter='|'))
    
## Shorten the variable name to "sheet" for conciseness
sheet = spreadsheet

# Explicitly Stated Intentions
## 1) Swap the column order
### Go through each row of the sheet and reorder the columns
for row in sheet:
    row[0], row[1] = row[1], row[0]

## 2) Convert the dates to standardized Unicode dates
### Define a function for converting dates
def parse_date(date_string):
    #### Specify all the expected date input formats
    expected_formats = [
        '%m/%d/%Y', ##### Handles dates like "06/1/2025"
        '%m/%d/%y', ##### Handles dates like "06/14/25" and "6/18/25"
        ]
    for format in expected_formats:
        try:
            #### If the date matches this format, convert it to "YYYY-MM-DD"
            return datetime.datetime.strptime(date_string, format).strftime('%Y-%m-%d')
        except ValueError:
            #### If the date doesn't match that format, try the next format in the list
            pass
    #### If the date doesn't match any of our expected formats, raise an error
    raise ValueError(f"Date '{date_string}' is not in a recognized format.")

### Specify which rows are headers, and which ones contain data
header_rows = sheet[:2]
data_rows = sheet[2:]

### Call the function to convert the dates in data rows
for row in data_rows:
    row[0] = parse_date(row[0])

## 3) Sort the rows by date
sorted_data_rows = sorted(data_rows, key=lambda row: row[0])

### Add the header back to the top of the sheet.
sheet = header_rows + sorted_data_rows

## 4) Save the modified data as a new output CSV file
with open(output_file_name, 'w') as output_file:
    writer = csv.writer(output_file, delimiter='|')
    writer.writerows(sheet)
