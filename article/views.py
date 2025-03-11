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
from user.models import CustomUser
from django.contrib import messages
from Utils.Chimpvine.article import article_chimpvine
from Utils.Dansonsolutions.article import article_Dansonsolutions
from Utils.Preppers.article import article_Preppers
from Utils.Visitnepal.article import article_Visitnepal
from Utils.Dansonconsultancy.article import article_Dansonconsultancy
from Utils.Mathfun.article import article_mathfun
from Utils.Mathtricksjr.article import article_mathtricksjr


from django.shortcuts import render, redirect

from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Access the values from the environment
chimpvine_username = os.getenv('WP_USERNAME_CHIMPVINE')
chimpvine_password = os.getenv('WP_PASSWORD_CHIMPVINE')

dansonsolutions_username = os.getenv('WP_USERNAME_DANSONSOLUTIONS')
dansonsolutions_password = os.getenv('WP_PASSWORD_DANSONSOLUTIONS')

preppers360_username = os.getenv('WP_USERNAME_PREPPERS360')
preppers360_password = os.getenv('WP_PASSWORD_PREPPERS360')

visitnepal_username = os.getenv('WP_USERNAME_VISITNEPAL')
visitnepal_password = os.getenv('WP_PASSWORD_VISITNEPAL')

dansonconsultancy_username = os.getenv('WP_USERNAME_DANSONCONSULTANCY')
dansonconsultancy_password = os.getenv('WP_PASSWORD_DANSONCONSULTANCY')

mathfun_username = os.getenv('WP_USERNAME_MATHFUN')
mathfun_password = os.getenv('WP_PASSWORD_MATHFUN')

mathtricksjr_username = os.getenv('WP_USERNAME_MATHTRICKSJr')
mathtricksjr_password = os.getenv('WP_PASSWORD_MATHTRICKSJr')



SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDENTIALS_FILE = "credentials.json"

# Initialize Google Sheets client
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

@login_required
def article(request):
    return render(request, 'article/article.html')
def update_sheet(sheet, row_number, status, date, time, email):
    try:
        status_col = sheet.find("Status").col
        date_col = sheet.find("Date").col
        time_col = sheet.find("Time").col
        email_col = sheet.find("User").col

        # Update status, date, time, and user
        sheet.update_cell(row_number, status_col, status)
        sheet.update_cell(row_number, date_col, date)
        sheet.update_cell(row_number, time_col, time)

        if email:
            sheet.update_cell(row_number, email_col, email)
            print(f"Updated User: {email}")

    except Exception as e:
        print(f"Error updating sheet: {str(e)}")

import base64
import json
import os
import http.client

def post_to_wordpress(content, website):
    print(f"Posting to {website}...")

    try:
        # Convert content to JSON and set status to draft
        content['status'] = 'draft'
        payload = json.dumps(content)
        
        # Define website configurations
        wp_sites = {
            'preppers360.com': "preppers360.com",
            'mathfun.com': "mathfun.us",  # Special case for mathfun.com
            'dansonsolutions.com': "dansonsolutions.com",
            'chimpvine.com': "site.chimpvine.com",
            'visitnepal360.com': "visitnepal360.com",
            'dansonconsultancy.com': "dansonconsultancy.com",
            'mathtricksjr.com': "mathtricksjr.com"
        }

        # Validate website
        if website not in wp_sites:
            print("Invalid or unsupported website")
            return None

        # Get host and endpoint based on website
        wp_host = wp_sites[website]
        wp_endpoint = "/wp-json/wp/v2/posts" if website != "chimpvine.com" else "/wp-json/wp/v2/article"

        # Initialize headers
        wp_headers = {
            'Content-Type': 'application/json'
        }

        # If the website is mathfun.com, use the custom header and cookie
        if website == "mathfun.com":
            wp_headers['Authorization'] = 'Basic c2hyZXlhOjVvMUMgRnRTWCBxMnJNIFlhRjEgWDh4ViBkUVAx'
            wp_headers['Cookie'] = 'nfdbrandname=hostgator'
        
        else:
            # For other websites, retrieve credentials from environment variables
            if website == "chimpvine.com":
                username = os.getenv('WP_USERNAME_CHIMPVINE')
                password = os.getenv('WP_PASSWORD_CHIMPVINE')
            elif website == "dansonsolutions.com":
                username = os.getenv('WP_USERNAME_DANSONSOLUTIONS')
                password = os.getenv('WP_PASSWORD_DANSONSOLUTIONS')
            elif website == "preppers360.com":
                username = os.getenv('WP_USERNAME_PREPPERS360')
                password = os.getenv('WP_PASSWORD_PREPPERS360')
            elif website == "visitnepal360.com":
                username = os.getenv('WP_USERNAME_VISITNEPAL')
                password = os.getenv('WP_PASSWORD_VISITNEPAL')
            elif website == "dansonconsultancy.com":
                username = os.getenv('WP_USERNAME_DANSONCONSULTANCY')
                password = os.getenv('WP_PASSWORD_DANSONCONSULTANCY')
            elif website == "mathtricksjr.com":
                username = os.getenv('WP_USERNAME_MATHTRICKSJr')
                password = os.getenv('WP_PASSWORD_MATHTRICKSJr')
            else:
                print("Invalid or unsupported website")
                return None

            # Encode authentication using username and password
            auth_string = f"{username}:{password}"
            auth_encoded = base64.b64encode(auth_string.encode()).decode()
            wp_headers['Authorization'] = f'Basic {auth_encoded}'

        # Send the request
        conn = http.client.HTTPSConnection(wp_host)
        conn.request("POST", wp_endpoint, payload, wp_headers)
        response = conn.getresponse()
        response_data = response.read().decode()

        print(f"Response: {response.status} {response.reason}")
        print(f"Response Data: {response_data}")

        return response.status, response_data

    except Exception as e:
        print(f"Error posting to WordPress: {str(e)}")
        return None

    
def process_sheet(sheet, generate_content_fn, website,email):
    all_rows = list(enumerate(sheet.get_all_records(), start=2))
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")
    created_contents, failed_contents = [], []

    for row_number, row_data in all_rows:
        if row_data.get("Status", "") == "Posted successfully!":
            continue

        content = generate_content_fn(row_data)
        print(content)


        if content:
            response_status, response_data = post_to_wordpress(content, website)
            print(f"Response Status: {response_status}, Response Data: {response_data}")

            if response_status in [200, 201]:
                update_sheet(sheet, row_number, "Drafted successfully!", date, time, email)
                created_contents.append(row_data.get("article_title", ""))
                print("Article posted successfully!")
            else:
                update_sheet(sheet, row_number, "Post Failed!", date, time, email)
                failed_contents.append(row_data.get("article_title", ""))
                print("Failed to post the article.")

        else:
            update_sheet(sheet, row_number, "Content Generation Failed!", date, time, email)
            failed_contents.append(row_data.get("article_title", ""))
            print("Content generation failed.")
            

    return f"Created: {len(created_contents)}, Failed: {len(failed_contents)}"


@login_required

@csrf_exempt
def generate_and_post_article(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            google_sheet_id = data.get('google_sheet_id')  # Fixed the key name
            website = data.get('website', '').strip().lower()  # Ensure consistency here
            email = data.get('email', request.user.email)

            if not google_sheet_id or not website:
                return JsonResponse({'error': 'Invalid input data.'}, status=400)

            print(f"Opening Google Sheet: {google_sheet_id}")
            workbook = client.open_by_key(google_sheet_id)  # Fixed the key name here as well
            sheet = workbook.sheet1

          
            if website == 'chimpvine.com':
                result = process_sheet(sheet, lambda row: article_chimpvine(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'dansonsolutions.com':
                result = process_sheet(sheet, lambda row: article_Dansonsolutions(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'preppers360.com':
                result = process_sheet(sheet, lambda row: article_Preppers(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'visitnepal360.com':
                result = process_sheet(sheet, lambda row: article_Visitnepal(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'dansonconsultancy.com':
                result = process_sheet(sheet, lambda row: article_Dansonconsultancy(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'mathfun.com':
                result = process_sheet(sheet, lambda row: article_mathfun(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
            elif website == 'mathtricksjr.com':
                result = process_sheet(sheet, lambda row: article_mathtricksjr(row.get("article_title", ""), row.get("seo_keywords", ""), row.get("language", "")), website, email)
                              
            else:
                return JsonResponse({'error': 'Invalid website selection.'}, status=400)


            return JsonResponse({'result': result}, status=200)

        

        except SpreadsheetNotFound:
            return JsonResponse({'error': 'Google Sheet not found.'}, status=404)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")  # Debugging
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)



