from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gspread.exceptions import SpreadsheetNotFound
import gspread
import json
import http.client
from datetime import datetime
from Utils.Chimpvine.article import article_chimpvine
from django.shortcuts import render, redirect
from Utils.Quiz.quiz import quiz_json





SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDENTIALS_FILE = "credentials.json"
WP_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic bmlyYWphbmFkbWluOmRRRVogU3VqWSBPYjFtIHRLVFcgR2JxRCBaeFd1'
}
WP_ENDPOINT = "/wp-json/custom/v1/create-quiz"
WP_HOST = "site.chimpvine.com"

# Initialize Google Sheets client
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)


def quiz(request):
    return render(request, 'quiz.html')



def update_sheet(sheet, row_number, status, date, time, user_name=""):
    try:
        status_col = sheet.find("Status").col
        date_col = sheet.find("Date").col
        time_col = sheet.find("Time").col
        user_col = sheet.find("User").col

        sheet.update_cell(row_number, status_col, status)
        sheet.update_cell(row_number, date_col, date)
        sheet.update_cell(row_number, time_col, time)

        if user_name:
            sheet.update_cell(row_number, user_col, user_name)
    except Exception as e:
        print(f"Error updating Google Sheet: {str(e)}")

def post_to_wordpress(content):
    try:
        payload = json.dumps(content)
        conn = http.client.HTTPSConnection(WP_HOST)
        conn.request("POST", WP_ENDPOINT, payload, WP_HEADERS)
        response = conn.getresponse()
        print(f"Response: {response.status}")
        return response.status
    except Exception as e:
        print(f"Error posting to WordPress: {str(e)}")
        return None

def process_sheet(sheet, generate_content_fn):
    all_rows = list(enumerate(sheet.get_all_records(), start=2))
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")

    created_contents, failed_contents = [], []

    for row_number, row_data in all_rows:
        if row_data.get("Status", "") == "Posted successfully!":
            continue

        content = generate_content_fn(row_data)

        if content:
            response_status = post_to_wordpress(content)

            if response_status in [200, 201]:
                update_sheet(sheet, row_number, "Posted successfully!", date, time, row_data.get("User", ""))
                created_contents.append(row_data.get("topic", ""))
            else:
                update_sheet(sheet, row_number, "Post Failed!", date, time)
                failed_contents.append(row_data.get("topic", ""))
        else:
            update_sheet(sheet, row_number, "Content Generation Failed!", date, time)
            failed_contents.append(row_data.get("topic", ""))

    return f"Created: {len(created_contents)}, Failed: {len(failed_contents)}"

@csrf_exempt

def submit_quiz(request):
    if request.method =='POST':            
        try:
            data = json.loads(request.body)
            google_sheet_ip = data.get('google_sheet_ip')

            if not google_sheet_ip:
                return JsonResponse({'error': 'Google Sheet ID is required.'}), 400

            workbook = client.open_by_key(google_sheet_ip)
            sheet = workbook.sheet1

            result = process_sheet(sheet, lambda row: quiz_json(
                row.get("topic", ""),
                row.get("subject", ""),
                row.get("number", ""),
                row.get("difficulty", ""),
                row.get("grade", ""),
                row.get("description", ""),
                row.get("image_url", "")
            ))

            return JsonResponse({'result': result}, status=200)

        except SpreadsheetNotFound:
            return JsonResponse({'error': 'Google Sheet not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
def home(request):
    return JsonResponse({"message": "Welcome to the Article Generator API!"})
