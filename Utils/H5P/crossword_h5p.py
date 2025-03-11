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


def update_crossword_json(generated_output: Dict[str, Any], theme: str) -> Dict[str, Any]:
    """
    Update the crossword puzzle JSON file with new generated content.
    
    Args:
        generated_output (dict): The output from the LLM containing clues and answers
        theme (str): The theme of the crossword puzzle
    
    Returns:
        dict: Updated JSON configuration
    """
    base_json_path = os.path.join('crossword_h5p.json')  # Change this to your crossword base file path

    try:
        with open(base_json_path, 'r', encoding='utf-8') as file:
            base_config = json.load(file)
    except Exception as e:
        print(f"Error reading base JSON file: {e}")
        return None

    # Update words with clues and extra clues
    base_config['words'] = []
    for clue_data in generated_output.get('clues', []):
        word_entry = {
            "fixWord": False,
            "orientation": "across",  # Adjust orientation if needed (across or down)
            "clue": clue_data['clue'],
            "answer": clue_data['answer'],
            "extraClue": {
                "params": {
                    "text": f"<p>{clue_data.get('extraClue', '')}</p>\n"
                },
                "library": "H5P.AdvancedText 1.1",
                "metadata": {
                    "contentType": "Text",
                    "license": "U",
                    "title": "Untitled Text"
                },
                "subContentId": str(uuid.uuid4())
            }
        }
        base_config['words'].append(word_entry)

    # Update task description
    base_config['taskDescription'] = f"<p>{generated_output.get('task_description', 'Solve the crossword puzzle')}</p>\n"

    unique_id = f"{theme.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    output_filename = f"{unique_id}_crossword.json"
    output_path = os.path.join('H5P_json', 'crossword_h5p', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(base_config, file, indent=4)
        print(f"Generated crossword JSON: {output_filename}")
    except Exception as e:
        print(f"Error saving updated JSON: {e}")
        return None

    return base_config


def crossword_puzzle_generation(theme, difficulty_level, num_clues, topic, chapter, description):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.5,
        max_tokens=4095
    )

    prompt_file_path = os.path.join('Prompt-templates', 'H5P','crossword_h5p.txt')

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

    def generate_crossword(topic, chapter, theme, difficulty_level, num_clues, description):
        prompt = prompt_template.replace("{theme}", theme).replace("{difficulty_level}", difficulty_level).replace("{num_clues}", str(num_clues)).replace("{topic}", str(topic)).replace("{chapter}", str(chapter)).replace("{description}", str(description))
        try:
            response = llm.predict(prompt)
            return response
        except Exception as e:
            print(f"Error generating crossword puzzle: {e}")
            return None

    output = generate_crossword(theme, difficulty_level, num_clues, topic, chapter, description)
    if output is None:
        return "Error: Unable to generate crossword puzzle."

    output = output.replace("json", "").replace("```", "")

    try:
        parsed_output = json.loads(output)
        updated_json = update_crossword_json(parsed_output, theme)
        create_new_h5p_with_updated_json(updated_json, theme)
        return updated_json
    except json.JSONDecodeError:
        print("Error: Generated output is not valid JSON")
        return "Error: Unable to parse crossword puzzle output."


def create_new_h5p_with_updated_json(updated_json: Dict[str, Any], theme: str):
    try:
        reference_h5p_path = 'crossword.h5p'  # Path to your reference crossword H5P file
        temp_dir = 'temp_h5p'
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        with zipfile.ZipFile(reference_h5p_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        content_json_path = os.path.join(temp_dir, 'content', 'content.json')

        try:
            with open(content_json_path, 'w', encoding='utf-8') as file:
                json.dump(updated_json, file, indent=4)
            print("Updated content.json with new crossword puzzle content.")
        except Exception as e:
            print(f"Error updating content.json: {e}")
            return

        unique_id = f"{theme.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        new_h5p_dir = os.path.join('H5P_CROSSWORD')
        os.makedirs(new_h5p_dir, exist_ok=True)
        new_h5p_path = os.path.join(new_h5p_dir, f'{unique_id}_crossword.h5p')

        with zipfile.ZipFile(new_h5p_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)

        print(f"New H5P file created: {new_h5p_path}")
        shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"Error creating H5P package: {e}")