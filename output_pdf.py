import os
from fpdf import FPDF
from datetime import datetime

"""
-- PDF generation with FPDF
-- The PDF will include a header with the FireFind icon and title, and a summary of threats.
-- The output file is saved in the user's Downloads folder with a datetimestamp
"""

class PDF(FPDF):
    def __init__(self, report_datetime, filename, threat_details, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_datetime = report_datetime
        self.filename = filename
        self.threat_details = threat_details


    def header(self):
        # FireFind icon
        self.image("FireFind.png", x=10, y=8, w=10, h=10)
        # FireFind logo text
        self.set_xy(18, 9)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(203, 203, 203)
        self.cell(10, 10, "FireFind")
        self.ln(10)
        # FireFind title centered at the top
        self.set_font("helvetica", "B", 20)
        self.set_text_color(0, 0, 0) # Reset to black
        self.cell(0, 10, "Firewall Threat Analysis", align="C")
        self.ln(10)
        # Datetime in top right
        self.set_font("helvetica", "", 10)
        self.set_xy(-60, 10)
        self.set_text_color(203, 203, 203)
        self.cell(50, 10, self.report_datetime, align="R")
        # Space after header
        self.ln(20)
        self.set_text_color(0, 0, 0) # Reset to black
        self.cell(0, 10, "Generated from: " + self.filename, align="L")
        self.ln(10)


    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


    def add_threat_summary(self):
        critical_count = 0
        moderate_count = 0
        low_count = 0
        
        # Count the number of threats in each category
        for category in self.threat_details:
            if(category[0] == "Critical"):
                for threat in category[1]:
                    critical_count += 1
            elif(category[0] == "Moderate"):
                for threat in category[1]:
                    moderate_count += 1
            elif(category[0] == "Low"):
                for threat in category[1]:
                    low_count += 1

        # Colours for the threat summary
        threat_summary = [
            ("Critical", "Moderate", "Low"),
            (critical_count, moderate_count, low_count),
            ((255, 0, 0), (255, 140, 0), (255, 215, 0)) # Red, Orange, Yellow
        ]

        # Set cell dimensions
        cell_width = 60
        cell_height = 20

        # Add title for the threat summary
        self.set_font("helvetica", "B", 20)
        self.set_text_color(0, 0, 0) # Reset to black
        self.cell(0, 10, "Threat Summary", align="L")
        self.ln(10)

        #TODO - add a table instead of just cells
        with self.table() as table:
            for row_data in threat_summary:
                row = table.row()
                for cell_data in row_data:
                    row.cell(cell_data)

        # Add a horizontal line
        self.set_draw_color(0, 0, 0)  # Black color for the line
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)


    def add_threat_details(self):
        # Add a title for the threat details
        self.set_font("helvetica", "B", 20)
        self.set_text_color(0, 0, 0) # Reset to black
        self.cell(0, 10, "Threat Details", align="L")
        self.ln(10)

        def write_threat_details(title, details, color):
            self.set_font("helvetica", "B", 20)
            self.set_text_color(*color)
            self.cell(0, 12, title)
            self.ln(10)
            self.set_text_color(0, 0, 0) # Reset to black
            number_items = len(details) > 1
            for idx, item in enumerate(details, 1):
                if number_items:
                    self.ln(2)
                    self.set_font("helvetica", "U", 14)
                    self.cell(0, 10, f"Threat {idx}:", align="L")
                    self.ln(7)

                self.set_font("helvetica", "", 12)
                self.cell(40, 10, "Port - Protocol:")
                self.set_font("helvetica", "", 12)
                self.cell(0, 10, item["Finding"])
                self.ln(5)

                self.set_font("helvetica", "", 12)
                self.cell(40, 10, "Risk Explanation:")
                self.set_font("helvetica", "", 12)
                self.cell(0, 10, item["Risk Explanation"])
                self.ln(5)

                self.set_font("helvetica", "", 12)
                self.cell(40, 10, "Recommendation:")
                self.set_font("helvetica", "", 12)
                self.cell(0, 10, item["Recommendation"])
                self.ln(5)
            self.ln(5)

        # Add details for each category
        for title, details, color in threat_details:
            write_threat_details(title, details, color)

    def generate_report(self, output_path):
        self.add_page(orientation="P", format="A4")
        self.add_threat_summary()
        self.add_threat_details()
        self.output(output_path)

#TODO - use a real file for testing
input_filename = "example.csv"

datetimeStamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Example threat details
threat_details = [
    ("Critical", [
        {
            "Finding": "Port 23 - Telnet",
            "Risk Explanation": "Telnet is insecure and should be disabled.",
            "Recommendation": "Disable Telnet and use SSH."
        },
        {
            "Finding": "Port 3306 - MySQL",
            "Risk Explanation": "MySQL exposed to the internet.",
            "Recommendation": "Restrict MySQL access to trusted hosts only."
        }
    ], (255, 0, 0)),
    ("Moderate", [
        {
            "Finding": "Port 80 - HTTP",
            "Risk Explanation": "HTTP traffic is not encrypted.",
            "Recommendation": "Use HTTPS to encrypt web traffic."
        }
    ], (255, 140, 0)),
    ("Low", [
        {
            "Finding": "Port 443 - HTTPS",
            "Risk Explanation": "Ensure proper SSL/TLS configurations.",
            "Recommendation": "Use strong ciphers and keep certificates updated."
        }
    ], (255, 215, 0)),
]

# Get the user's Downloads folder
downloadsFolder = os.path.join(os.path.expanduser("~"), "Downloads")
# Create a timestamp for the output file to ensure uniqueness
datetimeStampFile = datetime.now().strftime("%Y%m%d_%H%M%S")
# Construct the output file path
outputPath = os.path.join(downloadsFolder, f"FireFind_{datetimeStampFile}.pdf")

pdf = PDF(datetimeStamp, input_filename, threat_details)
pdf.set_auto_page_break(auto=True, margin=15)
# Set metadata for the PDF
pdf.set_title("FireFind - Firewall Threat Analysis")
pdf.set_author("Fire Auditors")
pdf.set_subject("Firewall Threat Report")
pdf.generate_report(outputPath)
print(f"PDF saved to: {outputPath}")