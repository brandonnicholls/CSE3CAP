from tkinter import *
from tkinter import ttk

root = Tk()
root.title("FireFind - Results")
root.geometry("1920x1080") 

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=0)  # Filter frame - don't expand.
root.rowconfigure(1, weight=1)  # Results frame - expand to fill space.

style = ttk.Style()
style.configure("Outer.TFrame", background="lightgray", relief="raised", borderwidth=2)
style.configure("Inner.TFrame", background="lightblue", relief="sunken", borderwidth=2)
style.configure("Inner2.TFrame", background="lightgreen", relief="flat", borderwidth=1)
style.configure("Results.TFrame", background="white", relief="sunken", borderwidth=2)
style.configure("Header.TLabel", background="lightsteelblue", font=("Helvetica", 10, "bold"))
style.configure("Green.TButton", foreground="white", font=("Helvetica", 9, "bold"))
style.map("Green.TButton", background=[('active', '#45a049'), ('!active', '#4CAF50')])

# Create outer/parent frame.
outer_frame = ttk.Frame(root, style="Outer.TFrame", width=900, height=35)
outer_frame.grid(row=0, column=0, padx=5, pady=(100, 5), sticky="n")
outer_frame.grid_propagate(False)  # Prevents frame from shrinking to fit contents.

# Configure outer_frame grid columns.
columns_config = [
    (0, 0),  # Search entry
    (1, 0),  # Severity label
    (2, 0),  # Severity dropdown
    (3, 0),  # Source IP label
    (4, 0),  # Source IP dropdown
    (5, 0),  # Destination IP label
    (6, 0),  # Destination IP dropdown
    (7, 1),  # Spacer column
]

for col, weight in columns_config:
    outer_frame.columnconfigure(col, weight=weight)

outer_frame.rowconfigure(0, weight=1)
outer_frame.rowconfigure(1, weight=0)  # Don't expand the bottom row.


# Search Entry.
entry = StringVar()
search = ttk.Entry(outer_frame, textvariable=entry, font=("Helvetica", 12), width=20)
search.grid(row=1, column=0, padx=5, pady=5, sticky="w")

# Severity Label (positioned to the right of search entry).
label = ttk.Label(outer_frame, text='Severity')
label.grid(row=1, column=1, padx=5, pady=5, sticky="w")

# Severity Dropdown Menu.
dropdown_var = StringVar()
severity_options = ["All", "Critical", "High", "Medium", "Low", "Info"]
dropdown = ttk.Combobox(outer_frame, textvariable=dropdown_var, values=severity_options, 
                       state="readonly", width=12)
dropdown.set("All")  # Set default value.
dropdown.grid(row=1, column=2, padx=5, pady=5, sticky="w")

# Source IP Label (positioned to the right of dropdown).
source_ip_label = ttk.Label(outer_frame, text='Source IP')
source_ip_label.grid(row=1, column=3, padx=5, pady=4, sticky="w")

# Source IP Dropdown Menu.
source_ip_var = StringVar()
source_ip_options = ["All", "192.168.1.1", "192.168.1.100", "10.0.0.1", "172.16.0.1", "Custom..."]
source_ip_dropdown = ttk.Combobox(outer_frame, textvariable=source_ip_var, values=source_ip_options, 
                                 state="normal", width=12)
source_ip_dropdown.set("All")  # Set default value.
source_ip_dropdown.grid(row=1, column=4, padx=5, pady=5, sticky="w")

# Destination IP Label.
dest_ip_label = ttk.Label(outer_frame, text='Destination IP')
dest_ip_label.grid(row=1, column=5, padx=5, pady=5, sticky="w")

# Destination IP Dropdown Menu.
dest_ip_var = StringVar()
dest_ip_options = ["All", "192.168.1.10", "192.168.1.50", "10.0.0.10", "172.16.0.10", "Custom..."]
dest_ip_dropdown = ttk.Combobox(outer_frame, textvariable=dest_ip_var, values=dest_ip_options, 
                               state="normal", width=12)
dest_ip_dropdown.set("All")  # Set default value.
dest_ip_dropdown.grid(row=1, column=6, padx=5, pady=5, sticky="w")

# Export button.
button = ttk.Button(outer_frame, text="Export", width=10, style="Green.TButton")
button.grid(row=1, column=7, padx=5, pady=5)

# Results Display Frame.
results_frame = ttk.Frame(root, style="Results.TFrame", width=1000, height=500)
results_frame.grid(row=1, column=0, padx=20, pady=(50, 20), sticky="n")
results_frame.grid_propagate(False)  # Prevent frame from shrinking to fit contents.

# Configure results frame grid - 9 columns for the improved headings.
results_columns_config = [
    (0, 0),  # ID
    (1, 0),  # Action
    (2, 0),  # Protocol
    (3, 1),  # Source IP
    (4, 0),  # Src Port
    (5, 1),  # Destination IP
    (6, 0),  # Dst Port
    (7, 0),  # Risk Level
    (8, 2),  # Description
]

for col, weight in results_columns_config:
    results_frame.columnconfigure(col, weight=weight)

results_frame.rowconfigure(0, weight=0)  # Header row
results_frame.rowconfigure(1, weight=1)  # Results content area

# Column Headers.
headers = ["ID", "Action", "Protocol", "Source IP", "Src Port", "Destination IP", "Dst Port", "Risk Level", "Description"]
header_widths = [4, 7, 8, 12, 8, 13, 8, 10, 11]

for i, (header, width) in enumerate(zip(headers, header_widths)):
    header_label = ttk.Label(results_frame, text=header, style="Header.TLabel", width=width)
    header_label.grid(row=0, column=i, padx=1, pady=2, sticky="ew")

# Results content area (for future data display).
content_frame = ttk.Frame(results_frame)
content_frame.grid(row=1, column=0, columnspan=9, sticky="nsew", padx=5, pady=5)
content_frame.columnconfigure(0, weight=1)
content_frame.rowconfigure(0, weight=1)

# Placeholder text for now.
placeholder_label = ttk.Label(content_frame, text="Results will be displayed here...", 
                            font=("Helvetica", 12), foreground="gray")
placeholder_label.grid(row=0, column=0, pady=50)




root.mainloop()

