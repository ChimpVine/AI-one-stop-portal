import gspread
from google.oauth2.service_account import Credentials
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import os
import json
from datetime import datetime
import requests
import base64
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from dotenv import load_dotenv
from Utils.Combined.article import generate_article
from Utils.Combined.quiz import generate_quiz

# Load environment variables
load_dotenv()

@login_required
def articlequiz(request):
    return render(request, 'articlequiz.html')

def encode_auth(username, password):
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode()).decode()

def combine_article_and_quiz(subject, grade, difficulty, topic, language):
    """
    Generate and combine article and quiz data into a single JSON object.
    """
    try:
        # Generate article
        article_data = generate_article(subject, grade, difficulty, topic, language)
        if not article_data:
            print(f"❌ Failed to generate article for {subject} {topic}")
            return None

        # Generate quiz
        quiz_data = generate_quiz(subject, grade, difficulty, topic, language)
        if not quiz_data:
            print(f"Failed to generate quiz for {subject} {topic}")
            return None

        # Combine the data
        combined_data = {
            "Subject": subject,
            "Grade": grade,
            "Difficulty": difficulty,
            "Topic": topic,
            "Image": "https://site.chimpvine.com/wp-content/uploads/2024/06/quiz-thumbnail.png",
            "questions": quiz_data.get("questions", []),
            "article": article_data.get("article", {}),
            "access_type": "login"
        }

        return combined_data
    except Exception as e:
        print(f"Error combining article and quiz: {str(e)}")
        return None
@csrf_exempt
def process_quiz_article(request):
    # Get the JSON data from the request body
    try:
        data = json.loads(request.body)
        website = data.get('website', '').strip().lower()
        google_sheet_id = data.get('google_sheet_id', '')
    except:
        # Fallback to POST parameters if not JSON
        website = request.POST.get('website', '').strip().lower()
        google_sheet_id = request.POST.get('google_sheet_id', '')

    # Use the provided Google Sheet ID if available, otherwise use the default
    SPREADSHEET_ID = google_sheet_id if google_sheet_id else "1LSQ2PW8xVrLdYPgK66sJp3inHwzoOfDEhN0iMR2DN4E"
    
    # Google Service Account JSON key file path
    SERVICE_ACCOUNT_FILE = "credentials.json"
    worksheet_name = "Sheet1"

    try:
        # Authenticate with Google Sheets
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[
            "https://www.googleapis.com/auth/spreadsheets"
        ])
        sheet_client = gspread.authorize(creds)
        sheet = sheet_client.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)

        # Create folders for saving JSON files
        output_folder = "generated_content"
        os.makedirs(output_folder, exist_ok=True)

        # Read spreadsheet data
        rows = sheet.get_all_values()
        headers = rows[0]
        data_rows = rows[1:]

        # Ensure required columns exist
        required_columns = ["Subject", "Grade", "Difficulty", "Topic", "Language", "Status"]
        col_index = {name: headers.index(name) for name in required_columns if name in headers}

        # Encode Authorization Header for dev site
        username = "sanjitasendang12"
        password = "2fFj fWLX vY1X T6ZG SFDf 8chG"
        auth_header = encode_auth(username, password)

        # Process counter for tracking success
        processed_count = 0
        skipped_count = 0

        # Process each row
        for i, row in enumerate(data_rows):
            # Skip already processed rows
            if row[col_index["Status"]].strip().lower() == "successful":
                skipped_count += 1
                continue

            # Extract necessary values
            subject = row[col_index["Subject"]]
            grade = row[col_index["Grade"]]
            difficulty = row[col_index["Difficulty"]]
            topic = row[col_index["Topic"]]
            language = row[col_index["Language"]] if "Language" in col_index else "English"
            
            print(f"Processing row {i + 2} - Subject: {subject}, Grade: {grade}, Difficulty: {difficulty}, Topic: {topic}")

            # Ensure values are valid before proceeding
            if not all([subject, grade, difficulty, topic]):
                print(f"⚠️ Skipping row {i + 2} due to missing values: {row}")
                skipped_count += 1
                continue

            # Generate combined data
            combined_data = combine_article_and_quiz(subject, grade, difficulty, topic, language)
            
            if combined_data:
                # Check the website value (case insensitive)
                if "dev" in website.lower() or "/dev314159" in website.lower():
                    url = "https://site.chimpvine.com/dev314159/wp-json/custom/v1/create-article-quiz"
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Basic {auth_header}'
                    }

                    # Send the POST request to the API
                    response = requests.post(url, json=combined_data, headers=headers, verify=False)
                    print(response.text)

                elif "chimpvine.com" in website.lower():
                    # Use environment variables for chimpvine.com
                    wp_username = os.getenv('WP_USERNAME_CHIMPVINE')
                    wp_password = os.getenv('WP_PASSWORD_CHIMPVINE')

                    auth_header = encode_auth(wp_username, wp_password)

                    url = "https://chimpvine.com/wp-json/wp/v2/article"
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Basic {auth_header}'
                    }

                    # Send the POST request to the API for chimpvine.com
                    response = requests.post(url, json=combined_data, headers=headers, verify=False)
                    print(response.text)
                else:
                    print(f"Skipping row {i + 2} because the website '{website}' is not recognized.")
                    skipped_count += 1
                    continue

                # Create timestamp for filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Save JSON locally
                file_name = f"{subject}_{topic}_{timestamp}.json"
                file_path = os.path.join(output_folder, file_name)

                with open(file_path, "w", encoding="utf-8") as json_file:
                    json.dump(combined_data, json_file, indent=2, ensure_ascii=False)

                # Update status in the spreadsheet
                sheet.update_cell(i + 2, col_index["Status"] + 1, "Successful")
                print(f"Processed row {i + 2} and saved: {file_name}")
                processed_count += 1
            else:
                print(f"Failed to generate content for row {i + 2}")
                skipped_count += 1

        result_message = f"Processing complete: {processed_count} items processed successfully, {skipped_count} items skipped."
        return JsonResponse({"result": result_message}, status=200)

    except Exception as e:
        error_message = f"Error in main execution: {str(e)}"
        print(error_message)
        return JsonResponse({"error": error_message}, status=500)