import tkinter as tk

class UI:
    def __init__(self, root):
        self.root = root
        root.title("FireFind")
        #TODO Set FireFind.ico icon to have transparent background
        self.icon_image = tk.PhotoImage(file="FireFind.ico")
        root.iconphoto(False, self.icon_image)
        root.geometry("1920x1080")
        root.configure(bg="#1e1e1e")
        root.resizable(False, False)
        self.create_widgets()


    def create_widgets(self):
        # Title Label with FireFind icon and horizontal orange stripe
        stripe = tk.Frame(root, bg="#ff8800", height=111, width=1920)
        stripe.pack(fill=tk.X, pady=(20, 0))
        #TODO Set FireFind.png icon to have transparent background
        title_image = tk.PhotoImage(file="FireFind.png")
        title_label = tk.Label(stripe, text="FireFind", font=("Helvetica", 24, "bold"), bg=stripe['bg'], fg="#000000")
        title_label.config(image=title_image, compound=tk.LEFT, padx=10, pady=10)
        title_label.image = title_image
        title_label.grid()

        # Navigation Frame
        nav_frame = tk.Frame(root, bg="#2e2e2e", width=200)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        nav_frame.pack_propagate(False)
        buttons = ["Upload", "Dashboard", "Results", "Configuration"]
        
        for btn in buttons:
            button = tk.Button(nav_frame, text=btn, font=("Helvetica", 14), bg="#3e3e3e", fg="#cbcbcb", bd=0, relief=tk.FLAT)
            button.pack(fill=tk.X, pady=5, padx=10)
            if btn == "Upload":
                button.config(command=self.upload_screen)
            elif btn == "Dashboard":
                button.config(command=self.dashboard_screen)
            elif btn == "Results":
                button.config(command=self.results_screen)
            elif btn == "Configuration":
                button.config(command=self.configuration_screen)

    # Content Frame
        self.content_frame = tk.Frame(root, bg="#1e1e1e")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.content_frame.pack_propagate(False)


    def clear_content(self):
        # Clear all widgets in the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()


    def upload_screen(self):
        # Navigate to file selection frame and clear the content frame
        self.clear_content()
        file_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        file_frame.pack(fill=tk.BOTH, expand=True)
        file_label = tk.Label(file_frame, text="Select a file to upload", font=("Helvetica", 18), bg="#1e1e1e", fg="#cbcbcb")
        file_label.pack(pady=20)
        upload_button = tk.Button(file_frame, text="Browse", font=("Helvetica", 14), bg="#ff8800", fg="#1e1e1e", bd=0, relief=tk.FLAT)
        upload_button.pack(pady=10)


    def dashboard_screen(self):
        # Navigate to dashboard frame and clear the content frame
        self.clear_content()
        dashboard_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        dashboard_frame.pack(fill=tk.BOTH, expand=True)
        dashboard_label = tk.Label(dashboard_frame, text="Dashboard", font=("Helvetica", 18), bg="#1e1e1e", fg="#cbcbcb")
        dashboard_label.pack(pady=20)

        # Add 3 tiles for summary statistics
        stats_frame = tk.Frame(dashboard_frame, bg="#1e1e1e")
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
        chart_frame = tk.Frame(dashboard_frame, bg="#1e1e1e")
        chart_frame.pack(pady=20)
        chart_label = tk.Label(chart_frame, text="Threat Distribution Chart (Placeholder)", font=("Helvetica", 14), bg="#1e1e1e", fg="#cbcbcb")
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
        summary_frame = tk.Frame(dashboard_frame, bg="#1e1e1e")
        summary_frame.pack(pady=10)
        summary_label = tk.Label(summary_frame, text="Threat Summary Table (Placeholder)", font=("Helvetica", 14), bg="#1e1e1e", fg="#cbcbcb")
        summary_label.pack()
        table = tk.Frame(summary_frame, bg="#2e2e2e")
        table.pack(pady=10)
        headers = ["File Name", "Date"]
        for i, header in enumerate(headers):
            header_label = tk.Label(table, text=header, font=("Helvetica", 12, "bold"), bg=table['bg'], fg="#ff8800", borderwidth=1, relief="solid", width=30)
            header_label.grid(row=0, column=i)
        

    def results_screen(self):
        # Navigate to results frame and clear the content frame
        self.clear_content()
        results_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        results_frame.pack(fill=tk.BOTH, expand=True)
        results_label = tk.Label(results_frame, text="Results", font=("Helvetica", 18), bg="#1e1e1e", fg="#cbcbcb")
        results_label.pack(pady=20)
    

    def configuration_screen(self):
        # Navigate to configuration frame and clear the content frame
        self.clear_content()
        config_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        config_frame.pack(fill=tk.BOTH, expand=True)
        config_label = tk.Label(config_frame, text="Configuration", font=("Helvetica", 18), bg="#1e1e1e", fg="#cbcbcb")
        config_label.pack(pady=20)


# create the main application window
if __name__ == "__main__":
    root = tk.Tk()
    app = UI(root)
    root.mainloop()