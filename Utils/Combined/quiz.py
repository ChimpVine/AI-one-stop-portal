from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def generate_quiz(subject, grade, difficulty, topic, language):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=4095
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
    prompt_file_path=""
    
    prompt_file_path = os.path.join('Prompt-templates','Combined', 'quiz.txt')
    print(prompt_file_path)
    prompt_template = load_prompt_template(prompt_file_path)
    # print("Prompt template loaded:", prompt_template)

    if prompt_template is None:
        return "Error: Unable to load prompt template."
    
    print(subject, grade, difficulty, topic)

    def generate_quiz(subject, grade, difficulty, topic, language):
        prompt = prompt_template.replace("{subject}", str(subject))\
                        .replace("{grade}", str(grade))\
                        .replace("{difficulty}", str(difficulty))\
                        .replace("{topic}", str(topic))\
                        .replace("{language}",  str(language))

        # prompt = prompt_template.replace("{grade_level}", grade_level).replace("{math_topic}", math_topic).replace("{interest}", interest)
        try:
            response = llm.predict(prompt)
            return response
        except Exception as e:
            print(f"Error generating fun maths: {e}")
            return None

    # Logic for MCQs with a single correct answer
    output = generate_quiz(subject, grade, difficulty, topic, language)
    
    if output is None:
        return "Error: Unable to generate fun maths."

    # Clean up the lesson plan output
    output = output.replace("```", "").replace("json", "").replace("\n", "")
    # print("Cleaned Output:", output)
    output_json = json.loads(output)
    return output_json