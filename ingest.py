import os
"""
-- The fileParts() function reads a string of a file's name and returns a tuple containing 
-- the file name and its extension.
-- It uses the os.path.splitext() method to split the file name into two parts:
-- the file name without the extension and the extension itself.
-- If the file name is empty or an error occurs, it returns None for both parts.
"""
global fileExtension, fileName

def fileParts(file):
    if not file:
        return None, None
    try:
        fileName, fileExtension = os.path.splitext(file)
        return fileName, fileExtension.lstrip('.')
    except Exception as e:
        print(f"Error: {e}")
        return None, None

file = "example.csv"

fileName, fileExtension = fileParts(file)


#TODO - Add logic to handle different file types:
if(fileExtension == "csv"):
    # Do something with CSV file
    print("Processing CSV file")
elif(fileExtension == "xlsx"):
    # Do something with XLSX file
    print("Processing XLSX file")
else:
    # Report a file type error
    print("Unsupported file type")