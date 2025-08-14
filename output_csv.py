import csv, os
from datetime import datetime

"""
-- The writeToCSV() function writes a given list of lists to a CSV file.
-- The first row is treated as the header.
-- The output file is saved in the user's Downloads folder with a datetimestamp
-- -- this is to ensure that each output file is unique and does not overwrite previous files.
-- The output file is named "output_<timestamp>.csv".
"""

# The example data has the columns: Finding, Risk, Explanation, Recommendation
# These were detailed by the Project Owner in the Meet & Greet session
exampleOutputData = [
    ["Finding", "Risk Rating", "Risk Explanation", "Recommendation"],
    ["Port 23 - Telnet", "High", "Telnet is an insecure protocol that transmits data in plaintext, making it vulnerable to interception.", "Disable Telnet and use SSH for secure remote access."],
    ["Port 80 - HTTP", "Medium", "HTTP traffic is not encrypted, which can expose sensitive data to eavesdropping.", "Use HTTPS to encrypt web traffic."],
    ["Port 443 - HTTPS", "Low", "HTTPS is generally secure, but misconfigurations can lead to vulnerabilities.", "Ensure proper SSL/TLS configurations and use strong ciphers."],
    ["Port 3306 - MySQL", "High", "MySQL databases can be vulnerable to SQL injection attacks if not properly secured.", "Implement input validation and use prepared statements to prevent SQL injection."]
]

# Get the user's Downloads folder and create a timestamped output file path
downloadsFolder = os.path.join(os.path.expanduser("~"), "Downloads")
# Create a timestamp for the output file to ensure uniqueness
datetimeStamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# Construct the output file path
outputPath = os.path.join(downloadsFolder, f"output_{datetimeStamp}.csv")

def writeToCSV(data, fileName):
    with open(fileName, mode='w', newline='') as file:
        writer = csv.writer(file)
        for row in data:
            writer.writerow(row)

file = exampleOutputData

writeToCSV(file, outputPath)