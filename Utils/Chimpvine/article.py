import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import json
# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY12')
def article_chimpvine(article_title, seo_keywords, language):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=8000
    )
    # Debugging: check current directory
    print("Current working directory:", os.getcwd())
    
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
    prompt_file_path = os.path.join('Prompt-templates','Chimpvine', 'article.txt')
    prompt_template = load_prompt_template(prompt_file_path)

    if prompt_template is None:
        return None  # Handle the error as needed

    command = f'''Generate me an article for "{article_title}" in language "{language}". Compulsorily use these keywords in the article: "{seo_keywords}".'''
    def generate_lesson_plan(command):
        prompt = prompt_template.replace("{context}", command)
        try:
            response = llm.invoke(prompt)
            return response
        except Exception as e:
            print(f"Error generating lesson plan: {e}")
            return None

    # Logic for MCQs with a single correct answer
    output = generate_lesson_plan(command)
    if output is None:
        return None  # Handle the error as needed
    output_content = output.content if hasattr(output, 'content') else str(output)
    # Clean up the lesson plan output
    output_content = output_content.replace("content='", "").replace("json", "").replace('\n', '')

    # print( output_content)
    
     # Try to decode JSON
    try:
        article = json.loads(output_content)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None
    
    return article