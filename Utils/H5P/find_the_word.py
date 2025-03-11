import zipfile
import json
import os
import uuid
import shutil
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_PROD')

def update_word_search_json(generated_output: Dict[str, Any], theme: str) -> Dict[str, Any]:
    """
    Update the word search JSON file with new generated content.

    Args:
        generated_output (dict): The output from the LLM containing words and task description
        theme (str): The theme of the word search puzzle

    Returns:
        dict: Updated JSON configuration
    """
    base_json_path = os.path.join('find_the_word_h5p.json')

    try:
        with open(base_json_path, 'r', encoding='utf-8') as file:
            base_config = json.load(file)
    except Exception as e:
        print(f"Error reading base JSON file: {e}")
        return None

    unique_id = f"{theme.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"

    base_config['taskDescription'] = generated_output.get('task_description', '')
    base_config['wordList'] = ','.join(generated_output.get('words', []))
    base_config['l10n']['wordListHeader'] = f"{theme} Word Search"

    output_filename = f"{unique_id}_word_search.json"
    output_path = os.path.join('H5P_json', 'find_the_word_h5p', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(base_config, file, indent=4)
        print(f"Generated word search JSON: {output_filename}")
    except Exception as e:
        print(f"Error saving updated JSON: {e}")
        return None

    return base_config, output_path

def find_the_word_generation(topic, chapter, theme, difficulty_level, no_of_words, description):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=4095
    )

    prompt_file_path = os.path.join('Prompt-templates', 'H5P', 'find_the_word.txt')

    def load_prompt_template(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    prompt_template = load_prompt_template(prompt_file_path)
    if prompt_template is None:
        return "Error: Unable to load prompt template."

    def generate_word_search(topic, chapter, theme, difficulty_level, no_of_words, description):
        prompt = prompt_template.replace("{topic}", topic).replace("{chapter}", chapter).replace("{theme}", theme).replace("{difficulty_level}", difficulty_level).replace("{no_of_words}", str(no_of_words)).replace("{description}", description)
        try:
            response = llm.predict(prompt)
            return response
        except Exception as e:
            print(f"Error generating word search puzzle: {e}")
            return None

    output = generate_word_search(topic, chapter, theme, difficulty_level, no_of_words, description)
    if output is None:
        return "Error: Unable to generate word search puzzle."

    output = output.replace("json", "").replace("```", "")

    try:
        parsed_output = json.loads(output)
        updated_json, json_file_path = update_word_search_json(parsed_output, theme)
        create_new_h5p_with_updated_json(updated_json, theme, json_file_path)
        return updated_json
    except json.JSONDecodeError:
        print("Error: Generated output is not valid JSON")
        return "Error: Unable to parse word search puzzle output."

def create_new_h5p_with_updated_json(updated_json: Dict[str, Any], theme: str, json_file_path: str):
    try:
        reference_h5p_path = 'find-the-words.h5p'  # Update this with your actual path
        temp_dir = 'temp_h5p'
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        with zipfile.ZipFile(reference_h5p_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        content_json_path = os.path.join(temp_dir, 'content', 'content.json')

        try:
            with open(content_json_path, 'w', encoding='utf-8') as file:
                json.dump(updated_json, file, indent=4)
            print("Updated content.json with new word search content.")
        except Exception as e:
            print(f"Error updating content.json: {e}")
            return

        unique_id = f"{theme.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        new_h5p_dir = os.path.join('H5P_FIND_THE_WORD')
        os.makedirs(new_h5p_dir, exist_ok=True)
        new_h5p_path = os.path.join(new_h5p_dir, f'{unique_id}_word_search.h5p')

        with zipfile.ZipFile(new_h5p_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)

        print(f"New H5P file created: {new_h5p_path}")
        shutil.rmtree(temp_dir)

        # Delete the JSON file after creating the H5P package
        if os.path.exists(json_file_path):
            os.remove(json_file_path)
            print(f"Deleted temporary JSON file: {json_file_path}")

    except Exception as e:
        print(f"Error creating H5P package: {e}")