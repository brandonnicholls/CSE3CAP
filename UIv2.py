import tkinter as tk
import tkinter.filedialog as fd
from tkinter import messagebox  

class UI:
    def __init__(self, root):
        self.root = root
        root.title("FireFind")
        # TODO Set FireFind.ico icon to have transparent background
        self.icon_image = tk.PhotoImage(file="FireFind.ico")
        root.iconphoto(False, self.icon_image)
        root.geometry("1920x1080")
        root.configure(bg="white")
        root.resizable(True, True)
        root.geometry("800x500")
        self.active_nav = None
        self.nav_buttons = {}
        self.create_widgets()

    def create_widgets(self):
        # Top bar 
        TOP_BAR_COLOR = "#d19a6e"
        TOPBAR_HEIGHT = 50  
        topbar = tk.Frame(self.root, bg=TOP_BAR_COLOR, height=TOPBAR_HEIGHT)
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)  

        # Logo text
        fire_label = tk.Label(topbar, text="🔥", bg=TOP_BAR_COLOR, fg="#e36d2c", font=("Arial", 14, "bold"))
        fire_label.pack(side="left", padx=(15, 0))
        text_label = tk.Label(topbar, text="FireFind", bg=TOP_BAR_COLOR, fg="white", font=("Arial", 14, "bold"))
        text_label.pack(side="left", padx=(0, 10))

        # Sidebar
        SIDEBAR_COLOR = "#f5f5f5"
        ACTIVE_BG = "#e6f0ff"  # Light blue for active
        ACTIVE_FG = "#3390ff"  # Blue text for active
        NORMAL_BG = SIDEBAR_COLOR
        NORMAL_FG = "#444444"

        sidebar = tk.Frame(self.root, bg=SIDEBAR_COLOR, width=200)
        sidebar.pack(side="left", fill="y")

        nav_items = [
            ("Dashboard", self.dashboard_screen, "🏠 "),
            ("Upload", self.upload_screen, "📂 "),
            ("Results", self.results_screen, "📊 "),
            ("Settings", self.configuration_screen, "⚙️"),
        ]

        self.nav_buttons = {}
        for name, command, icon in nav_items:
            btn = tk.Button(
                sidebar,
                text=f"{icon} {name}",
                anchor="w",
                relief="flat",
                bg=NORMAL_BG,
                fg=NORMAL_FG,
                padx=20,
                pady=8,
                font=("Arial", 12),
                bd=0,
                activebackground=ACTIVE_BG,
                activeforeground=ACTIVE_FG,
                command=lambda n=name, c=command: self.on_nav_click(n, c)
            )
            btn.pack(fill="x")
            self.nav_buttons[name] = btn

        # Back button at the bottom
        back_btn = tk.Button(sidebar, text="⬅️ Back", anchor="w", relief="flat",
                             bg=SIDEBAR_COLOR, fg="black", padx=20, pady=8, font=("Arial", 12))
        back_btn.pack(side="bottom", fill="x")
        
        # Content Frame
        self.content_frame = tk.Frame(self.root, bg="white")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.content_frame.pack_propagate(False)

        # Set default page
        self.on_nav_click("Dashboard", self.dashboard_screen)

    def on_nav_click(self, name, command):
        # Highlight the active button
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.config(bg="#e6f0ff", fg="#3390ff")
            else:
                btn.config(bg="#f5f5f5", fg="#444444")
        # Call the page function
        command()

    def clear_content(self):
        # Clear all widgets in the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def upload_screen(self):
        self.clear_content()
        file_frame = tk.Frame(self.content_frame, bg="white")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Title
        title = tk.Label(file_frame, text="Upload Firewall Rules", font=("Helvetica", 16, "bold"), bg="white", anchor="w")
        title.pack(anchor="w", pady=(0, 15))

        # Upload a file section
        upload_section = tk.Frame(file_frame, bg="white")
        upload_section.pack(anchor="w", pady=(0, 20))

        upload_label = tk.Label(upload_section, text="Upload a file", font=("Helvetica", 12, "bold"), bg="white")
        upload_label.pack(anchor="w")

        upload_desc = tk.Label(upload_section, text="Select a firewall rules export file (CSV or XLSX)", font=("Helvetica", 10), bg="white")
        upload_desc.pack(anchor="w", pady=(0, 8))

        # File selection
        file_select_frame = tk.Frame(upload_section, bg="white")
        file_select_frame.pack(anchor="w", pady=(0, 10))

        self.selected_file = tk.StringVar()

        def choose_file():
            file_path = fd.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
            if file_path:
                self.selected_file.set(file_path)

        choose_btn = tk.Button(file_select_frame, text="Choose File", command=choose_file)
        choose_btn.pack(side="left")

        upload_btn = tk.Button(
            file_select_frame,
            text="Upload",
            bg="#4285f4",
            fg="white",
            padx=10,
            command=self.upload_file  
        )
        upload_btn.pack(side="left", padx=(10, 0))

        # Supported Vendors
        vendors_label = tk.Label(file_frame, text="Supported Vendors", font=("Helvetica", 12, "bold"), bg="white")
        vendors_label.pack(anchor="w", pady=(20, 0))

        vendors = ["Fortinet", "Sophos", "Barracuda", "Checkpoint", "WatchGuard"]
        for vendor in vendors:
            tk.Label(file_frame, text=vendor, font=("Helvetica", 10), bg="white").pack(anchor="w")

        # File Format
        format_label = tk.Label(file_frame, text="File Format", font=("Helvetica", 12, "bold"), bg="white")
        format_label.pack(anchor="w", pady=(20, 0))

        tk.Label(file_frame, text="Accepted formats: CSV, XLSX", font=("Helvetica", 10), bg="white").pack(anchor="w")
        tk.Label(file_frame, text="File size limit: 10 MB", font=("Helvetica", 10), bg="white").pack(anchor="w")

    def upload_file(self):
        """Upload file logic"""
        if not self.selected_file.get():
            messagebox.showwarning("No file", "Please choose a file before uploading.")
        else:
            messagebox.showinfo("Upload Successful", f"Uploaded: {self.selected_file.get()}")

    def dashboard_screen(self):
        self.clear_content()
        dashboard_frame = tk.Frame(self.content_frame, bg="white")
        dashboard_frame.pack(fill=tk.BOTH, expand=True)
        dashboard_label = tk.Label(dashboard_frame, text="Dashboard", font=("Helvetica", 18), bg="white", fg="#cbcbcb")
        dashboard_label.pack(pady=20)

        # Add 3 tiles for summary statistics
        stats_frame = tk.Frame(dashboard_frame, bg="white")
        stats_frame.pack(pady=10)
        stats = [("Total Threats", "15"), ("Critical", "5"), ("Moderate", "7"), ("Low", "3")]
        for stat in stats:
            tile = tk.Frame(stats_frame, bg="#2e2e2e", width=150, height=100)
            tile.pack(side=tk.LEFT, padx=10)
            tile.pack_propagate(False)
            stat_label = tk.Label(tile, text=stat[0], font=("Helvetica", 14), bg=tile['bg'], fg="#cbcbcb")
            stat_label.pack(pady=(10, 5))
            value_label = tk.Label(tile, text=stat[1], font=("Helvetica", 24, "bold"), bg=tile['bg'], fg="#ff8800")
            value_label.pack()
        
        # Add donut chart
        chart_frame = tk.Frame(dashboard_frame, bg="white")
        chart_frame.pack(pady=20)
        chart_label = tk.Label(chart_frame, text="Threat Distribution Chart (Placeholder)", font=("Helvetica", 14), bg="white", fg="#cbcbcb")
        chart_label.pack()
        canvas = tk.Canvas(chart_frame, width=300, height=300, bg="#2e2e2e")
        canvas.pack(pady=10)
        data = [5, 7, 3]  # Example data for Critical, Moderate, Low
        total = sum(data)
        start_angle = 90
        colors = ["#ff0000", "#ff8c00", "#ffd700"]
        for i, value in enumerate(data):
            extent = -(value / total) * 360
            canvas.create_arc(10, 10, 290, 290, start=start_angle, extent=extent, fill=colors[i], outline="")
            start_angle += extent
        canvas.create_oval(100, 100, 200, 200, fill=canvas['bg'], outline="")

        # Add threat summary table with File Name and Date fields
        summary_frame = tk.Frame(dashboard_frame, bg="white")
        summary_frame.pack(pady=10)
        summary_label = tk.Label(summary_frame, text="Threat Summary Table (Placeholder)", font=("Helvetica", 14), bg="white", fg="#cbcbcb")
        summary_label.pack()
        table = tk.Frame(summary_frame, bg="#2e2e2e")
        table.pack(pady=10)
        headers = ["File Name", "Date"]
        for i, header in enumerate(headers):
            header_label = tk.Label(table, text=header, font=("Helvetica", 12, "bold"), bg=table['bg'], fg="#ff8800", borderwidth=1, relief="solid", width=30)
            header_label.grid(row=0, column=i)
        

    def results_screen(self):
        self.clear_content()
        results_frame = tk.Frame(self.content_frame, bg="white")
        results_frame.pack(fill=tk.BOTH, expand=True)
        results_label = tk.Label(results_frame, text="Results", font=("Helvetica", 18), bg="white", fg="#cbcbcb")
        results_label.pack(pady=20)
    

    def configuration_screen(self):
        self.clear_content()
        config_frame = tk.Frame(self.content_frame, bg="white")
        config_frame.pack(fill=tk.BOTH, expand=True)
        config_label = tk.Label(config_frame, text="Configuration", font=("Helvetica", 18), bg="white", fg="#cbcbcb")
        config_label.pack(pady=20)


# create the main application window
if __name__ == "__main__":
    root = tk.Tk()
    app = UI(root)
    root.mainloop()