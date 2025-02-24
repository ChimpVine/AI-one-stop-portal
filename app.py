# import os
# import gspread
# from google.oauth2.service_account import Credentials
# from dotenv import load_dotenv
# from Utils.new import article_mathfun  # Assuming your function is in utils.new.py

# # Load environment variables
# load_dotenv()

# # Define the scope and credential file
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# CREDENTIALS_FILE = "credentials.json"  # Ensure this file is correct and authorized

# # Initialize Google Sheets client
# creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
# client = gspread.authorize(creds)

# # Define the sheet ID here
# sheet_id = "1LSQ2PW8xVrLdYPgK66sJp3inHwzoOfDEhN0iMR2DN4E"

# def process_sheets(sheet):
#     """Reads data from Google Sheets and generates articles based on input data."""
#     try:
#         # Get all records from the sheet
#         records = sheet.get_all_records()

#         # Find the index of the "Status" column (instead of "Generated")
#         headers = sheet.row_values(1)  # Assuming headers are in the first row
#         status_index = headers.index("Status") + 1  # gspread is 1-indexed

#         updates = []  # Collect changes to apply in a batch update

#         # Iterate over the records with row numbers
#         for row_number, record in enumerate(records, start=2):  # Start at row 2 to avoid the header row
#             subject = record.get("Subject")
#             grade = record.get("Grade")
#             difficulty = record.get("Difficulty")
#             topic = record.get("Topic")

#             # Generate article (check if article is being returned)
#             article = article_mathfun(subject, grade, difficulty, topic)

#             # Debug: Print the article or error message
#             if article:
#                 print("Article generated successfully!")
#             else:
#                 print("Failed to generate article.")
                
#             print(article)   

#             # Collect the result and store it
#             status = "yes" if article else "no"

#             # Correct range for the "Status" column
#             status_column = chr(64 + status_index)  # Convert index to column letter (e.g., 1 -> A)
#             updates.append({
#                 'range': f"{status_column}{row_number}",  # Correct range for updating the "Status" column
#                 'values': [[status]]  # Set status to "yes" or "no"
#             })

#             print(f"{'Article generated' if article else 'Failed to generate article'} for {subject} - {grade} - {difficulty} - {topic}")

#         # Batch update if there are changes
#         if updates:
#             sheet.batch_update(updates)
#             print("Batch update completed.")
#         else:
#             print("No updates needed.")

#     except Exception as e:
#         print(f"Error while processing sheets: {e}")

# # Open the Google Sheet by its key (spreadsheet ID) and process it
# try:
#     # Open the Google Sheet by its key (spreadsheet ID)
#     sheet = client.open_by_key(sheet_id).sheet1  # Use the correct sheet ID
#     process_sheets(sheet)
# except Exception as e:
#     print(f"Error opening Google Sheet: {e}")


import os
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from Utils.new import article_mathfun  # Assuming your function is in utils.new.py

# Load environment variables
load_dotenv()

# Define the scope and credential file
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "credentials.json"  # Ensure this file is correct and authorized

# Initialize Google Sheets client
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Drive API client
drive_service = build('drive', 'v3', credentials=creds)

# Define the folder ID where the files will be stored
FOLDER_ID = '1FUXWiAkl_2J1duxXhSvinARcHI0v_rMC'  # Replace with your actual folder ID
import io

def save_json_to_drive(data, file_name):
    """Generates JSON file in memory and uploads it to Google Drive."""
    try:
        # Convert data to JSON format in memory
        json_data = json.dumps(data)
        json_bytes = io.BytesIO(json_data.encode())  # Create a file-like object

        # Upload the file to Google Drive
        file_metadata = {
            'name': file_name,
            'parents': [FOLDER_ID],
            'mimeType': 'application/json'
        }
        media = MediaFileUpload(json_bytes, mimetype='application/json', resumable=True)

        # Upload file to Google Drive
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

        # Return the link to the file
        return file.get('webViewLink')

    except Exception as e:
        print(f"Error uploading to Drive: {e}")
        return None

def process_sheets(sheet):
    """Reads data from Google Sheets and generates articles and JSON files."""
    try:
        # Get all records from the sheet
        records = sheet.get_all_records()

        # Find the index of the "Status" column and "Google drive link"
        headers = sheet.row_values(1)
        status_index = headers.index("Status") + 1  # gspread is 1-indexed
        drive_link_index = headers.index("Google drive link") + 1

        updates = []  # Collect changes to apply in a batch update

        # Iterate over the records with row numbers
        for row_number, record in enumerate(records, start=2):  # Start at row 2 to avoid the header row
            subject = record.get("Subject")
            grade = record.get("Grade")
            difficulty = record.get("Difficulty")
            topic = record.get("Topic")

            # Generate article (check if article is being returned)
            article = article_mathfun(subject, grade, difficulty, topic)


            # Prepare data for JSON output (this is the structure you can adjust)
            json_data = {
                "article": article
                
            }

            # Save JSON to Google Drive
            if article:
                file_name = f"{subject}_{grade}_{difficulty}_{topic}.json"
                file_link = save_json_to_drive(json_data, file_name)
                status = "Successful"
            else:
                file_link = ""
                status = "Failed"

            # Correct range for the "Status" and "Google drive link" columns
            status_column = chr(64 + status_index)
            drive_link_column = chr(64 + drive_link_index)

            # Collect the result and store it
            updates.append({
                'range': f"{status_column}{row_number}",
                'values': [[status]]  # Set status to "yes" or "no"
            })
            updates.append({
                'range': f"{drive_link_column}{row_number}",
                'values': [[file_link]]  # Set the Google Drive link
            })

            print(f"{'Article generated' if article else 'Failed to generate article'} for {subject} - {grade} - {difficulty} - {topic}")

        # Batch update if there are changes
        if updates:
            sheet.batch_update(updates)
            print("Batch update completed.")
        else:
            print("No updates needed.")

    except Exception as e:
        print(f"Error while processing sheets: {e}")


# Open the Google Sheet by its key (spreadsheet ID)
sheet = client.open_by_key('1LSQ2PW8xVrLdYPgK66sJp3inHwzoOfDEhN0iMR2DN4E').sheet1
process_sheets(sheet)
