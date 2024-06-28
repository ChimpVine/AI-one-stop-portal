from gspread.exceptions import SpreadsheetNotFound  # Import specific exception
from googleapiclient.errors import HttpError
import io
import requests  # Import requests library for HTTP requests
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from forms import LoginForm, RegistrationForm, DepartmentAssignmentForm
from models import User, Department
from config import Config
from extensions import db, login
from flask_migrate import Migrate
import bcrypt
import gspread
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
import json
import http.client
from datetime import datetime
import os.path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os
from googleapiclient.http import MediaFileUpload
from openai import OpenAI
from pathlib import Path
import uuid  # For generating unique filenames
import os  # For directory creation
import requests
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login.init_app(app)
migrate = Migrate(app, db)
openAI_key = "oprn_api"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'error')
            # Redirect to login page after flashing error
            return redirect(url_for('login'))

        login_user(user)
        # Redirect to index or another page on successful login
        return redirect(url_for('index'))

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, full_name=form.full_name.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Staff member registered successfully!', 'success')
        return redirect(url_for('assign_departments'))

    return render_template('register.html', title='Register', form=form)

# @app.route('/assign_departments', methods=['GET', 'POST'])
# @login_required
# def assign_departments():
#     if not current_user.is_admin:
#         flash('You do not have permission to access this page.')
#         return redirect(url_for('index'))
#     form = DepartmentAssignmentForm()
#     form.user.choices = [(u.id, u.email)
#                          for u in User.query.filter_by(is_admin=False).all()]
#     form.departments.choices = [(d.id, d.name) for d in Department.query.all()]
#     if form.validate_on_submit():
#         user = User.query.get(form.user.data)
#         user.departments = Department.query.filter(
#             Department.id.in_(form.departments.data)).all()
#         db.session.commit()
#         flash('Departments assigned successfully!')
#         return redirect(url_for('index'))
#     return render_template('assign_departments.html', title='Assign Departments', form=form)


@app.route('/assign_departments', methods=['GET', 'POST'])
@login_required
def assign_departments():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('index'))

    form = DepartmentAssignmentForm()
    form.user.choices = [(u.id, u.email)
                         for u in User.query.filter_by(is_admin=False).all()]
    form.departments.choices = [(d.id, d.name) for d in Department.query.all()]

    if form.validate_on_submit():
        user = User.query.get(form.user.data)

        # Retrieve existing departments
        existing_departments = set(user.departments)

        # Get the newly selected departments
        new_departments = Department.query.filter(
            Department.id.in_(form.departments.data)).all()

        # Combine existing and new departments, avoiding duplicates
        combined_departments = existing_departments.union(new_departments)

        # Update user's departments
        user.departments = list(combined_departments)

        db.session.commit()
        flash('Departments assigned successfully!')
        return redirect(url_for('index'))

    return render_template('assign_departments.html', title='Assign Departments', form=form)


@app.route('/')
@app.route('/index')
@login_required
def index():
    if current_user.is_admin:
        return render_template('admin_dashboard.html')
    else:
        departments = current_user.departments
        return render_template('staff_dashboard.html',  current_user=current_user, departments=departments)


@app.route('/department/<department_name>')
@login_required
def department(department_name):
    try:
        # Check if the department exists in the database
        department = Department.query.filter_by(name=department_name).first()
        if department:
            # Render the corresponding department HTML template
            return render_template(f'{department_name.lower()}.html', department=department)
        else:
            # Redirect to the dashboard or handle the case where the department doesn't exist
            flash(f'Department "{department_name}" not found.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        # Log the exception for debugging purposes
        app.logger.error(f"Exception occurred: {str(e)}")
        flash('An error occurred. Please try again later.', 'error')
        return redirect(url_for('index'))


# Quiz part
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    "credentials.json", scopes=scopes)
client = gspread.authorize(creds)


def quiz_json(topic, subject, number, difficulty, grade, description, image_url):
    model = ChatOpenAI(
        model="gpt-4o",
        openai_api_key=openAI_key,
        temperature=0,
        max_tokens=4095
    )

    prompt_template = """Role: Act as a particular subject teacher and complete the given task below as shown in example.

    Task: Generate a quiz with 10 questions. The quiz should contain MCQ with 4 options and only one correct answer.

    Example:
    query = Generate quiz on topic 'LCM' for subject 'Math' . Generate '3' number of questions in 'Easy' difficulty"

    Output:

    --
    "Subject": "Mathematics",
    "Difficulty": "Easy",
    "Topic": "LCM",
    "Grade": "Level 5",
    "Image":"https://site.chimpvine.com/wp-content/uploads/2024/06/Analogy.jpg"
    "questions": [
        --
        "Type": "radio",
        "questionname":"What is the LCM of 8 and 12?",
        "answers": [24,16,20,28]
        ``,
        --
        "Type": "radio",
        "questionname":"What is the LCM of 5 and 7?",
        "answers": [35,25,42,30]
        ``,
        --
        "Type": "radio",
        "questionname":"What is the LCM of 9 and 15?",
        "answers": [45,24,36,50]
    ``
    ]
    ``

    Instruction:
    1. Always put the correct answer in the 1st option.
    2. Always generate output on JSON format.
    3. Never use single quote in the question.
    4. The output should not contain any headers. Eg. 'Output Format'
    5. Never repeat the same option.
    6. Generate questions and options maintaininf the grade standard.
    7. Never forget ',' in the context
    8. Each array in the answers should contain individual answer options.
    9.Separate each answer option within the answers arrays using commas.
    10.Remove any unnecessary spaces between the numbers.
    11. Ensure that there are no additional characters such as spaces, commas, or quotes within the numbers For example, if you have an answer array like this: ""answers": [3,580,246,791,3,580,246,790,3,580,246,792,3,580,246,793]
"You should modify it to look like this:""answers": [3580246791, 3580246790, 3580246792, 3580246793]
".

    {context}

    """

    prompt = PromptTemplate(
        input_variables=["context"],
        template=prompt_template,
    )

    chain = LLMChain(llm=model, prompt=prompt)

    query = f"Generate quiz on topic {topic} for subject {subject}. Generate {number} number of questions in {difficulty} mode. This quiz is made for grade {grade} students. The topic description is {description}. The image url is {image_url} "

    try:
        content = chain.invoke({'context': query})
        output = content['text'].replace('--', '{')
        output = output.replace('``', '}')
        output = output.replace("}`json", '')
        output = output.replace("}`", "")

        # Print the generated JSON content for debugging
        # print("Generated JSON content:", output)

        # Attempt to load JSON data
        print(output)
        quizzes = json.loads(output)
        print("Parsed JSON:", quizzes)

        main = json.dumps(quizzes)
        return main

    except json.JSONDecodeError as e:
        print("JSON decoding error:", e)
        return None
    except Exception as ex:
        print("Failed to generate content for:", description)
        print("Error:", ex)
        return None


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    google_sheet_ip = request.form['quizForm-name']
    print("Google Sheet IP from quizfun:", google_sheet_ip)

    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name
    else:
        first_name = ''
    print("Logged-in User's First Name:", first_name)
    created_contents = []
    failed_contents = []

    try:
        # Handle the data from mathForm
        sheet_id = google_sheet_ip
        workbook = client.open_by_key(sheet_id)
        sheet = workbook.sheet1

        date = datetime.now().strftime("%Y-%m-%d")
        time = datetime.now().strftime("%H:%M:%S")
        print("Current date:", date)
        print("Current time:", time)
        User_Name = f"{first_name}"
        print("user name", User_Name)

        # Retrieve all values from the sheet along with row numbers
        all_rows_with_row_numbers = list(
            enumerate(sheet.get_all_records(), start=2))  # Start from row 2

        # Iterate through each row in the sheet along with row numbers
        for row_number, row_data in all_rows_with_row_numbers:
            status = row_data.get("Status", "")

            # Skip the row if the status is already "Posted successfully!"
            if status == "Posted successfully!":
                continue

            topic = row_data.get("topic", "")
            subject = row_data.get("subject", "")
            number = row_data.get("number", "")
            difficulty = row_data.get("difficulty", "")
            grade = row_data.get("grade", "")
            description = row_data.get("description", "")
            image_url = row_data.get("image_url", "")
            Date = row_data.get("Date", "")
            Time = row_data.get("Time", "")
            User = row_data.get("User", "")

            print(f"topic: {topic}, subject: {subject}, number: {number}, difficulty: {difficulty}, grade: {grade},description: {description},Date: {Date}, Time: {Time}")

            # Generate content for the quiz
            content = quiz_json(topic, subject, number,
                                difficulty, grade, description, image_url)
            print(content)

            if content:
                print(f"Posted to WordPress: {topic}")

                # Prepare the payload
                wordpress_payload = content
                conn = http.client.HTTPSConnection("site.chimpvine.com")
                headers = {'Content-Type': 'application/json'}
                conn.request("POST", "/wp-json/custom/v1/create-quiz",
                             wordpress_payload, headers)
                res = conn.getresponse()

                print("Response Status Code:", res.status)
                data = res.read()
                print("Response Content:", data.decode("utf-8"))

                # Update status in Google Sheet
                if res.status == 200 or res.status == 201:
                    sheet.update_cell(row_number, sheet.find(
                        "Status").col, "Posted successfully!")
                    sheet.update_cell(row_number, sheet.find("Date").col, date)
                    sheet.update_cell(row_number, sheet.find("Time").col, time)
                    sheet.update_cell(
                        row_number, sheet.find("User").col, User_Name)
                    created_contents.append(topic)
                    flash('Quiz data posted successfully!', 'success')
                else:
                    sheet.update_cell(row_number, sheet.find(
                        "Status").col, "Post Failed!")
                    sheet.update_cell(row_number, sheet.find("Date").col, date)
                    sheet.update_cell(row_number, sheet.find("Time").col, time)
                    sheet.update_cell(
                        row_number, sheet.find("User").col, User_Name)
                    print(data.decode("utf-8"))
                    failed_contents.append(topic)
                    flash('Failed to post quiz data. Please try again.', 'error')
            else:
                print(f"Failed to generate content for: {topic}")
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Content Generation Failed!")

        else:
            print("No data found in the spreadsheet.")

    except gspread.exceptions.SpreadsheetNotFound as e:
        flash(f"Google Sheet not found: {str(e)}", 'error')
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')

    return render_template('quiz.html', created_contents=created_contents, failed_contents=failed_contents)


@app.route('/h5p_generation', methods=['GET', 'POST'])
@login_required
def h5p_generation():
    if request.method == 'POST':
        sheet_id = request.form.get('sheet_id')
        folder_id = request.form.get('folder_id')

        # Validate inputs
        if not sheet_id:
            flash("Please enter Google Sheet ID.", "warning")
        elif not folder_id:
            flash("Please enter Google Drive Folder ID.", "warning")
        else:
            try:
                # Process H5P generation
                process_data_h5p_generation(sheet_id, folder_id)
                flash("Processing initiated.", "success")
            except gspread.exceptions.SpreadsheetNotFound:
                flash("Invalid Google Sheet ID. Please check and try again.", "error")
            except HttpError as e:
                if e.resp.status == 404:
                    flash(
                        "Invalid Google Drive Folder ID. Please check and try again.", "error")
                else:
                    flash(f"An error occurred: {str(e)}", "error")
            except Exception as e:
                flash(f"An unexpected error occurred: {str(e)}", "error")

    return render_template('h5p_generation.html')


def process_data_h5p_generation(sheet_id, folder_id, output_folder='generated_json'):
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]

    # Initialize credentials
    creds = Credentials.from_service_account_file(
        "credentials.json", scopes=scopes)

    client = gspread.authorize(creds)
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")

    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Check if sheet_id is provided
    if sheet_id:
        workbook = client.open_by_key(sheet_id)
        sheet = workbook.sheet1

        # Retrieve all values from the sheet along with row numbers
        all_rows_with_row_numbers = list(
            enumerate(sheet.get_all_records(), start=2))  # Start from row 2

        # Initialize the language model
        llm = ChatOpenAI(
            model="gpt-3.5-turbo-1106",
            openai_api_key=openAI_key,
            temperature=0,
            max_tokens=4095
        )
        prompt_template = """Role: Act as a particular subject teacher and complete the given task below as shown in example.

Task: Generate a h5p content with questions.  Please watch the example below and generate the output on exact same Output Format.

Example:
Query : Generate 4 h5p questions of different type on the topic : 'countries' for subject 'English'. The questions are prepared for grade '6' and are in 'English'. The Difficulty level of questions should be 'medium'

Output Format :
[
"questions": ["<p>Nepal is a landlock country located between *China/India* and *India/China*.</p>\\n"],"title": "Fill in the Blanks",

"taskDescription":"Identify the correct places","textField": "*Kathmandu* is the capital of Nepal.\\n*Delhi* is the capital of India.\\n*Beijing* is the capital of China.","distractors": "*Tokyo*\\n","title": "Drag the Words",

"taskDescription":"Identify the correct geographical location","textField": "<p>The *Andes* is the longest mountain range, while the *Himalayas* is the highest.</p>\\n","title": "Mark the Words",

"question": "<p>What is the largest continent in the world?</p>\\n","title": "Single Choice Set","answers": ["<p>Asia</p>\\n", "<p>Europe</p>\\n"]
]

Instructions:
1. The answers for "Mark the Words" must be single word, without any white spaces.
2. Return the output in JSON arrayformat with fields. Always put questions/testField first.
3. The output should contain different types: "Mark the Words","Drag the Words","Fill in the Blanks".
4. Generate "Fill in the blanks" 3 times, "Drag the Words" 3 times "Mark the Words" 3 times,"Single Choice Set" 3 times .
5. The most important thing is that the correct answer for the question is enclosed inside * *. .
6. Always maintain the particular topic and output format while generating.
7. Never repeat the questions with same answer.
8. Return the output in JSON arrayformat with fields.
9. the key "textField" and "questions" should not be present together for a single h5p.
10."Fill in the Blanks" must always have "questions" key, "Drag the Words" must have "Distractor" key
11. Do not mention "Output format:"

{context}
"""
        prompt = PromptTemplate(
            input_variables=["context"], template=prompt_template)
        chain = LLMChain(llm=llm, prompt=prompt)

        try:
            # Process each row of the Google Sheet
            for row_number, row_data in all_rows_with_row_numbers:
                status = row_data.get("Status", "")

                # Skip the row if the status is already "Generated successfully!"
                if status == "Generated successfully!":
                    continue

                try:
                    # Retrieve row data and process it
                    topic = row_data.get("topic", "")
                    subject = row_data.get("subject", "")
                    difficulty = row_data.get("difficulty", "")
                    grade = row_data.get("grade", "")
                    language = row_data.get("language", "")
                    topic_nospace = topic.replace(" ", "_")

                    print("Processing row:", row_data)
                    print(
                        f"topic: {topic}, subject: {subject}, difficulty: {difficulty}, grade: {grade}, language: {language}")

                    query = f"""Generate 12 h5p questions of different type on the topic :{topic} for subject {subject}. The questions are prepared for grade {grade} and are in {language}. The Difficulty level of questions should be {difficulty}."""
                    quizz = chain.invoke({'context': query})
                    quizzes = json.loads(quizz['text'])

                    new_entries = quizzes
                    print("h5p generated", quizzes)

                    with open('content_.json', 'r') as file:
                        data = json.load(file)

                    for index, item in enumerate(data['content']):
                        for i in new_entries:
                            if i['title'] == item['content']['metadata']['title']:
                                if item['content']['metadata']['contentType'] == 'Drag the Words':
                                    item['content']['params']['textField'] = i['textField']
                                    item['content']['metadata']['title'] = i['title']
                                    item['content']['params']['taskDescription'] = i['taskDescription']
                                    item['content']['params']['distractors'] = i['distractors']

                                if item['content']['metadata']['contentType'] == 'Mark the Words':
                                    item['content']['params']['textField'] = i['textField']
                                    item['content']['metadata']['title'] = i['title']
                                    item['content']['params']['taskDescription'] = i['taskDescription']

                                if item['content']['metadata']['contentType'] == 'Fill in the Blanks':
                                    item['content']['params']['questions'] = i['questions']
                                    item['content']['metadata']['title'] = i['title']

                                if item['content']['metadata']['contentType'] == 'Single Choice Set':
                                    item['content']['params']['choices'][0]['question'] = i['question']
                                    item['content']['params']['choices'][0]['answers'] = i['answers']
                                    item['content']['metadata']['title'] = i['title']

                                new_entries.remove(i)
                                break

                    if not new_entries:
                        # Save the generated JSON to the specified folder
                        output_file_path = os.path.join(
                            output_folder, f'{topic_nospace}.json')
                        with open(output_file_path, 'w') as file:
                            json.dump(data, file, indent=4)

                        print(json.dumps(quizzes, indent=4))
                        sheet.update_cell(row_number, sheet.find(
                            "Status").col, "Generated successfully!")
                        sheet.update_cell(
                            row_number, sheet.find("Date").col, date)
                        sheet.update_cell(
                            row_number, sheet.find("Time").col, time)

                        # Upload the file to Google Drive
                        drive_service = build("drive", "v3", credentials=creds)
                        filename = f"{topic_nospace}.json"

                        file_metadata = {
                            "name": filename,
                            "parents": [folder_id]
                        }

                        media = MediaFileUpload(
                            output_file_path, mimetype="application/json")
                        uploaded_file = drive_service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields="id"
                        ).execute()

                        print(
                            f"File '{filename}' uploaded successfully. File ID: {uploaded_file.get('id')}")

                        file_link = f"https://drive.google.com/file/d/{uploaded_file.get('id')}/view?usp=sharing"
                        sheet.update_cell(
                            row_number, sheet.find("Link").col, file_link)

                except Exception as e:
                    # Log errors and update the sheet with error status
                    print("Error processing Google Sheet row:", str(e))
                    sheet.update_cell(row_number, sheet.find(
                        "Status").col, "Failed Generated!")
                    sheet.update_cell(row_number, sheet.find("Date").col, date)
                    sheet.update_cell(row_number, sheet.find("Time").col, time)

            print("All rows have been successfully processed.")

        except Exception as e:
            # Handle any general errors in processing the sheet
            print('Regenerate')
            print("Error processing Google Sheet row:", str(e))
            sheet.update_cell(row_number, sheet.find(
                "Status").col, "Failed Generated!")
            sheet.update_cell(row_number, sheet.find("Date").col, date)
            sheet.update_cell(row_number, sheet.find("Time").col, time)

# h5p_audio Part


@app.route('/h5p_audio', methods=['GET', 'POST'])
def data_processing():
    if request.method == 'POST':
        sheet_id = request.form['sheet_id']
        folder_id = request.form['folder_id']
        if sheet_id and folder_id:
            try:
                process_data(sheet_id, folder_id)
                flash("Audio generated successfully.", "success")
            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")
        else:
            flash(
                "Please enter both Google Sheet ID and Google Drive Folder ID.", "warning")
    return render_template('h5p_audio.html')


# Function to process the data


def process_data(sheet_id, folder_id):
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    OpenAI_key = openAI_key
    # Google Sheets credentials
    creds = Credentials.from_service_account_file(
        "credentials.json", scopes=scopes)
    client_sheets = gspread.authorize(creds)
    date = datetime.now().strftime("%Y-%m-%d")
    # Changed colon to hyphen for filename compatibility
    time = datetime.now().strftime("%H-%M-%S")

    # Language model setup
    llm = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        openai_api_key=OpenAI_key,
        temperature=0,
        max_tokens=4095
    )

    prompt_template = """You need to translate the given text based on the language provided.

    {context}
    """

    prompt = PromptTemplate(
        input_variables=["context"],
        template=prompt_template,
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    # Google Drive setup
    drive_service = build('drive', 'v3', credentials=creds)

    # Attempt to open the Google Sheet and process the data
    if sheet_id:
        try:
            workbook = client_sheets.open_by_key(sheet_id)
            sheet = workbook.sheet1
            # Retrieve all values from the sheet along with row numbers
            all_rows_with_row_numbers = list(
                enumerate(sheet.get_all_records(), start=2))  # Start from row 2

            success_count = 0  # Track the number of successful translations

            # Processing the data from the Google Sheet
            for row_number, row_data in all_rows_with_row_numbers:
                status = row_data.get("Status", "")

                # Skip the row if the status is already "Success!"
                if status == "Success!":
                    continue

                text = row_data.get("Text", "")
                language = row_data.get("language", "")

                print(f"Text: {text}, Language: {language}")

                if text and language:
                    # Generate a unique filename for the original text audio file
                    original_audio_filename = f"{date}_{time}_{uuid.uuid4()}_original.mp3"
                    audio_directory = "./audio"  # Adjust directory path
                    os.makedirs(
                        audio_directory, exist_ok=True)  # Create directory if it doesn't exist
                    original_audio_file_path = Path(
                        audio_directory) / original_audio_filename

                    # OpenAI client setup
                    client_openai = OpenAI(api_key=OpenAI_key)

                    # Generate speech for original text and save to file
                    response = client_openai.audio.speech.create(
                        model="tts-1",
                        voice="onyx",
                        input=text
                    )

                    response.stream_to_file(original_audio_file_path)
                    print(
                        f"Original audio file generated: {original_audio_file_path}")

                    # Upload the original audio file to Google Drive
                    original_file_metadata = {
                        "name": original_audio_filename,
                        "parents": [folder_id]  # Add the folder ID
                    }
                    original_media = MediaFileUpload(
                        original_audio_file_path, mimetype="audio/mpeg")
                    uploaded_original_file = drive_service.files().create(
                        body=original_file_metadata,
                        media_body=original_media,
                        fields="id"
                    ).execute()

                    # Print the file ID upon successful upload
                    print(
                        f"Original audio file '{original_audio_filename}' uploaded successfully. File ID: {uploaded_original_file.get('id')}")

                    # Generate file link for original audio
                    original_file_link = f"https://drive.google.com/file/d/{uploaded_original_file.get('id')}/view?usp=sharing"

                    # Update the link in the Google Sheet
                    sheet.update_cell(row_number, sheet.find(
                        "Original_Audio_Link").col, original_file_link)

                    # Proceed with translation
                    query = f"Translate the text: '{text}' into the language: '{language}'"
                    response = chain.run({'context': query})
                    translated_text = response.strip()
                    print(f"Translated Text: {translated_text}")

                    # Update the sheet with the translated text and status
                    sheet.update_cell(
                        row_number, sheet.find("Translated_Text").col, translated_text)
                    sheet.update_cell(
                        row_number, sheet.find("Status").col, "Success!")
                    sheet.update_cell(row_number, sheet.find("Date").col, date)
                    sheet.update_cell(row_number, sheet.find("Time").col, time)

                    success_count += 1  # Increment success count

                    # Generate a unique filename for the translated text audio file
                    translated_audio_filename = f"{date}_{time}_{uuid.uuid4()}_translated.mp3"
                    translated_audio_file_path = Path(
                        audio_directory) / translated_audio_filename

                    # Generate speech for translated text and save to file
                    response = client_openai.audio.speech.create(
                        model="tts-1",
                        voice="onyx",
                        input=translated_text
                    )

                    response.stream_to_file(translated_audio_file_path)
                    print(
                        f"Translated audio file generated: {translated_audio_file_path}")

                    # Upload the translated audio file to Google Drive
                    translated_file_metadata = {
                        "name": translated_audio_filename,
                        "parents": [folder_id]  # Add the folder ID
                    }
                    translated_media = MediaFileUpload(
                        translated_audio_file_path, mimetype="audio/mpeg")
                    uploaded_translated_file = drive_service.files().create(
                        body=translated_file_metadata,
                        media_body=translated_media,
                        fields="id"
                    ).execute()

                    # Print the file ID upon successful upload
                    print(
                        f"Translated audio file '{translated_audio_filename}' uploaded successfully. File ID: {uploaded_translated_file.get('id')}")

                    # Generate file link for translated audio
                    translated_file_link = f"https://drive.google.com/file/d/{uploaded_translated_file.get('id')}/view?usp=sharing"

                    # Update the link in the Google Sheet
                    sheet.update_cell(row_number, sheet.find(
                        "Translated_Audio_Link").col, translated_file_link)

            # Display success message after all translations
            print(
                f"All audio files generated and translations completed successfully! Total successful translations: {success_count}")

        except Exception as e:
            print(f"An error occurred: {e}")

            # Update the sheet with error status and current date/time
            sheet.update_cell(row_number, sheet.find("Status").col, "Failed!")


# This is the article Section


@app.route('/generate_and_post_article', methods=['POST'])
def generate_and_post_article():
    google_sheet_ip = request.form['google_sheet_ip']
    website = request.form['website']

    try:
        if website == 'Chimpvine.com':
            result = submit_Chimvine_form(google_sheet_ip)
        elif website == 'dansonsolutions.com':
            result = submit_DansonsolutionsForm(google_sheet_ip)
        elif website == 'Mathfun.com':
            result = submit_MathfunForm(google_sheet_ip)
        elif website == 'Mathjr.com':
            result = submit_math_form(google_sheet_ip)
        elif website == 'Chimpvinesiam.com':
            result = submit_Siam_form(google_sheet_ip)
        else:
            result = "Invalid website selection"

        flash(result, 'success')  # Flash success message

    except gspread.exceptions.SpreadsheetNotFound as e:
        flash(f"Google Sheet not found:", 'error')
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')

    return render_template('article.html')


def article_json(topic, key_word, language):
    model = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        openai_api_key=openAI_key,
        temperature=0,
        max_tokens=4095
    )

    prompt_template = """Role: Act as a content writer. You are about to write an article for an edtech site.
        Task: Generate an article for the requested topic. Generate the output as shown in the example below:

        Example :

        Input Query : Generate me an article for "GCF"

        Output:
        --
        "title": "Your Post Title",
        "content": " ",
        "acf": --
            "faq_quesion_1": "What is the importance of finding the Greatest Common Factor (GCF)?",
            "faq_answer_1": "Finding the Greatest Common Factor (GCF) is crucial as it helps simplify fractions and solve various mathematical problems efficiently.",
            "faq_quesion_2": "How does the GCF concept relate to factors?",
            "faq_answer_2": "The GCF is closely related to the concept of factors, as it represents the largest number that divides two or more numbers without leaving a remainder.",
            "faq_quesion_3": "Can the GCF be utilized to simplify fractions?",
            "faq_answer_3": "Yes, the GCF is instrumental in simplifying fractions by dividing both the numerator and denominator by their greatest common factor.",
            "faq_quesion_4": "What methods are available to determine the GCF of numbers?",
            "faq_answer_4": "Several methods exist to find the GCF, including prime factorization, listing factors, and using the Euclidean algorithm.",
            "faq_quesion_5": "How is the concept of GCF applied in real-life situations?",
            "faq_answer_5": "The concept of GCF finds practical applications in various real-life scenarios such as simplifying recipes, dividing resources equally, and optimizing resource allocation in business operations.",
            "articles_description": "<h3>What is GCF?:</h3> In the realm of mathematics, particularly when dealing with numbers and their relationships, the term Greatest Common Factor or GCF frequently arises. But what exactly does it entail? Let's embark on a journey into the realm of GCF and uncover its significance in solving mathematical quandaries.",
            "analogy_of_defination": "<h3>The GCF Explained:</h3> The Greatest Common Factor (GCF) of two or more numbers is the largest number that divides each of the given numbers without leaving a remainder. In simpler terms, it is the greatest number that is a factor of all the given numbers.",
            "articles_methods": "<h3>Finding the GCF: </h3>  There are several methods to determine the GCF of numbers. One approach involves listing the factors of each number and identifying the greatest common factor. Another method entails using prime factorization to find the GCF efficiently.",
            "examples": "<h3>Finding the GCF of 24 and 36:</h3> <strong> Step 1: </strong> List the factors of each number<br>Factors of 24: 1, 2, 3, 4, 6, 8, 12, 24<br>Factors of 36: 1, 2, 3, 4, 6, 9, 12, 18, 36<br><strong> Step 2: </strong> Identify the greatest common factor<br>The greatest common factor of 24 and 36 is 12.<br>Thus, the GCF of 24 and 36 is 12.",
            "example": "<strong> Summary::</strong> <br> This example demonstrates the method of finding the Greatest Common Factor (GCF) of two numbers, 24 and 36. Initially, the factors of each number are listed, followed by identifying the greatest common factor among them. By determining that the largest number shared by both sets of factors is 12, it is concluded that the GCF of 24 and 36 is 12. This process illustrates how the GCF is utilized to identify the largest divisor common to both numbers, facilitating calculations and problem-solving in various mathematical contexts. ",
            "article_tips_and_tricks": "<strong>1. Prime Factorization:</strong><br> <strong>Scenario:</strong> Finding the GCF of 18 and 24.<br> <strong>Tip: </strong>To find the GCF, list the factors of each number and identify the greatest common factor.<br> Calculation: Factors of 18: 1, 2, 3, 6, 9, 18 <br> Factors of 24: 1, 2, 3, 4, 6, 8, 12, 24 <br> Greatest common factor: 6<br> Answer: A) 6 cookies. <br><strong>2. The Garden Plot Puzzle</strong><br><strong>Scenario:</strong> Finding the GCF of 30 and 42.<br><strong>Tip: </strong>List the factors of each number and identify the greatest common factor to find the GCF.<br>Calculation: Factors of 30: 1, 2, 3, 5, 6, 10, 15, 30<br>Factors of 42: 1, 2, 3, 6, 7, 14, 21, 42<br>Greatest common factor: 6<br>Answer: B) 14 meters.<br><strong>3. The Classroom Bookshelf Challenge</strong><br><strong>Scenario:</strong> Finding the GCF of 36 and 48.<br><strong>Tip:</strong> Utilize the method of listing factors to find the GCF of the given numbers.<br>Calculation: Factors of 36: 1, 2, 3, 4, 6, 9, 12, 18, 36<br>Factors of 48: 1, 2, 3, 4, 6, 8, 12, 16, 24, 48<br>Greatest common factor: 12<br>Answer: C) 24 books.",
            "application": "<strong>Real-Life Applications of GCF:</strong>,<br> <strong>Story: The GCF Expedition of Emma and Noah</strong><br>Emma and Noah, two adventurous friends, embarked on a journey filled with puzzles and challenges that required the application of GCF to overcome obstacles and achieve success.<br> <strong>Challenge 1: The Puzzle Maze</strong><br> Emma and Noah found themselves in a perplexing maze filled with enigmatic symbols. To unlock the next passage, they needed to decipher the greatest common factor of two numbers written on a plaque. The numbers were 16 and 24. Recognizing the significance of GCF, they quickly determined that the greatest common factor was 8, allowing them to proceed through the maze.<br>  <strong>Challenge 2: The Cryptic Cipher</strong> <br> Continuing their expedition, Emma and Noah stumbled upon an ancient cryptic cipher inscribed on a stone tablet. To decipher the message, they had to compute the GCF of two mysterious numbers engraved beneath the inscription. The numbers revealed were 42 and 56. Applying their knowledge of GCF, they deduced that the greatest common factor was 14, unlocking the hidden message and unraveling the mystery. <br>  <strong>Challenge 3: The Guardian's Riddle</strong> <br>In their final challenge, Emma and Noah encountered a wise guardian guarding a hidden treasure. The guardian presented them with a riddle that involved determining the GCF of three numbers carved on a stone pedestal. The numbers were 36, 54, and 72. Drawing upon their understanding of GCF, Emma and Noah calculated that the greatest common factor was 18, earning them the guardian's approval and access to the treasure.",
            "quiz": "<strong>Quiz 1: </strong><br> What is the significance of finding the Greatest Common Factor (GCF)?,<br> <strong>Quiz 2: </strong><br>  How does the GCF concept relate to factors?,<br> <strong>Quiz 3: </strong><br> Can the GCF be utilized to simplify fractions?,<br> <strong>Quiz 4: </strong><br> What methods are available to determine the GCF of numbers?,<br> <strong>Quiz 5: </strong><br> How is the concept of GCF applied in real-life situations?"
            ``
        ``

        Instruction:

        1. Always generate output on JSON format.
        2. Never use single quote in the question.
        3. Always remember that its faq_quesion not faq_question
        4. Remember don't put anything inside the content part let it be emty as it is
        5, Don't put : in the between  "Your Post Title"
        6. Always put the h3 tag between each sub heading and strong tag between each context . For eg: "<h3>sub heading</h3>, <strong>context</strong>.
        7. , 5 Tips and Tricks, 5 Quizzes, 5 Real-Life Applications and 5 FAQs.
        8. Also generate "example" which is a small Summary of the "examples"
        9. Generae that explain in more words
        10. Always generate 3 examples

    {context}

    """
    prompt = PromptTemplate(
        input_variables=["context"],
        template=prompt_template,
    )

    chain = LLMChain(llm=model, prompt=prompt)

    query = f'''Generate me an article for "{topic}" in language "{language}". Compulsorily use these keywords in the article: "{key_word}".'''
    content = chain.invoke({'context': query})

    # Print content for debugging
    print("Generated Content:", content)

    # Check if content is in expected format
    if 'text' not in content:
        print("Error: 'text' key not found in content.")
        return None
    output = content['text'].replace('--', '{')
    output = output.replace('``', '}')
    # Print output for debugging
    print("Output:", output)

    # Try to decode JSON
    try:
        article = json.loads(output)
        print("Article JSON:", article)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None

    return article


def submit_Chimvine_form(google_sheet_ip):
    print("Google Sheet IP from Chimvine:", google_sheet_ip)
    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name

    else:
        first_name = ''

    print("Logged-in User's First Name:", first_name)

    # Handle the data from mathForm

    sheet_id = google_sheet_ip
    workbook = client.open_by_key(sheet_id)
   # Define date and time here
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")

    # Access the first sheet of the workbook
    sheet = workbook.sheet1

    created_contents = []
    failed_contents = []

    # Retrieve all values from the sheet along with row numbers
    all_rows_with_row_numbers = list(
        enumerate(sheet.get_all_records(), start=2))  # Start from row 2

    # Iterate through each row in the sheet along with row numbers
    for row_number, row_data in all_rows_with_row_numbers:
        status = row_data.get("Status", "")

        # Skip the row if the status is already "Posted successfully!"
        if status == "Posted successfully!":
            continue
        article_title = row_data.get("article_title", "")
        seo_keywords = row_data.get("seo_keywords", "")
        language = row_data.get("language", "")
        Date = row_data.get("Date", "")
        Time = row_data.get("Time", "")
        User = row_data.get("User", "")

        print(
            f"Article Title: {article_title}, SEO Keywords: {seo_keywords}, Language: {language}, Status: {status}, Date: {Date}, Time: {Time}")

        # Generate content for the article
        content = article_json(article_title, seo_keywords, language)
        print(content)
        if content:
            print(f"Posted to WordPress: {article_title}")
            created_contents.append(article_title)
            # Prepare the payload
            payload = json.dumps(content)
            print(payload)

            # Send the POST request to create the new article
            conn = http.client.HTTPSConnection("site.chimpvine.com")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic bmlyYWphbmFkbWluOmRRRVogU3VqWSBPYjFtIHRLVFcgR2JxRCBaeFd1'
            }
            conn.request("POST", "/wp-json/wp/v2/article", payload, headers)
            res = conn.getresponse()
            print(res)
            data = res.read()
            # Update status in Google Sheet
            if res.status == 201:
                User_Name = f"{first_name} "
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Posted successfully!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                sheet.update_cell(
                    row_number, sheet.find("User").col, User_Name)
            else:
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Post Failed!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                failed_contents.append(article_title)
                print(data.decode("utf-8"))
        else:
            print(f"Failed to generate content for: {article_title}")
            # Update status in Google Sheet
            sheet.update_cell(
                row_number, sheet.find("Status").col, "Content Generation Failed!")
            failed_contents.append(article_title)

    else:
        print("No data found in the spreadsheet.")

    return render_template('article.html', created_contents=created_contents, failed_contents=failed_contents)


# For Siam


def submit_Siam_form(google_sheet_ip):
    print("Google Sheet IP from SiamForm:", google_sheet_ip)
    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name

    else:
        first_name = ''

    print("Logged-in User's First Name:", first_name)

    # Handle the data from mathForm

    sheet_id = google_sheet_ip
    workbook = client.open_by_key(sheet_id)

    # Access the first sheet of the workbook
    sheet = workbook.sheet1

    created_contents = []
    failed_contents = []

    # Retrieve all values from the sheet along with row numbers
    all_rows_with_row_numbers = list(
        enumerate(sheet.get_all_records(), start=2))  # Start from row 2

    # Iterate through each row in the sheet along with row numbers
    for row_number, row_data in all_rows_with_row_numbers:
        status = row_data.get("Status", "")

        # Skip the row if the status is already "Posted successfully!"
        if status == "Posted successfully!":
            continue
        article_title = row_data.get("article_title", "")
        seo_keywords = row_data.get("seo_keywords", "")
        language = row_data.get("language", "")
        Date = row_data.get("Date", "")
        Time = row_data.get("Time", "")
        User = row_data.get("User", "")

        print(
            f"Article Title: {article_title}, SEO Keywords: {seo_keywords}, Language: {language}, Status: {status}, Date: {Date}, Time: {Time}")

        # Generate content for the article
        content = article_json(article_title, seo_keywords, language)
        print(content)
        if content:
            print(f"Posted to WordPress: {article_title}")
            created_contents.append(article_title)
            # Prepare the payload
            payload = json.dumps(content)
            print(payload)

            # Send the POST request to create the new article
            conn = http.client.HTTPSConnection("chimpvinesiam.com")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic bmlyYWphbmFkbWluOjdZWDYgNmJRQSBIazNHIGxxSUkgYzRYTiBhRkJl'
            }
            conn.request("POST", "/wp-json/wp/v2/article", payload, headers)
            res = conn.getresponse()
            print(res)
            data = res.read()
            # Update status in Google Sheet
            if res.status == 201:
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                User_Name = f"{first_name} "
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Posted successfully!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                sheet.update_cell(
                    row_number, sheet.find("User").col, User_Name)
            else:
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Post Failed!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                failed_contents.append(article_title)
                print(data.decode("utf-8"))
        else:
            print(f"Failed to generate content for: {article_title}")
            # Update status in Google Sheet
            sheet.update_cell(
                row_number, sheet.find("Status").col, "Content Generation Failed!")
            failed_contents.append(article_title)

    else:
        print("No data found in the spreadsheet.")

    return render_template('article.html', created_contents=created_contents, failed_contents=failed_contents)


# For Dansonsolution and Math Trciks Jr

def article_generator(topic, key_word, language):
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        openai_api_key=openAI_key,
        temperature=0,
        max_tokens=4095
    )

    prompt_template = """Role: Act as a content writer. You are about to write an article for an edtech site.
        Task: Generate an article for the requested topic. Generate the output as shown in the example below:

        Example :

        Input Query : Generate me an article for "Least Common Multiple"

        OUTPUT:

        <h2>Introduction</h2>

        <h4>What is LCM?:</h4>
        When dealing with numbers, especially in mathematics, you often come across the term "Least Common Multiple" or LCM. But what exactly does it mean? Let's dive into the world of LCM and understand its significance in solving mathematical problems.

        <h2>Definition</h2>

        <h4>The LCM Explained: </h4>
        The Least Common Multiple (LCM) of two or more numbers is the smallest multiple that is exactly divisible by each of the numbers. In simpler terms, it is the smallest number that is a multiple of all the given numbers.

        <h2>Methods </h2>

        <h4>Finding the LCM: </h34>
        There are various methods to find the LCM of numbers. One common method is to list the multiples of each number and find the smallest multiple that is common to all the numbers. Another method involves using prime factorization to find the LCM.

        <h2>Example</h2>

        <h4>Finding the LCM of 12 and 15:</h4>
        <strong> Step 1: </strong> List the multiples of each number
        Multiples of 12: 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, ...
        Multiples of 15: 15, 30, 45, 60, 75, 90, 105, 120, ...
        <strong> Step 2: </strong> Identify the smallest common multiple
        The smallest common multiple of 12 and 15 is 60.
        So, the LCM of 12 and 15 is 60.

        <h2>Quizzes</h2>

        <strong>1. "The Bakery Dilemma"</strong>
        <strong> Scenario: </strong>
        A bakery needs to pack cookies in boxes of 12 and 15. What is the least number of cookies they can pack in each box to ensure no cookies are left over?
        A) 60 cookies
        B) 30 cookies
        C) 45 cookies
        D) 120 cookies
        Equation: LCM of 12 and 15
        Answer: A) 60 cookies

        <strong>2. "The Garden Planting Puzzle"</strong>
        <strong> Scenario: </strong> A gardener wants to plant flowers in rows of 8 and 10. What is the least number of flowers they need to plant to fill each row without any flowers left over?
        A) 40 flowers
        B) 80 flowers
        C) 20 flowers
        D) 100 flowers
        Equation: LCM of 8 and 10
        Answer: A) 40 flowers

        <strong>3. "The Classroom Seating Arrangement"</strong>
        <strong> Scenario: </strong> A teacher wants to arrange students in rows of 6 and 9. What is the least number of students needed to fill each row without any students left over?
        A) 18 students
        B) 36 students
        C) 12 students
        D) 24 students
        Equation: LCM of 6 and 9
        Answer: A) 18 students

        <strong>4. "The Music Playlist Dilemma"</strong>
        <strong> Scenario: </strong> A DJ wants to create a playlist with songs that repeat every 4 and 6 minutes. What is the least amount of time before the playlist repeats a song?
        A) 12 minutes
        B) 24 minutes
        C) 18 minutes
        D) 36 minutes
        Equation: LCM of 4 and 6
        Answer: A) 12 minutes

        <strong>5. "The Sports Equipment Packing Challenge"</strong>
        <strong>Scenario: </strong>A coach needs to pack sports equipment in bags of 5 and 7. What is the least number of equipment items they can pack in each bag without any items left over?
        A) 35 items
        B) 70 items
        C) 25 items
        D) 50 items
        Equation: LCM of 5 and 7
        Answer: A) 35 items

        <h2>Tips and Tricks</h2>

        <strong>1. The Bakery Dilemma</strong>
        <strong>Scenario:</strong> Finding the LCM of 12 and 15.
        <strong>Tip: </strong>To find the LCM, list the multiples of each number and identify the smallest common multiple.
        Calculation: Multiples of 12: 12, 24, 36, 48, 60, ...
        Multiples of 15: 15, 30, 45, 60, ...
        Smallest common multiple: 60
        Answer: A) 60 cookies.

        <strong>2. The Garden Planting Puzzle</strong>
        <strong>Scenario:</strong> Finding the LCM of 8 and 10.
        <strong>Tip: </strong>List the multiples of each number and identify the smallest common multiple to find the LCM.
        Calculation: Multiples of 8: 8, 16, 24, 32, 40, ...
        Multiples of 10: 10, 20, 30, 40, ...
        Smallest common multiple: 40
        Answer: A) 40 flowers.

        <strong>3. The Classroom Seating Arrangement</strong>
        <strong>Scenario:</strong> Finding the LCM of 6 and 9.
        <strong>Tip:</strong> Use the method of listing multiples to find the LCM of the given numbers.
        Calculation: Multiples of 6: 6, 12, 18, 24, 30, ...
        Multiples of 9: 9, 18, 27, 36, ...
        Smallest common multiple: 18
        Answer: A) 18 students.

        <strong>4. The Music Playlist Dilemma</strong>
        <strong>Scenario:</strong> Finding the LCM of 4 and 6.
        <strong>Tip:</strong> List the multiples of each number and identify the smallest common multiple to find the LCM.
        Calculation: Multiples of 4: 4, 8, 12, 16, 20, ...
        Multiples of 6: 6, 12, 18, 24, ...
        Smallest common multiple: 12
        Answer: A) 12 minutes.

        <strong>5. The Sports Equipment Packing Challenge</strong>
        <strong>Scenario:</strong> Finding the LCM of 5 and 7.
        <strong>Tip:</strong> Use the method of listing multiples to find the LCM of the given numbers.
        Calculation: Multiples of 5: 5, 10, 15, 20, 25, ...
        Multiples of 7: 7, 14, 21, 28, ...
        Smallest common multiple: 35
        Answer: A) 35 items.

        <h2>Real-Life Applications</h2>

        <strong>Story: "The LCM Adventure of Alex and Lily"</strong>
        Alex and Lily were two adventurous siblings who loved solving puzzles and riddles. One day, they encountered a series of challenges that required them to use the concept of LCM to overcome obstacles and complete their quests.

        <strong>Challenge 1: The Treasure Hunt</strong>
        Alex and Lily embarked on a treasure hunt that led them to a mysterious cave. Inside the cave, they found a locked chest with a riddle written on it. The riddle stated, "To open the chest, find the least number that is a multiple of 4, 6, and 8." Remembering their lessons on LCM, Alex and Lily quickly calculated the LCM of 4, 6, and 8, which turned out to be 24. They used the number to unlock the chest and discovered a map to the hidden treasure.

        <strong>Challenge 2: The Magical Bridge</strong>
        As they continued their adventure, Alex and Lily encountered a magical bridge guarded by a mystical creature. The creature challenged them to find the least number of steps that would cause the bridge to light up. The steps were numbered 5, 7, and 9. Applying their knowledge of LCM, Alex and Lily calculated the LCM of 5, 7, and 9, which turned out to be 315. As they took 315 steps, the bridge lit up, allowing them to cross safely.

        <strong>Challenge 3: The Enchanted Garden</strong>
        In the final challenge, Alex and Lily entered an enchanted garden filled with beautiful flowers. They were tasked with arranging the flowers in rows, with each row containing 12, 15, and 18 flowers. Using the concept of LCM, they determined that they needed 180 flowers to fill each row without any flowers left over. The garden bloomed with vibrant colors, and the siblings completed their adventure successfully.

        <h2>FAQ</h2>

        <strong>What is the significance of finding the LCM of numbers?</strong>
        Finding the LCM is important in various mathematical and real-life scenarios. It helps in solving problems related to scheduling, repeating patterns, and resource allocation. In mathematics, the LCM is used in operations involving fractions, simplifying expressions, and solving equations.

        <strong>How is the LCM related to the concept of multiples?</strong>
        The LCM is directly related to the concept of multiples. It represents the smallest common multiple of two or more numbers. Multiples are the result of multiplying a number by an integer, and the LCM is the smallest multiple that is common to all the given numbers.

        <strong>Can the LCM be used to find the common denominator in fractions?</strong>
        Yes, the LCM is used to find the common denominator when adding or subtracting fractions. By finding the LCM of the denominators, you can convert the fractions to equivalent fractions with the same denominator, making it easier to perform operations.

        <strong>Are there specific methods to find the LCM of numbers?</strong>
        Yes, there are different methods to find the LCM, including listing multiples, using prime factorization, and using the method of division. Each method has its advantages and can be applied based on the given numbers and the preferred approach.

        <strong>How does the concept of LCM apply to real-life situations?</strong>
        The concept of LCM has practical applications in various real-life situations, such as scheduling events, planning recurring tasks, and organizing resources. It helps in determining the least amount of time, distance, or quantity needed to fulfill specific requirements, making it a valuable tool in problem-solving.

        Instruction:
        1. Always include Introduction, Defination, Methods, Example, Quizzes, Real-Life Applications and FAQs.
        2. Always put the h3 tag between each sub heading and strong tag between each context . For eg: "<h3>sub heading</h3>, <strong>context</strong>.
        3. Always compulsorily generate 5 Examples, 5 Tips and Tricks, 5 Quizzes,5 Real-Life Applications and 5 FAQs. More than one 'tips and tricks', 'Real-Life Applications' and 'quizzes' can be added for each keywords to make 5 in total for all three categories.
        4. Always generate article of around 5000-6000 words.
        5. Do not add a conclusion. Finish at FAQ.


        {context}
        """

    prompt = PromptTemplate(
        input_variables=["context"],
        template=prompt_template,)

    chain = LLMChain(llm=llm, prompt=prompt)

    query = f'''Generate me an article for "{topic}" in language "{language}". Compulsorily use these keywords in article : "{key_word}".'''

    content = chain.run(query)

    return content

# For Math Tricks Jr


def submit_math_form(google_sheet_ip):
    print("Google Sheet IP from mathForm:", google_sheet_ip)
    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name

    else:
        first_name = ''

    print("Logged-in User's First Name:", first_name)

    # Handle the data from mathForm

    sheet_id = google_sheet_ip
    workbook = client.open_by_key(sheet_id)

    # Access the first sheet of the workbook
    sheet = workbook.sheet1

    created_contents = []
    failed_contents = []

    # Retrieve all values from the sheet along with row numbers
    all_rows_with_row_numbers = list(
        enumerate(sheet.get_all_records(), start=2))  # Start from row 2

    # Iterate through each row in the sheet along with row numbers
    for row_number, row_data in all_rows_with_row_numbers:
        status = row_data.get("Status", "")

        # Skip the row if the status is already "Posted successfully!"
        if status == "Posted successfully!":
            continue
        article_title = row_data.get("article_title", "")
        seo_keywords = row_data.get("seo_keywords", "")
        language = row_data.get("language", "")
        Date = row_data.get("Date", "")
        Time = row_data.get("Time", "")
        User = row_data.get("User", "")

        print(
            f"Article Title: {article_title}, SEO Keywords: {seo_keywords}, Language: {language}, Status: {status}, Date: {Date}, Time: {Time}")

        # Generate content for the article
        content = article_generator(article_title, seo_keywords, language)

        print(content)
        if content:
            print(f"Posted to WordPress: {article_title}")
            created_contents.append(article_title)
            # Prepare the payload
            # Prepare WordPress Post Data
            wordpress_payload = {
                "title": article_title,
                "content": content,
            }

            # Convert payload to bytes
            payload_bytes = json.dumps(wordpress_payload).encode('utf-8')

            # Send WordPress Post Request
            conn = http.client.HTTPSConnection("mathtricksjr.com")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic TmlyYWphbl9hZG1pbjpSeEFTIEp5a3QgQ0lsOSBySmFIIFFzRXAgU0ZqeA=='
            }

            conn.request("POST", "/wp-json/wp/v2/posts", payload_bytes,
                         headers)  # Use payload_bytes instead of payload
            res = conn.getresponse()
            print(res)
            data = res.read()
            # Update status in Google Sheet
            if res.status == 201:
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                User_Name = f"{first_name}"
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Posted successfully!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                sheet.update_cell(
                    row_number, sheet.find("User").col, User_Name)
            else:
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Post Failed!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                failed_contents.append(article_title)
                print(data.decode("utf-8"))
        else:
            print(f"Failed to generate content for: {article_title}")
            # Update status in Google Sheet
            sheet.update_cell(
                row_number, sheet.find("Status").col, "Content Generation Failed!")
            failed_contents.append(article_title)

    else:
        print("No data found in the spreadsheet.")

    return render_template('article.html', created_contents=created_contents, failed_contents=failed_contents)


# For Dansonsolutions
def submit_DansonsolutionsForm(google_sheet_ip):
    print("Google Sheet IP from Dansonsolutions:", google_sheet_ip)
    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name

    else:
        first_name = ''

    print("Logged-in User's First Name:", first_name)

    # Handle the data from mathForm

    sheet_id = google_sheet_ip
    workbook = client.open_by_key(sheet_id)

    # Access the first sheet of the workbook
    sheet = workbook.sheet1

    created_contents = []
    failed_contents = []

    # Retrieve all values from the sheet along with row numbers
    all_rows_with_row_numbers = list(
        enumerate(sheet.get_all_records(), start=2))  # Start from row 2

    # Iterate through each row in the sheet along with row numbers
    for row_number, row_data in all_rows_with_row_numbers:
        status = row_data.get("Status", "")

        # Skip the row if the status is already "Posted successfully!"
        if status == "Posted successfully!":
            continue
        article_title = row_data.get("article_title", "")
        seo_keywords = row_data.get("seo_keywords", "")
        language = row_data.get("language", "")
        Date = row_data.get("Date", "")
        Time = row_data.get("Time", "")
        User = row_data.get("User", "")

        print(
            f"Article Title: {article_title}, SEO Keywords: {seo_keywords}, Language: {language}, Status: {status}, Date: {Date}, Time: {Time}")

        # Generate content for the article
        content = article_generator(article_title, seo_keywords, language)

        print(content)
        if content:
            print(f"Posted to WordPress: {article_title}")
            created_contents.append(article_title)
            # Prepare the payload
            # Prepare WordPress Post Data
            wordpress_payload = {
                "title": article_title,
                "content": content,
            }

            # Convert payload to bytes
            payload_bytes = json.dumps(wordpress_payload).encode('utf-8')

            # Send WordPress Post Request
            conn = http.client.HTTPSConnection("dansonsolutions.com")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ZGFuc29uYWRtaW46OWZrVCBHcUxwIDJ1Z3IgNDMwYyBDczBKIHM3V1U='
            }

            conn.request("POST", "/wp-json/wp/v2/posts", payload_bytes,
                         headers)  # Use payload_bytes instead of payload
            res = conn.getresponse()
            print(res)
            data = res.read()
            # Update status in Google Sheet
            if res.status == 201:
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                User_Name = f"{first_name}"
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Posted successfully!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                sheet.update_cell(
                    row_number, sheet.find("User").col, User_Name)
            else:
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Post Failed!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                failed_contents.append(article_title)
                print(data.decode("utf-8"))
        else:
            print(f"Failed to generate content for: {article_title}")
            # Update status in Google Sheet
            sheet.update_cell(
                row_number, sheet.find("Status").col, "Content Generation Failed!")
            failed_contents.append(article_title)

    else:
        print("No data found in the spreadsheet.")

    return render_template('article.html', created_contents=created_contents, failed_contents=failed_contents)


# Article generator for mathfun

def article_generator_for_mathfun(topic, key_word, language):
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        openai_api_key=openAI_key,
        temperature=0,
        max_tokens=4095
    )

    prompt_template = """Role: Act as a content writer. You are about to write an article for an edtech site.
        Task: Generate an article for the requested topic. Generate the output as shown in the example below:

        Example :

        Input Query : Generate me an article for "Even and Odd Numbers"

        OUTPUT:

        <h2><strong>Introduction</strong></h2>

        <p>Numbers are the essence of mathematics, and among them, even and odd numbers stand as peculiar twins in the realm of numerical wonders. Just as in life, where opposites attract, the pairing of even and odd numbers brings a fascinating harmony to the world of mathematics.</p>

        <p>This article will be your one-stop guide to understanding even and odd numbers. We’ll delve into their definitions, explore their properties, and uncover their hidden importance in both mathematics and everyday situations. We’ll equip you with strategies to identify even and odd numbers like a pro and even show you some cool tricks you can use to solve math problems faster. So, whether you’re a curious student or someone who wants to brush up on the basics, this article is for you.</p>

        <h2><strong>Understanding Even and Odd Numbers</strong></h2>

        <h3><strong>What are Even and Odd Numbers?</strong></h3>

        <p><strong>Even numbers:</strong> Even numbers are whole numbers that can be perfectly divided by 2 with no remainder. Examples of even numbers include 2, 4, 6, 8, 10, and so on.</p>

        <p><strong>Odd numbers:</strong> Odd numbers are whole numbers that leave a remainder of 1 when divided by 2. Examples of odd numbers include 1, 3, 5, 7, 9, and so on.</p>

        <h3><strong>Properties of Even and Odd Numbers</strong></h3>

        <h4><strong>Even Numbers:</strong></h4>

        <ul>
        <li><strong>Divisible by 2:</strong> Even numbers are those that can be divided by 2 with no remainder.</li>
        <li><strong>Ending in 0, 2, 4, 6, or 8:</strong> The last digit of even numbers is always 0, 2, 4, 6, or 8.</li>
        </ul>

        <h4><strong>Odd Numbers:</strong></h4>

        <ul>
        <li><strong>Not Divisible by 2:</strong> Odd numbers cannot be divided by 2 without leaving a remainder of 1.</li>
        <li><strong>Ending in 1, 3, 5, 7, or 9:</strong> The last digit of odd numbers is always 1, 3, 5, 7, or 9.</li>
        </ul>

        <h2><strong>Importance of Even and Odd Numbers</strong></h2>
        <p>Even and odd numbers might seem like a basic concept, but their significance in the world of mathematics and beyond is truly remarkable. Let’s delve deeper and explore why understanding even and odd numbers is crucial.</p>
        <h3><strong>Role of Even and Odd Numbers in Mathematics</strong></h3>

        <p>These classifications pave the way for numerous mathematical operations and concepts:</p>

        <ul>
        <li><strong>Number Theory:</strong> Even and odd numbers are fundamental building blocks in number theory, exploring properties like divisibility and prime numbers.</li>
        <li><strong>Algebra:</strong> Even and odd numbers properties play a vital role in simplifying algebraic expressions and predicting outcomes of operations.</li>
        <li><strong>Geometry:</strong> Even and odd numbers find applications in geometric shapes, influencing properties like the number of sides in a polygon.</li>
        </ul>

        <h3><strong>Application of Even and Odd Numbers in Daily Life Scenarios</strong></h3>

        <p>Even and odd numbers aren’t confined to textbooks – they are surprisingly present in our everyday lives:</p>

        <ul>
        <li><strong>Pairing Objects:</strong> Even numbers ensure equal distribution – even numbers of socks, shoes, or chopsticks for a balanced experience.</li>
        <li><strong>Alternating Patterns:</strong> Traffic lights often follow an even-odd pattern to ensure smooth traffic flow.</li>
        <li><strong>Problem-Solving:</strong> Even and odd properties can be used to solve everyday problems, like distributing pizza slices evenly among friends.</li>
        </ul>

        <h3><strong>Significance of Even and Odd Numbers in Problem-Solving</strong></h3>

        <p>Beyond everyday applications, even and odd numbers hold immense value in problem-solving:</p>

        <ul>
        <li><strong>Logic Puzzles:</strong> Many logic puzzles involve identifying even and odd properties to reach the solution.</li>
        <li><strong>Parity Checks:</strong> In computer science, even and odd properties are used for “parity checks” – a way to detect errors in data transmission.</li>
        </ul>

        <h2><strong>Recognizing Even and Odd Numbers</strong></h2>

        <h3><strong>Strategies for Identifying Even Numbers</strong></h3>

        <p>Here are two key methods to recognize even numbers quickly and confidently:</p>

        <ul>
        <li><strong>Divisibility by 2:</strong> If a number is divisible by 2 with no remainder, it’s an even number.</li>
        <li><strong>Last Digit Analysis:</strong> Even numbers end in 0, 2, 4, 6, or 8.</li>
        </ul>

        <h3><strong>Strategies for Recognizing Odd Numbers</strong></h3>

        <p>Just like even numbers, odd numbers have their own identification tricks:</p>

        <ul>
        <li><strong>Non-divisibility by 2:</strong> Odd numbers cannot be divided by 2 without leaving a remainder of 1.</li>
        <li><strong>Last Digit Analysis:</strong> Odd numbers end in 1, 3, 5, 7, or 9.</li>
        </ul>

        <h3><strong>Practice Exercises to Reinforce Recognition Skills</strong></h3>

        <p>Now that you have the tools, let’s put them into practice. Try identifying whether the following numbers are even or odd:</p>

        <ul>
        <li>42 (Even: divisible by 2 and ends in 2)</li>
        <li>81 (Odd: not divisible by 2 and ends in 1)</li>
        <li>110 (Even: divisible by 2 and ends in 0)</li>
        <li>537 (Odd: not divisible by 2 and ends in 7)</li>
        </ul>

        <h2><strong>Even and Odd Properties in Arithmetic Operations</strong></h2>

        <p>Understanding how even and odd numbers behave during basic arithmetic operations like addition, subtraction, multiplication, and division can be a game-changer:</p>

        <h3><strong>Adding or Subtracting Even and Odd Numbers</strong></h3>

        <p>Even + Even = Even</p>
        <p>Odd + Odd = Even</p>
        <p>Even + Odd = Odd</p>
        <p>Even – Even = Even</p>
        <p>Odd – Odd = Even</p>
        <p>Even – Odd = Odd</p>
        <p>Odd – Even = Odd</p>

        <h3><strong>Multiplying and Dividing Even and Odd Numbers</strong></h3>

        <p>Even x Even = Even</p>
        <p>Odd x Odd = Odd</p>
        <p>Even x Odd = Even</p>

        <h2><strong>Even and Odd Numbers in Algebraic Expressions</strong></h2>

        <p>Even and odd properties can be applied to simplify algebraic expressions:</p>

        <h3><strong>Identifying Patterns in Equations Involving Even and Odd Numbers</strong></h3>

        <p>By recognizing even and odd terms in an equation, you can predict the outcome of certain operations.</p>

        <h3><strong>Simplifying Expressions Using Even and Odd Properties</strong></h3>

        <p>Knowing that Even + Even = Even or Even x Odd = Even allows you to combine or cancel out terms in expressions, leading to faster solutions.</p>

        <h2><strong>Practical Examples Demonstrating the Application of Even and Odd Number Properties in Problem-Solving</strong></h2>

        <p>Let’s see how these concepts translate into real-world problem-solving:</p>

        <p>Example 1: You have 12 cookies and want to share them equally among your friends. Since 12 is even (divisible by 2 and ends in 2), you can distribute them evenly without any leftover cookies.</p>

        <p>Example 2: An equation states: x + 7 = 14. Knowing that 7 is odd, we can add -7 to both sides and see that x must be even.</p>

        <h2><strong>Conclusion</strong></h2>

        <p>We’ve embarked on a journey exploring the fascinating world of even and odd numbers. From their basic definitions to their surprising applications, we’ve uncovered the magic these seemingly simple concepts hold.</p>

        <h3><strong>Recap of Key Points Covered in the Article:</strong></h3>

        <ul>
        <li>We established the definitions of even and odd numbers, along with their divisibility and last-digit rules for quick identification.</li>
        <li>We delved into the significance of even and odd numbers in mathematics, highlighting their role in number theory, algebra, and geometry.</li>
        <li>We explored the practical applications of even and odd numbers in everyday life, from ensuring fair distribution to understanding traffic flow patterns.</li>
        <li>We equipped ourselves with strategies to recognize even and odd numbers efficiently, including divisibility checks and last-digit analysis.</li>
        <li>We unlocked the power of even and odd number properties in solving mathematical problems, learning how these concepts can be applied to arithmetic operations and simplify algebraic expressions.</li>
        </ul>

        <p>The journey with even and odd numbers doesn’t end here. As you progress in mathematics, you’ll encounter even and odd properties resurfacing in more advanced topics like prime factorization and modular arithmetic.</p>

        <h3><strong>Ways to Keep Exploring:</strong></h3>

        <ul>
        <li>Challenge yourself with online quizzes and puzzles that involve even and odd numbers.</li>
        <li>Look for patterns in everyday objects – are there even or odd numbers of stairs in your house? How about buttons on your shirt?</li>
        <li>Try inventing your own word problems or brain teasers that utilize even and odd properties.</li>
        </ul>

        <p>The more you practice and explore, the more you’ll appreciate the elegance and versatility of even and odd numbers in the vast world of mathematics.</p>

        <h2><strong>Frequently Asked Questions (FAQs)</strong></h2>

        <h3><strong>Are there any numbers that are neither even nor odd?</strong></h3>

        <p>No, whole numbers are classified as either even or odd. Zero is a special case; it’s considered neither even nor odd by some mathematicians, while others consider it to be even because it’s divisible by 2.</p>

        <h3><strong>How can I identify even and odd numbers quickly when dealing with large numbers?</strong></h3>

        <p>For larger numbers, divisibility by 2 can be cumbersome. Here’s a trick: a number is even if the last two digits are divisible by 4. For example, 1256 is even because the last two digits (56) are divisible by 4 (14).</p>

        <h3><strong>How are even and odd numbers used in advanced mathematics?</strong></h3>

        <p>Even and odd properties play a crucial role in concepts like parity checks (used in error detection in data transmission), modular arithmetic (a system of clock-like arithmetic), and identification of prime numbers (numbers divisible by only 1 and itself).</p>

        Instruction:
        1. Always include Introduction, Understanding Even and Odd Numbers, Properties of Even and Odd Numbers, Importance of Even and Odd Numbers, Role of Even and Odd Numbers in Mathematics, Application of Even and Odd Numbers in Daily Life Scenarios, Significance of Even and Odd Numbers in Problem-Solving,Recognizing Even and Odd Numbers,Practice Exercises to Reinforce Recognition Skills,Practical Examples Demonstrating the Application of Even and Odd Number Properties in Problem-Solving, Conclusion and Frequently Asked Questions (FAQs).
        2. Always put the h3 tag between each sub heading and strong tag between each context . For eg: "<h3>sub heading</h3>, <strong>context</strong>.
        4. Always generate article of around 5000-6000 words.


        {context}
        """

    prompt = PromptTemplate(
        input_variables=["context"],
        template=prompt_template,)

    chain = LLMChain(llm=llm, prompt=prompt)

    query = f'''Generate me an article for "{topic}" in language "{language}". Compulsorily use these keywords in article : "{key_word}".'''

    content = chain.run(query)

    return content


def submit_MathfunForm(google_sheet_ip):
    print("Google Sheet IP from Mathfun:", google_sheet_ip)
    # Get the current user's username
    user = current_user  # Get the current logged-in user
    print("Current user name:", user.full_name)
    if user:
        first_name = user.full_name

    else:
        first_name = ''

    print("Logged-in User's First Name:", first_name)

    # Handle the data from mathForm

    sheet_id = google_sheet_ip
    workbook = client.open_by_key(sheet_id)

    # Access the first sheet of the workbook
    sheet = workbook.sheet1

    created_contents = []
    failed_contents = []

    # Retrieve all values from the sheet along with row numbers
    all_rows_with_row_numbers = list(
        enumerate(sheet.get_all_records(), start=2))  # Start from row 2

    # Iterate through each row in the sheet along with row numbers
    for row_number, row_data in all_rows_with_row_numbers:
        status = row_data.get("Status", "")

        # Skip the row if the status is already "Posted successfully!"
        if status == "Posted successfully!":
            continue
        article_title = row_data.get("article_title", "")
        seo_keywords = row_data.get("seo_keywords", "")
        language = row_data.get("language", "")
        Date = row_data.get("Date", "")
        Time = row_data.get("Time", "")
        User = row_data.get("User", "")

        print(
            f"Article Title: {article_title}, SEO Keywords: {seo_keywords}, Language: {language}, Status: {status}, Date: {Date}, Time: {Time}")

        # Generate content for the article
        content = article_generator_for_mathfun(
            article_title, seo_keywords, language)

        print(content)
        if content:
            print(f"Posted to WordPress: {article_title}")
            created_contents.append(article_title)
            # Prepare the payload
            # Prepare WordPress Post Data
            wordpress_payload = {
                "title": article_title,
                "content": content,
            }

            # Convert payload to bytes
            payload_bytes = json.dumps(wordpress_payload).encode('utf-8')

            # Send WordPress Post Request
            conn = http.client.HTTPSConnection("mathfun.us")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic c2hyZXlhOjVvMUMgRnRTWCBxMnJNIFlhRjEgWDh4ViBkUVAx',
                'Cookie': 'nfdbrandname=hostgator'
            }
            # Use payload_bytes instead of payload
            conn.request("POST", "/wp-json/wp/v2/posts/",
                         payload_bytes, headers)
            res = conn.getresponse()
            print(res)
            data = res.read()
            # Update status in Google Sheet
            if res.status == 201:
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                User_Name = f"{first_name}"
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Posted successfully!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                sheet.update_cell(
                    row_number, sheet.find("User").col, User_Name)
            else:
                sheet.update_cell(row_number, sheet.find(
                    "Status").col, "Post Failed!")
                sheet.update_cell(row_number, sheet.find("Date").col, date)
                sheet.update_cell(row_number, sheet.find("Time").col, time)
                failed_contents.append(article_title)
                print(data.decode("utf-8"))
        else:
            print(f"Failed to generate content for: {article_title}")
            # Update status in Google Sheet
            sheet.update_cell(
                row_number, sheet.find("Status").col, "Content Generation Failed!")
            failed_contents.append(article_title)

    else:
        print("No data found in the spreadsheet.")

    return render_template('mathfun.html', created_contents=created_contents, failed_contents=failed_contents)


# For Video Script

@app.route('/video_script', methods=['GET', 'POST'])
def video_script():
    if request.method == 'POST':
        try:
            sheet_id = request.form['sheet_id']
            folder_id = request.form['folder_id']

            if sheet_id and folder_id:
                # Assuming you have a function 'submit_video' to handle processing
                result = submit_video(sheet_id, folder_id)

                # Check if the result is successful
                if 'success' in result.lower():
                    flash(result, "success")
                else:
                    flash(result, "error")
            else:
                flash(
                    "Please enter both Google Sheet ID and Google Drive Folder ID.", "warning")

        except SpreadsheetNotFound as e:
            flash(f"Google Sheet not found: {str(e)}", "error")

        except Exception as e:
            flash(f"Google Sheet Id not found:: {str(e)}", "error")

    return render_template('video_script.html')


def process_video_data(topic, keywords, characters, visuals, storyline, cliffhanger):
    llm = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        openai_api_key=openAI_key,
        temperature=0,
        max_tokens=4095
    )

    propmt_template = '''Role: You are acting as a script writer for a children-friendly youtube Channel. Your main reponsibility is to write a script on a given
topic, giving musical choices, ausios and writing a compelling story to match the subject.

Task: Write a Children-friendly education oriented youtube script that is to be published.

Example:

Human Prompt: Give me a youtube script for the topic, 'Trees and Forest'. In the script, include key words 'forests, plant communication,ecosystems, climate change'. In the script, use characters 'Timber the tree and Fungi the friendly fungus'. The visuals in the video includes, 'Music,Introduction, animated story,interactive questions,educational content, activity and Wrap up.'
The story line should be as follows, 'The video opens up with a bright animated logo of channel with a cheerful and inviting tone. Then, images of lush forest appears, showing  underground root networks. This is welcomed by a soft ambient forest sounds and a voice asking a question. Then, we meet our characters who help each other survive and live. This is followed by an interactive content that pops up and asks the viewer a question regarding the characters. After about 5 seconds that includes thinking music, the content is followed by an educational conten that indirectly answers the question. The demonstration includes pictures, charts, graphics and points to support the case. This is followed by an demostration that appeals the viewers to take action. Now, we reach the end of the video. Firstly, we wrap up everything that we have learnd. This is followed by a call of action.'
In the storyline, also provide some clifhangers that may potentially hint future videos or topic that may be raised from this script.

AI Output:



[
    --
    "Video Section":"Opening Music",
    "Time Stamp":"0:00 - 0:10",
    "Visuals":"A bright, animated logo of the channel appears.",
    "Audio":"Cheerful and inviting tune.",
    "Script":"Instrumental only"
    ``,
    --
    "Video Section":"Introduction",
    "Time Stamp":"0:10 - 0:40",
    "Visuals":"Images of lush forests and underground root networks.",
    "Audio":"Background music fades to soft ambient forest sounds.",
    "Script":"Did you know that some trees communicate with each other through a hidden network underground? Today, we're diving into the fascinating world of plant communication and how it affects ecosystems."
    ``,
    --
    "Video Section":"Story Segment",
    "Time Stamp":"0:40 - 2:00",
    "Visuals":"Animated story of Timber the Tree and Fungi the Friendly Fungus in a forest.",
    "Audio":"Gentle, engaging storytelling voice.",
    "Script":"Meet Timber the Tree and Fungi the Friendly Fungus. Watch how they help each other survive, sharing nutrients and sending signals about pests, showing the beauty of symbiotic relationships in forests."
    ``,
    --
    "Video Section":"Interactive Question",
    "Time Stamp":"2:00 - 2:30",
    "Visuals":"A question pops up on screen with thinking music in the background.",
    "Audio":"Question posed by narrator, followed by a 5-second pause with thinking music.",
    "Script":"What do you think happens when Timber is attacked by pests? pause Timber sends chemical signals through Fungi, alerting nearby trees to boost their own pest defenses!"
    ``,
    --
    "Video Section":"Main Educational Content",
    "Time Stamp":"2:30 - 5:00",
    "Visuals":"Various visuals illustrating each section"s key points.",
    "Audio":"Narration with occasional background music for emphasis.",
    "Script":"A. The Wood Wide Web: Trees and fungi form a 'Wood Wide Web' for communication and nutrient exchange. example shown  B. Benefits and Challenges: Deforestation threatens this system, but conservation efforts are making a difference.' expert viewpoints  C. Future Trends: 'Sustainable forestry practices could protect these networks.' viewer engagement encouraged"
    ``,
    --
    "Video Section":"Activity or Demonstration",
    "Time Stamp":"5:00 - 6:00",
    "Visuals":"Step-by-step visuals of planting a mini-forest.",
    "Audio":"Upbeat background music with instructional voice-over.",
    "Script":"Let's plant a mini-forest together! This diversity supports plant health and communication, just like in larger ecosystems."
    ``,
    --
    "Video Section":"Wrap-Up and Reflection",
    "Time Stamp":"6:00 - 6:30",
    "Visuals":"Recap visuals of the video’s main points.",
    "Audio":"Soft, reflective music with a thoughtful tone from the narrator.",
    "Script":"Today, we explored the 'Wood Wide Web' and its crucial role in forests. How can understanding plant communication change our view of nature and conservation?"
    ``,
    --
    "Video Section":"Call to Action",
    "Time Stamp":"6:30 - 7:00",
    "Visuals":"Call to action text and visuals on screen.",
    "Audio":"Encouraging tone from the narrator.",
    "Script":"Share your mini-forest progress and explore more about plant science. Interested in biodiversity or climate change? There's so much more to discover!"
    ``
    ]

    Instructions:
    1. The duration of Video Should alwas be between 7-10 minutes.
    2. Always Use simple vocabulary. Prevent words such as 'delve','tapestry' etc.
    3. Only Give the AI output as result.
    4. Make the script time stamp total of 30 minutes and script content more long.


    {context}
    '''

    prompt = PromptTemplate(
        input_variables=["context"],
        template=propmt_template,
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    query = f'''Give me a youtube script for the topic,{topic} . In the script, include key words {keywords}. In the script, use characters {characters}. The visuals in the video includes,{visuals}.
        The story line should be as follows, {storyline}
        In the storyline, also provide some clifhangers that may potentially hint future videos or topic that may be raised from this script. The cliffhanger can also include {cliffhanger}
        '''

    content = chain.invoke({'context': query})

    output = content['text'].replace('[', "{")
    output = output.replace(']', "}")
    output = output.replace('``', "}")
    output = output.replace('--', "{")
    print("This the output", output)
    return output


def submit_video(sheet_id, folder_id):
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(
        "credentials.json", scopes=scopes)
    client_sheets = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)

    user = current_user  # Get the current logged-in user
    first_name = user.full_name if user else ''

    try:
        workbook = client_sheets.open_by_key(sheet_id)
        sheet = workbook.sheet1

        created_contents = []
        failed_contents = []
        success_count = 0  # Initialize the success count

        all_rows_with_row_numbers = list(
            enumerate(sheet.get_all_records(), start=2))  # Start from row 2

        for row_number, row_data in all_rows_with_row_numbers:
            status = row_data.get("Status", "")

            if status == "Posted successfully!":
                continue

            topic = row_data.get("Topic", "")
            keywords = row_data.get("Keywords", "")
            characters = row_data.get("Characters", "")
            visuals = row_data.get("Visuals", "")
            storyline = row_data.get("Storyline", "")
            cliffhanger = row_data.get("Cliffhanger", "")

            print(f"topic: {topic}, Keywords: {keywords}, characters: {characters}, visuals: {visuals}, storyline: {storyline}, cliffhanger: {cliffhanger}")
            content = process_video_data(
                topic, keywords, characters, visuals, storyline, cliffhanger)

            if content:
                created_contents.append(content)
                print(f"Posted to Google Drive: {topic}")

                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H-%M-%S")
                script_filename = f"{date}_{time}_{uuid.uuid4()}_script.txt"

                media = MediaIoBaseUpload(io.BytesIO(
                    content.encode()), mimetype='text/plain')
                file_metadata = {
                    "name": script_filename,
                    "parents": [folder_id]
                }
                uploaded_file = drive_service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ).execute()

                success_count += 1  # Increment the success count
                uploaded_file_id = uploaded_file.get("id")

                sheet.update_cell(row_number, 2, "Success!")
                print(
                    f"https://drive.google.com/file/d/{uploaded_file_id}/view")

                translated_file_link = f"https://drive.google.com/file/d/{uploaded_file_id}/view"
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                User_Name = f"{first_name}"

                status_col = sheet.find("Status")
                date_col = sheet.find("Date")
                time_col = sheet.find("Time")
                user_col = sheet.find("User")

                if status_col and date_col and time_col and user_col:
                    sheet.update_cell(
                        row_number, status_col.col, "Posted successfully!")
                    sheet.update_cell(row_number, date_col.col, date)
                    sheet.update_cell(row_number, time_col.col, time)
                    sheet.update_cell(row_number, user_col.col, User_Name)
                    sheet.update_cell(row_number, sheet.find(
                        "Link").col, translated_file_link)
                else:
                    print(
                        "One or more columns are missing in the sheet. Please check the sheet structure.")

            else:
                print(f"Failed to generate content for: {topic}")
                status_col = sheet.find("Status")
                if status_col:
                    sheet.update_cell(row_number, status_col.col,
                                      "Content Generation Failed!")
                else:
                    print(
                        "Status column is missing in the sheet. Please check the sheet structure.")
                failed_contents.append(topic)

        return f"{success_count} translation(s) were successful."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"Google Sheet ID not found:"


@app.route('/create_admin', methods=['GET', 'POST'])
@login_required  # Assuming you have login_required decorator for authentication
def create_admin():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if an admin with the email already exists
        existing_admin = User.query.filter_by(
            email=form.email.data, is_admin=True).first()
        if existing_admin:
            flash('Admin with this email already exists.', 'error')
            return redirect(url_for('create_admin'))

        # Create a new admin user
        new_admin = User(email=form.email.data,
                         full_name=form.full_name.data, is_admin=True)
        new_admin.set_password(form.password.data)

        db.session.add(new_admin)
        db.session.commit()

        flash('Admin user created successfully!', 'success')
        # Redirect to the same page after successful registration
        return redirect(url_for('create_admin'))

    return render_template('create_admin.html', title='Create Admin', form=form)


@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('You are not authorized to access this page.', 'error')
        return redirect(url_for('index'))

    admin_users = User.query.filter_by(is_admin=True).all()
    staff_users = User.query.filter_by(is_admin=False).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if user:
            try:
                db.session.delete(user)
                db.session.commit()
                print(f"Deleted user: {user.email}")  # Debugging statement
                flash(
                    f'User {user.email} has been deleted successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                print(f"Error deleting user: {e}")  # Debugging statement
                flash(f'Error deleting user: {e}', 'error')
        else:
            flash('User not found.', 'error')

        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', admin_users=admin_users, staff_users=staff_users)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
