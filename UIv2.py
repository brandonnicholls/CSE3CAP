import tkinter as tk
import tkinter.filedialog as fd
from tkinter import messagebox
from tkinter import simpledialog
import math
import os
import csv
from tkinter import ttk
import json
import sys
import runpy
import importlib
import io
import contextlib
from importlib import import_module

class UI:
    def __init__(self, root):
        self.root = root
        root.title("FireFind")
        self.icon_image = tk.PhotoImage(file="FireFind.ico")
        root.iconphoto(False, self.icon_image)
        root.geometry("1920x1080")
        root.configure(bg="white")
        root.resizable(True, True)
        self.active_nav = None
        self.active_command = None
        self.nav_buttons = {}
        self.history = []                # <-- add navigation history stack
        self.last_file_name = None       # <-- store last uploaded file name

        # icons will be created after widgets exist (see create_widgets)
        self.icon_high = None
        self.icon_medium = None
        self.icon_low = None

        # Settings state (in-memory)
        self.high_risk_ports = [
            {"port": 22, "enabled": tk.BooleanVar(value=True)},
            {"port": 445, "enabled": tk.BooleanVar(value=True)},
        ]
        self.flag_allow_any = tk.BooleanVar(value=True)
        self.flag_broad_source = tk.BooleanVar(value=True)

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
        self.back_btn = back_btn
        self.back_btn.config(command=self.go_back)   # bind handler
        self.update_back_button_state()              # set initial state

        # Content Frame
        self.content_frame = tk.Frame(self.root, bg="white")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.content_frame.pack_propagate(False)

        # create small colored circle icons for severity (now that content_frame exists)
        def _make_circle(color, size=14):
            img = tk.PhotoImage(width=size, height=size)
            bg = self.content_frame.cget("bg") or "white"
            r = (size // 2) - 1
            cx = size / 2 - 0.5
            cy = size / 2 - 0.5
            for y in range(size):
                row = []
                for x in range(size):
                    dx = x - cx
                    dy = y - cy
                    if dx*dx + dy*dy <= r*r:
                        row.append(color)
                    else:
                        row.append(bg)
                img.put("{" + " ".join(row) + "}", to=(0, y))
            return img

        self.icon_high = _make_circle("#dc2626")
        self.icon_medium = _make_circle("#f59e42")
        self.icon_low = _make_circle("#a3b83b")

        # Set default page
        self.on_nav_click("Dashboard", self.dashboard_screen)

    def on_nav_click(self, name, command):
        # preserve previous page on navigation and navigate to new
        self.navigate(name, command, push=True)

    def navigate(self, name, command, push=True):
        # push current page to history if requested
        if push and self.active_command and name != self.active_nav:
            self.history.append((self.active_nav, self.active_command))
        # set active
        self.active_nav = name
        self.active_command = command
        # update sidebar highlight
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.config(bg="#e6f0ff", fg="#3390ff")
            else:
                btn.config(bg="#f5f5f5", fg="#444444")
        # call the page function
        try:
            command()
        finally:
            self.update_back_button_state()

    def go_back(self):
        if not self.history:
            return
        name, command = self.history.pop()
        # navigate back without pushing the popped page onto history again
        self.navigate(name, command, push=False)

    def update_back_button_state(self):
        # disable back when history is empty
        try:
            if getattr(self, "back_btn", None):
                self.back_btn.config(state=(tk.NORMAL if self.history else tk.DISABLED))
        except Exception:
            pass

    def clear_content(self):
        # Clear all widgets in the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def upload_screen(self):
        self.clear_content()
        file_frame = tk.Frame(self.content_frame, bg="white")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Centered content block
        content = tk.Frame(file_frame, bg="white")
        content.pack(anchor="center")   # <-- centers the whole block

        # Title
        title = tk.Label(content, text="Upload Firewall Rules", font=("Helvetica", 16, "bold"), bg="white", anchor="w")
        title.pack(anchor="w", pady=(0, 15))

        # Upload a file section
        upload_section = tk.Frame(content, bg="white")
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
            file_path = fd.askopenfilename(filetypes=[("CSV/Excel files", "*.csv *xlsx")])
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
        vendors_label = tk.Label(content, text="Supported Vendors", font=("Helvetica", 12, "bold"), bg="white")
        vendors_label.pack(anchor="w", pady=(20, 0))

        vendors = ["Fortinet", "Sophos", "Barracuda", "Checkpoint", "WatchGuard"]
        for vendor in vendors:
            tk.Label(content, text=vendor, font=("Helvetica", 10), bg="white").pack(anchor="w")

        # File Format
        format_label = tk.Label(content, text="File Format", font=("Helvetica", 12, "bold"), bg="white")
        format_label.pack(anchor="w", pady=(20, 0))

        tk.Label(content, text="Accepted formats: CSV, XLSX", font=("Helvetica", 10), bg="white").pack(anchor="w")
        tk.Label(content, text="File size limit: 10 MB", font=("Helvetica", 10), bg="white").pack(anchor="w")

    def upload_file(self):
        """Upload file logic"""
        if not self.selected_file.get():
            messagebox.showwarning("No file", "Please choose a file before uploading.")
        else:
            file_path = self.selected_file.get()
            try:
                file_size = os.path.getsize(file_path)  # size in bytes
                max_size = 10 * 1024 * 1024  # 10 MB

                if file_size > max_size:
                    messagebox.showerror(
                        "File Too Large",
                        "The selected file exceeds the 10 MB size limit. Please choose a smaller file."
                    )
                    return
                # Call firefind.one normalizer CLI
                script_dir = os.path.dirname(os.path.abspath(__file__))
                results_dir = os.path.join(script_dir, "results")

                rc, out, err = run_module_in_process("firefind.one", [file_path, "--auto", "--out", results_dir, "--json-v01"], script_dir)
                print("firefind.one rc:", rc)
                print(out)
                print(err)
                if rc == 0:
                    # proceed same as before: find json_path and run risk engine (either in-process or run_module_in_process)
                    base_name = os.path.basename(file_path)
                    name, _ = os.path.splitext(base_name)
                    self.last_file_name = base_name  # store for later use by results screen / export
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    results_dir = os.path.join(script_dir, "results")
                    json_path = os.path.join(results_dir, f"{name}.rules.v01.jsonl")
                    self.last_json_path = json_path  # store for later use by results screen / export
                    # check if JSON was created
                    if os.path.exists(json_path):
                        # Call risk engine CLI
                        rc, out, err = run_module_in_process("tests.run_engine_cli", [json_path], script_dir)
                        if rc == 0:
                            # when user clicks no, stay on upload screen
                            if messagebox.askyesno("View Results", "File processed successfully. Would you like to view the results?"):
                                self.navigate("Results", self.results_screen)
                        print("tests.run_engine_cli:", rc)
                        print(out)
                        print(err)
                    else:
                        messagebox.showwarning("Output Missing", f"File processed but output JSON {json_path} not found.")

                elif rc == 2:
                    messagebox.showerror("FireFind Error", "File type not supported. Please upload a CSV or XLSX file.")
                elif rc == 3:
                    messagebox.showerror("FireFind Error", "No rules parsed from the file. Please check the file format and content.")
                else:
                    messagebox.showerror("FireFind Error", err or out or "Unknown error.")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Could not process file.\n{str(e)}")

    def load_findings(self, path="results/findings.jsonl"):
        findings = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        findings.append(json.loads(line))
                    except Exception:
                        continue
        return findings

    def dashboard_screen(self):
        self.clear_content()
        self.results_data = self.load_findings("results/findings.jsonl")
        dashboard_frame = tk.Frame(self.content_frame, bg="white")
        dashboard_frame.pack(fill=tk.BOTH, expand=True)

        # Count of findings by severity from self.results_data
        if self.results_data:
            high_count = sum(1 for r in self.results_data if str(r.get("severity","")).lower() == "high")
            medium_count = sum(1 for r in self.results_data if str(r.get("severity","")).lower() == "medium")
            low_count = sum(1 for r in self.results_data if str(r.get("severity","")).lower() == "low")
            total_count = high_count + medium_count + low_count
        else:
            high_count = 0
            medium_count = 0
            low_count = 0
            total_count = 0

        # Tiles 
        tile_data = [
            ("High-Risk Rules", high_count, "#dc2626", "#991b1b"),
            ("Medium-Risk Rules", medium_count, "#f59e42", "#b45309"),
            ("Low-Risk Rules", low_count, "#a3b83b", "#64741a"),
            ("Total Rules", total_count, "#2563eb", "#1e40af")
        ]
        tiles_frame = tk.Frame(dashboard_frame, bg="white")
        tiles_frame.pack(pady=30)
        for label, value, color, border in tile_data:
            tile = tk.Frame(
                tiles_frame, bg=color, width=200, height=100, bd=0, highlightthickness=0
            )
            tile.pack(side=tk.LEFT, padx=20)
            tile.pack_propagate(False)
            # Rounded corners (simulate with padding)
            inner = tk.Frame(tile, bg=color)
            inner.pack(expand=True, fill="both", padx=8, pady=8)
            lbl = tk.Label(inner, text=label, font=("Arial", 13, "bold"), bg=color, fg="white")
            lbl.pack(anchor="n", padx=10, pady=(10, 0))
            val = tk.Label(inner, text=value, font=("Arial", 22, "bold"), bg=color, fg="white")
            val.pack(anchor="s", padx=10, pady=(0, 10))

        # Donut Chart (fit to 600x400 canvas)
        chart_frame = tk.Frame(dashboard_frame, bg="white")
        chart_frame.pack(pady=10)

        canvas_w, canvas_h = 600, 400
        canvas = tk.Canvas(chart_frame, width=canvas_w, height=canvas_h, bg="white", highlightthickness=0)
        canvas.pack()

        # Prepare chart data
        if self.results_data:
            high_count = sum(1 for r in self.results_data if str(r.get("severity", "")).strip().lower() == "high")
            medium_count = sum(1 for r in self.results_data if str(r.get("severity", "")).strip().lower() == "medium")
            low_count = sum(1 for r in self.results_data if str(r.get("severity", "")).strip().lower() == "low")
        else:
            high_count = medium_count = low_count = 0

        chart_data = [
            (high_count, "#dc2626", "High Risk"),
            (medium_count, "#f59e42", "Medium Risk"),
            (low_count, "#a3b83b", "Low Risk")
        ]

        total_count = sum(v for v, *_ in chart_data)

        if total_count == 0:
            canvas.create_text(canvas_w/2, canvas_h/2, text="No firewall data", fill="#666", font=("Arial", 14, "bold"))
        else:
            # layout using full canvas
            cx, cy = canvas_w / 2.0, canvas_h / 2.0
            margin = 24
            outer_r = min(canvas_w, canvas_h) / 2.0 - margin   # outer radius
            bbox = (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r)

            start = 90.0
            for value, color, label in chart_data:
                if value <= 0:
                    continue
                extent = (value / total_count) * 360.0
                if extent >= 360.0:
                    extent = 359.999
                canvas.create_arc(*bbox, start=start, extent=extent, fill=color, outline=color)
                # label placement along slice mid-angle
                mid_angle = start + extent / 2.0
                label_r = outer_r * 0.62
                lx = cx + label_r * math.cos(math.radians(-mid_angle))
                ly = cy + label_r * math.sin(math.radians(-mid_angle))
                start += extent

            # donut hole (center)
            hole_r = outer_r * 0.45
            hole_bbox = (cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r)
            canvas.create_oval(*hole_bbox, fill="white", outline="white")

        # Table
        table_frame = tk.Frame(dashboard_frame, bg="white")
        table_frame.pack(pady=20)
        # Headers
        tk.Label(table_frame, text="File Name", font=("Arial", 12, "bold"),
                bg="#bdbdbd", fg="white", width=30, anchor="w").grid(row=0, column=0, sticky="ew")
        tk.Label(table_frame, text="Date", font=("Arial", 12, "bold"),
                bg="#bdbdbd", fg="white", width=30, anchor="w").grid(row=0, column=1, sticky="ew")

        # Data rows
        for i in range(1, 4):
            tk.Label(table_frame, text="", font=("Arial", 11), bg="white",
                    width=30, anchor="w", relief="solid", bd=1).grid(row=i, column=0, sticky="ew")
            tk.Label(table_frame, text="", font=("Arial", 11), bg="white",
                    width=30, anchor="w", relief="solid", bd=1).grid(row=i, column=1, sticky="ew")


    def results_screen(self):
        self.clear_content()
        self.results_data = self.load_findings("results/findings.jsonl")
        results_frame = tk.Frame(self.content_frame, bg="white")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header: title + search + filters + export
        header = tk.Frame(results_frame, bg="white")
        header.pack(fill="x", pady=(0,10))

        tk.Label(header, text="Results", font=("Helvetica", 18, "bold"), bg="white").pack(side="left")

        controls = tk.Frame(header, bg="white")
        controls.pack(side="right")

        # Search box
        search_var = tk.StringVar()
        search_entry = tk.Entry(controls, textvariable=search_var, width=30)
        search_entry.pack(side="left", padx=(0,8))
        tk.Button(controls, text="Search", command=lambda: apply_filters()).pack(side="left", padx=(0,8))

        # Severity filter
        severity_var = tk.StringVar(value="All")
        tk.Label(controls, text="Severity:", bg="white").pack(side="left", padx=(8,4))
        severity_menu = ttk.Combobox(controls, textvariable=severity_var, values=["All", "High", "Medium", "Low"], width=8, state="readonly")
        severity_menu.pack(side="left")

        # Source / Destination filters (populated after data load)
        src_var = tk.StringVar(value="Any")
        dst_var = tk.StringVar(value="Any")
        tk.Label(controls, text="Source IP:", bg="white").pack(side="left", padx=(8,4))
        src_menu = ttk.Combobox(controls, textvariable=src_var, values=["Any"], width=12, state="readonly")
        src_menu.pack(side="left")
        tk.Label(controls, text="Destination IP:", bg="white").pack(side="left", padx=(8,4))
        dst_menu = ttk.Combobox(controls, textvariable=dst_var, values=["Any"], width=12, state="readonly")
        dst_menu.pack(side="left", padx=(0,8))

        # CSV export button
        def export_csv():
            file_name = self.last_file_name
            file_name = os.path.splitext(file_name)[0]
            print(file_name)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            try:
                # use last json path produced by upload flow
                if not getattr(self, "last_json_path", None):
                    messagebox.showwarning("No results", "No processed results available. Please upload and process a file first.")
                    return
                json_path = self.last_json_path
                if not os.path.exists(json_path):
                    messagebox.showwarning("Missing file", f"JSON file not found:\n{json_path}")
                    return

                # call export manager module in-process
                rc, out, err = run_module_in_process("tests.run_engine_cli", [json_path, "--csv"], script_dir)
                if rc == 0:
                    messagebox.showinfo("Export Complete", f"Results exported to {script_dir}\\results\\{file_name}.rules.v01.analysis.csv")
                if rc != 0:
                    raise RuntimeError(err or out)
            except Exception as ex:
                messagebox.showerror("Export error", str(ex))

        tk.Button(controls, text="Export CSV", bg="#2ea44f", fg="white", command=export_csv).pack(side="left")
        tk.Label(controls, text=" ", bg="white").pack(side="left", padx=(4,0))  # spacer

        # PDF export button
        def export_pdf():
            file_name = self.last_file_name
            script_dir = os.path.dirname(os.path.abspath(__file__))
            try:
                # use last json path produced by upload flow
                if not getattr(self, "last_json_path", None):
                    messagebox.showwarning("No results", "No processed results available. Please upload and process a file first.")
                    return
                findings_path = "results/findings.jsonl"
                if not os.path.exists(findings_path):
                    messagebox.showwarning("Missing file", f"Results file not found:\n{findings_path}")
                    return

                # call export manager module in-process
                rc, out, err = run_module_in_process("firefind.export_manager", [findings_path, "--out", f"results\\{file_name}.pdf"], script_dir)
                if rc == 0:
                    messagebox.showinfo("Export Complete", f"Report exported to {script_dir}\\results\\{file_name}.pdf")
                if rc != 0:
                    raise RuntimeError(err or out)
            except Exception as ex:
                messagebox.showerror("Export error", str(ex))

        tk.Button(controls, text="Export PDF", bg="#2ea44f", fg="white", command=export_pdf).pack(side="left")

        # Treeview
        # split service into protocol and ports columns
        cols = ("rule_id", "finding", "source", "destination", "protocol", "ports", "rationale")
        tree_frame = tk.Frame(results_frame, bg="white")
        tree_frame.pack(fill="both", expand=True)

        yscroll = tk.Scrollbar(tree_frame, orient="vertical")
        xscroll = tk.Scrollbar(tree_frame, orient="horizontal")
        # show the tree column (#0) so we can display an icon there
        tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.config(command=tree.yview)
        xscroll.config(command=tree.xview)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        # headings
        # use the tree column (#0) as the Severity column so we can show image + text together
        tree.heading("#0", text="Severity")
        tree.column("#0", width=120, anchor="center")

        tree.heading("rule_id", text="Rule ID")
        tree.heading("finding", text="Finding")
        tree.heading("source", text="Source IP")
        tree.heading("destination", text="Destination IP")
        tree.heading("protocol", text="Protocol")
        tree.heading("ports", text="Ports")
        tree.heading("rationale", text="Rationale")

        tree.column("rule_id", width=80, anchor="center")
        tree.column("finding", width=350, anchor="w")
        tree.column("source", width=140, anchor="w")
        tree.column("destination", width=140, anchor="w")
        tree.column("protocol", width=120, anchor="center")
        tree.column("ports", width=140, anchor="center")
        tree.column("rationale", width=200, anchor="w")

        # configure tags for coloring (keep text black by default)
        tree.tag_configure("normal", foreground="#000000")  # black text for all rows

        # helpers for filtering & populating
        def unique_ips(field):
            vals = sorted({r.get(field, "") for r in self.results_data})
            vals = ["Any"] + [v for v in vals if v]
            return vals

        # populate src/dst filter lists
        src_menu['values'] = unique_ips("src")
        dst_menu['values'] = unique_ips("dst")

        def filtered_data():
            q = search_var.get().strip().lower()
            sev = severity_var.get()
            s = src_var.get()
            d = dst_var.get()

            def keep(r):
                if sev != "All" and str(r.get("severity","")).lower() != sev.lower():
                    return False
                if s != "Any" and r.get("src","") != s:
                    return False
                if d != "Any" and r.get("dst","") != d:
                    return False
                if q:
                    combined = " ".join([str(r.get(k,"")) for k in ("id","finding","src","dst","port","rationale","severity")]).lower()
                    return q in combined
                return True

            return [r for r in self.results_data if keep(r)]

        def populate_tree(items):
            tree.delete(*tree.get_children())

            def format_service_parts(rec):
                """Return (protocol_display, ports_display) from record's services field.
                   - strip any stray braces/brackets from port strings
                   - convert ranges where from==to to a single port (e.g. 80)
                """
                def clean_port_token(tok):
                    s = str(tok).strip()
                    # remove surrounding braces/brackets/quotes if present
                    if s.startswith("{") and s.endswith("}"):
                        s = s[1:-1].strip()
                    if s.startswith("[") and s.endswith("]"):
                        s = s[1:-1].strip()
                    s = s.strip("\"' ")
                    return s

                proto_set = []
                ports_tokens = []

                services = rec.get("services") or rec.get("service") or rec.get("service_ports") or []
                if isinstance(services, dict):
                    services = [services]
                if not isinstance(services, (list, tuple)):
                    services = []

                for svc in services:
                    if isinstance(svc, str):
                        # string like "tcp/80" or "dhcp-request"
                        proto_set.append(svc)
                        continue
                    if not isinstance(svc, dict):
                        continue

                    proto = (svc.get("protocol") or svc.get("proto") or "").lower()
                    proto = proto if proto and proto != "any" else "any"

                    # handle explicit range keys
                    if "from" in svc and "to" in svc:
                        try:
                            f = int(svc.get("from"))
                            t = int(svc.get("to"))
                            if f == t:
                                ports_tokens.append(str(f))
                            else:
                                ports_tokens.append(f"{f}-{t}")
                        except Exception:
                            # fallback to string cleanup
                            ports_tokens.append(clean_port_token(f"{svc.get('from')}-{svc.get('to')}"))
                        proto_set.append(proto)
                        continue

                    ports = svc.get("ports")
                    if ports is None:
                        p = svc.get("port")
                        if p is not None:
                            ports = [p]

                    # normalize various port representations
                    if isinstance(ports, (list, tuple)):
                        if not ports:
                            ports_tokens.append("any")
                        else:
                            for p in ports:
                                if isinstance(p, dict) and "from" in p and "to" in p:
                                    try:
                                        f = int(p.get("from"))
                                        t = int(p.get("to"))
                                        ports_tokens.append(str(f) if f == t else f"{f}-{t}")
                                    except Exception:
                                        ports_tokens.append(clean_port_token(p))
                                else:
                                    ports_tokens.append(clean_port_token(p))
                    elif isinstance(ports, (int, str)):
                        ports_tokens.append(clean_port_token(ports))
                    else:
                        ports_tokens.append("any")

                    proto_set.append(proto)

                # deduplicate while preserving order
                proto_list = [p for p in dict.fromkeys(proto_set) if p]
                ports_list = [p for p in dict.fromkeys(ports_tokens) if p]

                proto_display = ", ".join(proto_list) if proto_list else ""
                ports_display = ", ".join(ports_list) if ports_list else ""

                # present 'any' nicely
                if not ports_display or ports_display == "any":
                    ports_display = "any"

                return proto_display, ports_display

            def join_addrs(val):
                if isinstance(val, (list, tuple)):
                    return ", ".join(str(x) for x in val)
                if isinstance(val, str):
                    # raw newline-separated values in raw.src/dst may exist; show as comma list
                    return ", ".join(line.strip() for line in val.splitlines() if line.strip())
                return ""

            for r in items:
                sev = str(r.get("severity", "")).lower()
                if sev == "high":
                    icon = self.icon_high
                    sev_text = "High"
                elif sev == "medium":
                    icon = self.icon_medium
                    sev_text = "Medium"
                elif sev == "low":
                    icon = self.icon_low
                    sev_text = "Low"
                else:
                    icon = None
                    sev_text = ""

                proto_display, ports_display = format_service_parts(r)

                src_display = join_addrs(r.get("src") or r.get("src_addrs") or r.get("raw", {}).get("src", ""))
                dst_display = join_addrs(r.get("dst") or r.get("dst_addrs") or r.get("raw", {}).get("dst", ""))

                tree.insert(
                    "", "end",
                    image=icon,
                    text=sev_text,
                    values=(
                        r.get("rule_id"),
                        r.get("name") or r.get("title") or r.get("raw", {}).get("rule_id") or "",
                        src_display,
                        dst_display,
                        proto_display,
                        ports_display,
                        r.get("reason") or r.get("rationale") or r.get("raw", {}).get("reason") or "",
                    ),
                    tags=("normal",)
                )

        def apply_filters():
            populate_tree(filtered_data())

        populate_tree(self.results_data)

        # show detail on double click
        def on_double(e):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            rid = vals[0]
            rec = next((x for x in self.results_data if str(x.get("id")) == str(rid)), None)
            if rec:
                txt = "\n".join([f"{k}: {v}" for k, v in rec.items()])
                messagebox.showinfo(f"Rule {rec.get('id')}", txt)

        tree.bind("<Double-1>", on_double)
    

    def configuration_screen(self):
        self.clear_content()
        config_frame = tk.Frame(self.content_frame, bg="white")
        config_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Title
        config_label = tk.Label(config_frame, text="Settings", font=("Helvetica", 22, "bold"), bg="white")
        config_label.pack(anchor="w", pady=(0, 10))

        # High-Risk Administrative Ports section
        ports_label = tk.Label(config_frame, text="High-Risk Administrative Ports", font=("Helvetica", 16, "bold"), bg="white")
        ports_label.pack(anchor="w", pady=(10, 6))

        ports_container = tk.Frame(config_frame, bg="white", bd=1, relief="groove")
        ports_container.pack(fill="x", padx=(0, 0), pady=(0, 10))

        # function to refresh port list UI
        def refresh_ports_ui():
            for w in ports_container.winfo_children():
                w.destroy()

            for idx, entry in enumerate(self.high_risk_ports):
                row = tk.Frame(ports_container, bg="white")
                row.pack(fill="x", padx=6, pady=6)

                # toggle (use Checkbutton)
                cb = tk.Checkbutton(row, variable=entry["enabled"], onvalue=True, offvalue=False, bg="white")
                cb.pack(side="left")

                lbl = tk.Label(row, text=str(entry["port"]), bg="white", font=("Arial", 12))
                lbl.pack(side="left", padx=(8, 0), pady=2)

                # spacer and delete button on right
                spacer = tk.Frame(row, bg="white")
                spacer.pack(side="left", expand=True, fill="x")

                del_btn = tk.Button(row, text="X", fg="black", bg="#f0f0f0", command=lambda i=idx: remove_port(i))
                del_btn.pack(side="right")

        def add_port():
            answer = simpledialog.askinteger("Add Port", "Enter port number (1-65535):", parent=self.root, minvalue=1, maxvalue=65535)
            if answer is None:
                return
            for e in self.high_risk_ports:
                if e["port"] == answer:
                    messagebox.showwarning("Exists", f"Port {answer} already in list.")
                    return
            self.high_risk_ports.append({"port": int(answer), "enabled": tk.BooleanVar(value=True)})
            refresh_ports_ui()

        def remove_port(index):
            if 0 <= index < len(self.high_risk_ports):
                del self.high_risk_ports[index]
                refresh_ports_ui()

        refresh_ports_ui()

        add_port_btn = tk.Button(ports_container, text="Add Port", bg="#4f7ef6", fg="white", command=add_port)
        add_port_btn.pack(anchor="e", padx=6, pady=(0, 6))

        # Risk Rule Configuration
        risk_label = tk.Label(config_frame, text="Risk Rule Configuration", font=("Helvetica", 16, "bold"), bg="white")
        risk_label.pack(anchor="w", pady=(10, 6))

        risk_container = tk.Frame(config_frame, bg="white", bd=1, relief="groove")
        risk_container.pack(fill="x", padx=(0, 0), pady=(0, 10))

        # Allow-Any rules row
        row1 = tk.Frame(risk_container, bg="white")
        row1.pack(fill="x", padx=6, pady=8)
        tk.Label(row1, text="Flag Allow-Any Rules", bg="white", font=("Arial", 12)).pack(side="left")
        tk.Checkbutton(row1, variable=self.flag_allow_any, bg="white").pack(side="right")

        # Broad source ranges row
        row2 = tk.Frame(risk_container, bg="white")
        row2.pack(fill="x", padx=6, pady=8)
        tk.Label(row2, text="Flag Broad Source Ranges", bg="white", font=("Arial", 12)).pack(side="left")
        tk.Checkbutton(row2, variable=self.flag_broad_source, bg="white").pack(side="right")

def run_module_in_process(module_name: str, argv: list[str], project_dir: str):
    """
    Run a module in-process as if `python -m module_name argv...`.
    Returns (returncode, stdout, stderr).
    """
    old_argv = sys.argv[:]
    old_cwd = os.getcwd()
    old_path = sys.path[:]
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    try:
        # ensure project root is importable
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        # set argv for the module
        sys.argv = [module_name] + list(argv)
        os.chdir(project_dir)
        # prefer calling module.main if available to allow nicer APIs
        try:
            mod = importlib.import_module(module_name)
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                if hasattr(mod, "main") and callable(mod.main):
                    # module should read sys.argv (we set it above). prefer calling main() with no args.
                    try:
                        mod.main()
                    except TypeError:
                        # fallback attempts if main expects an argv param
                        try:
                            mod.main(list(argv))
                        except TypeError:
                            try:
                                mod.main(*argv)
                            except Exception:
                                raise
                else:
                    # fallback: run module as __main__
                    runpy.run_module(module_name, run_name="__main__")
            return 0, stdout_buf.getvalue(), stderr_buf.getvalue()
        except Exception:
             # if import failed or main raised, try run_module to get traceback
            stderr_buf.write("Exception while running module:\n")
            import traceback
            traceback.print_exc(file=stderr_buf)
             # attempt runpy.run_module as last resort to execute module top-level
            try:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                     runpy.run_module(module_name, run_name="__main__")
                return 0, stdout_buf.getvalue(), stderr_buf.getvalue()
            except Exception:
                return 1, stdout_buf.getvalue(), stderr_buf.getvalue()
    finally:
        # restore environment
        sys.argv = old_argv
        os.chdir(old_cwd)
        sys.path = old_path

# create the main application window
if __name__ == "__main__":
    root = tk.Tk()
    app = UI(root)
    root.mainloop()