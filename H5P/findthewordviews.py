import os
import glob
import gspread
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Utils.H5P.find_the_word import find_the_word_generation
from django.shortcuts import render

# Output folder for storing H5P files
output_folder = 'H5P_FIND_THE_WORD'

# Google Sheets and Drive API credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# Authenticate and return the Google Sheets and Google Drive API services
def authenticate_google_services():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    
    # Google Sheets Service
    sheet_service = gspread.authorize(creds)

    # Google Drive Service
    drive_service = build('drive', 'v3', credentials=creds)

    return sheet_service, drive_service

# Read input data from the Google Sheet
def read_input_sheet(sheet_id, sheet_name):
    """Read the input data from the specified Google Sheet."""
    sheet_service, _ = authenticate_google_services()
    worksheet = sheet_service.open_by_key(sheet_id).worksheet(sheet_name)
    data = worksheet.get_all_records()  # Fetch all records as a list of dictionaries
    return data, worksheet

# Upload generated H5P file to Google Drive
def upload_to_drive(file_path, folder_id):
    """Upload the generated H5P file to Google Drive."""
    _, drive_service = authenticate_google_services()

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found for upload.")
        return None

    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='application/zip')

    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return f"https://drive.google.com/file/d/{file['id']}/view"

# Delete the H5P file from local storage
def delete_local_file(file_path):
    """Delete the H5P file from local storage after upload."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted local file: {file_path}")
        else:
            print(f"File {file_path} not found, skipping delete.")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

# Update the Google Sheet with the generated H5P link and status
def update_google_sheet(worksheet, row_idx, generated_link, status):
    """Update the Google Sheet with the generated H5P link and status."""
    try:
        worksheet.update_cell(row_idx, worksheet.find("Generated H5P").col, generated_link)
        worksheet.update_cell(row_idx, worksheet.find("Status").col, status)
    except Exception as e:
        print(f"Error updating sheet row {row_idx}: {e}")

# Find the most recently generated H5P file
def get_latest_h5p_file(output_folder, theme):
    """Find the most recent H5P file matching the theme."""
    search_pattern = f"{output_folder}/{theme.lower().replace(' ', '_')}*.h5p"
    h5p_files = glob.glob(search_pattern)

    if h5p_files:
        return max(h5p_files, key=os.path.getctime)  # Get the newest file
    return None

# View to render the find_the_word page
def find_the_word(request):
    return render(request, 'h5p/find_the_word.html')
@csrf_exempt
def process_word_search(request):
    """Django API endpoint to process Google Sheets data, generate word search, and upload files."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    try:
        # Parse the incoming JSON data
        data = json.loads(request.body)

        # Extract the parameters from the request body with the correct keys
        sheet_id = data.get('google_sheet_id')  # Adjusted this key name
        sheet_name = data.get('sheet_name')
        drive_folder_id = data.get('drive_folder_id')

        # Set default value for output_folder if not provided
        output_folder = data.get('output_folder', 'H5P_FIND_THE_WORD')

        # Log the received data for debugging
        print(f"Received data: {data}")
        print(f"Using output folder: {output_folder}")

        # Check for missing required parameters
        if not all([sheet_id, sheet_name, drive_folder_id]):
            return JsonResponse({'error': 'Missing required parameters (google_sheet_id, sheet_name, or drive_folder_id)'}, status=400)

        # Process each row in the Google Sheet
        data, worksheet = read_input_sheet(sheet_id, sheet_name)

        for idx, row in enumerate(data, start=2):  # Start from row 2 (header is in row 1)
            topic = row.get('Topic', '').strip()
            chapter = row.get('Chapter', '').strip()
            theme = row.get('Theme', '').strip()
            difficulty_level = row.get('Difficulty Level', '').strip()
            no_of_words = row.get('Number of Words', '')
            description = row.get('Description', '')
            status = row.get('Status', '').strip()  # Get the status column

            # Process only if status is empty or "Unsuccessful"
            if status and status.lower() != "unsuccessful":
                print(f"Row {idx}: Skipping as status is '{status}'.")
                continue

            if not topic or not chapter or not theme or not difficulty_level or not no_of_words:
                print(f"Row {idx}: Missing required fields. Skipping.")
                update_google_sheet(worksheet, idx, '', 'Failed - Missing Data')
                continue

            try:
                print(f"Processing row {idx}: Topic='{topic}', Chapter='{chapter}', Theme='{theme}', Difficulty='{difficulty_level}', Words={no_of_words}, Description='{description}'")

                # Generate word search puzzle
                generated_json = find_the_word_generation(topic, chapter, theme, difficulty_level, no_of_words, description)
                if not generated_json:
                    raise ValueError("Word search generation failed.")

                # Find the newly created H5P file
                h5p_file_path = get_latest_h5p_file(output_folder, theme)
                if not h5p_file_path:
                    raise FileNotFoundError(f"No H5P file found for theme: {theme}")

                # Upload to Google Drive
                drive_link = upload_to_drive(h5p_file_path, drive_folder_id)
                if not drive_link:
                    raise Exception("Google Drive upload failed.")

                # Delete local file
                delete_local_file(h5p_file_path)

                # Update the Google Sheet with success
                update_google_sheet(worksheet, idx, drive_link, 'Successful')
                print(f"Row {idx}: Successfully processed.")

            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                update_google_sheet(worksheet, idx, '', 'Unsuccessful')

        print("Google Sheet update completed.")
        return JsonResponse({'message': 'Processing completed!'}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

