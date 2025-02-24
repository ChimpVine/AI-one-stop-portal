import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Validate API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY12')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

def article_mathfun(subject, grade, difficulty, topic):
    """Generates a structured math article using OpenAI API."""
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=8000
    )

    prompt_file_path = os.path.join('Prompt-templates', 'new', 'new.txt')

    def load_prompt_template(file_path):
        """Loads the prompt template from a file with encoding handling."""
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

    # Load the prompt template
    prompt_template = load_prompt_template(prompt_file_path)
    if not prompt_template:
        return None

    # Replace placeholders in the prompt template
    try:
        prompt = prompt_template.replace(
            "{subject}", subject
        ).replace(
            "{grade}", str(grade)
        ).replace(
            "{difficulty}", difficulty
        ).replace(
            "{topic}", topic
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    def generate_article(prompt):
        """Generates the article using the LLM."""
        try:
            response = llm.predict(prompt) 
            return response.strip() if isinstance(response, str) else str(response).strip()
        except Exception as e:
            print(f"Error generating article: {e}")
            return None

    output = generate_article(prompt)
    if not output:
        return None

    # Extract valid JSON content using regex
    json_match = re.search(r'\{.*\}', output, re.DOTALL)
    if json_match:
        json_content = json_match.group()
        try:
            article = json.loads(json_content)
            return article
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            return None
    else:
        print("No valid JSON found in response.")
        return None

# Test the function with sample inputs
if __name__ == "__main__":
    subject = "Mathematics"
    grade = "8"
    difficulty = "Medium"
    topic = "data analysis"

    article = article_mathfun(subject, grade, difficulty, topic)
    print(json.dumps(article, indent=4) if article else "Failed to generate article.")
