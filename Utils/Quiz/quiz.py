from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def generate_quiz(subject, grade, difficulty, topic, description, number,image_url=None):
    """Generate quiz based on input parameters."""
        
    def load_prompt_template(file_path):
        """Load the prompt template from a file, with error handling."""
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
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=4095
    )

    # Debugging: check current directory
    print("Current working directory:", os.getcwd())
    
    # Load the prompt template
    prompt_file_path = os.path.join('Prompt-templates', 'Quiz', 'quiz.txt')
    print(f"Loading prompt template from: {prompt_file_path}")
    prompt_template = load_prompt_template(prompt_file_path)
    
    if prompt_template is None:
        return "Error: Unable to load prompt template."

    # Replace placeholders in the template
    prompt = prompt_template.replace("{subject}", str(subject))\
                            .replace("{grade}", str(grade))\
                            .replace("{difficulty}", str(difficulty))\
                            .replace("{topic}", str(topic))\
                            .replace("{description}", str(description))\
                            .replace("{number}", str(number))

    # Generate the quiz from the prompt
    response = llm.predict(prompt)
    print(f"Raw response: {response}")  # Debugging: check the raw response

    # Clean the response if needed
    output = response.replace("```json", "").replace("```", "").strip()
    print(f"Cleaned output: {output}")  # Check if the cleaning worked

    try:
        output_json = json.loads(output)  # Try to parse the cleaned response into JSON
        print(f"Generated quiz JSON: {json.dumps(output_json, indent=4)}")  # Pretty print the JSON
        return output_json  # Return the JSON to the caller
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return "Error: Unable to generate quiz."
