import os
"""
-- the fileParts() function reads a string of a file's name and returns a tuple with the 
-- first element as the file name and the second element as the extension
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

test = "example.csv"

fileName, fileExtension = fileParts(test)


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