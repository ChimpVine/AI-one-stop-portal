import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import json

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def article_mathtricksjr(article_title, seo_keywords, language):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=8000
    )

    def load_prompt_template(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            print(f"Unicode decoding error for file: {file_path}. Trying different encoding.")
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return None
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    # Adjust the relative path to point directly to the file from the current directory
    prompt_file_path = os.path.join('Prompt-templates', 'Mathtricksjr', 'article.txt')
    prompt_template = load_prompt_template(prompt_file_path)

    if prompt_template is None:
        return None

    # Ensure JSON structure in the prompt
    command = f'''
    Generate an article for "{article_title}" in "{language}" using these keywords: "{seo_keywords}". 
    Respond ONLY in valid JSON format like this:
    {{
        "title": "Sample Title",
        "content": "Article content goes here.",
        "keywords": ["keyword1", "keyword2"]
    }}
    '''

    def generate_lesson_plan(command):
        prompt = prompt_template.replace("{context}", command)
        try:
            response = llm.invoke(prompt)
            return response
        except Exception as e:
            print(f"Error generating lesson plan: {e}")
            return None

    output = generate_lesson_plan(command)
    if output is None:
        return None

    output_content = output.content if hasattr(output, 'content') else str(output)
    print("Raw Output:", output_content)  # Debug: Check raw output before JSON parsing

    # Try to decode JSON directly without unnecessary replacements
    try:
        article = json.loads(output_content)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None

    return article
