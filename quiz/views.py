from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

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


# Initialize Google Sheets client
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

@login_required
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
        
import base64
import json 
import os 
import http.client       

def post_to_wordpress(content):
    print(f"Posting to chimpvine..")
    try:
        content['status']='draft'
        payload = json.dumps(content)
        WP_HEADERS = {
            'Content-Type': 'application/json'
        }
        WP_ENDPOINT = "/wp-json/custom/v1/create-quiz"
        WP_HOST = "site.chimpvine.com"
               # WP_HEADERS = {
        #     'Content-Type': 'application/json',
        #     'Authorization': 'Basic bmlyYWphbmFkbWluOmRRRVogU3VqWSBPYjFtIHRLVFcgR2JxRCBaeFd1'
        # }
        
        
        username=os.getenv('WP_USERNAME_CHIMPVINE')
        password=os.getenv('WP_PASSWORD_CHIMPVINE')
        
        if not username or not password:
            print("Error: Username or Password not found in environment variables.")
            return None    
        
        # Encode authentication using username and password
        auth_string = f"{username}:{password}"
        auth_encoded = base64.b64encode(auth_string.encode()).decode()
        WP_HEADERS['Authorization'] = f'Basic {auth_encoded}'

        # Send the request
        conn = http.client.HTTPSConnection(WP_HOST)
        conn.request("POST", WP_ENDPOINT, payload, WP_HEADERS)
        response = conn.getresponse()
        response_data = response.read().decode()

        print(f"Response: {response.status} {response.reason}")
        print(f"Response Data: {response_data}")

        return response.status, response_data

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
            status_code, response_data = post_to_wordpress(content)

            if status_code in [200, 201]:
                update_sheet(sheet, row_number, "Drafted successfully!", date, time, row_data.get("User", ""))
                created_contents.append(row_data.get("topic", ""))
            else:
                update_sheet(sheet, row_number, "Post Failed!", date, time)
                failed_contents.append(row_data.get("topic", ""))

                        # response_status = post_to_wordpress(content)

            # if response_status in [200, 201]:
            #     update_sheet(sheet, row_number, "Drafted successfully!", date, time, row_data.get("User", ""))
            #     created_contents.append(row_data.get("topic", ""))
            # else:
            #     update_sheet(sheet, row_number, "Post Failed!", date, time)
            #     failed_contents.append(row_data.get("topic", ""))
        else:
            update_sheet(sheet, row_number, "Content Generation Failed!", date, time)
            failed_contents.append(row_data.get("topic", ""))

    return f"Created: {len(created_contents)}, Failed: {len(failed_contents)}"

@login_required

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
