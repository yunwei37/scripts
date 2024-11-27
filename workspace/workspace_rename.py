import os
from pathlib import Path
import tempfile
import json
import subprocess
import yaml
from docx import Document
import pdfplumber

# Set up logging
def extract_text(file_path):
    """Extract text from a file based on its type."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.txt', '.md']:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    elif ext == '.pdf':
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ''
                for page in pdf.pages:
                    text += page.extract_text() or ''
            return text  # Limit to 2400 characters
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return "Error extracting text from PDF."
    elif ext in ['.doc', '.docx']:
        try:
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            return text  # Limit to 2400 characters
        except Exception as e:
            print(f"Error extracting text from Word document: {e}")
            return "Error extracting text from Word document."
    # for image files, try to extract text from the image
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
        return "This is a image file, see the image file for more information."
    else:
        return "This is a binary file."

def get_ai_filename(file_path, gen_struct_path):
    """Ask AI to generate a better filename for the file"""
    content = extract_text(str(file_path))
    original_suffix = file_path.suffix  # Get the original file extension
    
    # Read the template
    try:
        with open('.github/prompts/workspace_rename.md.template', 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print("Template file not found")
        return None

    # Schema for filename generation (updated to not include extension)
    schema = {
        "type": "object",
        "properties": {
            "new_filename": {
                "type": "string",
                "description": "New filename without extension"
            },
            "reason": {
                "type": "string",
                "description": "Reason for the suggested filename"
            }
        },
        "required": ["new_filename", "reason"],
        "additionalProperties": False
    }

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_input:
        prompt = template.format(
            file_name=file_path.name,
            file_content=content[:30000]
        )
        temp_input.write(prompt)
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_schema:
        json.dump(schema, temp_schema)
        schema_file = temp_schema.name

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_output:
        temp_output_path = temp_output.name

    try:
        cmd = [
            'python', gen_struct_path,
            temp_input_path, temp_output_path, schema_file
        ]
        
        # Add image path if it's an image
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            cmd.extend(['--image', str(file_path)])

        subprocess.run(cmd, check=True)

        with open(temp_output_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
            
        # Add the original extension to the new filename
        if result and result.get('new_filename'):
            result['new_filename'] = result['new_filename'].rstrip('.') + original_suffix
            
        return result
    except Exception as e:
        print(f"Error during AI filename generation: {e}")
        return None
    finally:
        os.unlink(temp_input_path)
        os.unlink(temp_output_path)
        os.unlink(schema_file)

def should_skip_file(file_path, workspace_dir):
    """Check if file should be skipped based on various criteria
    Args:
        file_path: absolute Path object of the file
        workspace_dir: absolute Path object of workspace directory
    """
    # Get relative path from workspace directory
    try:
        relative_path = file_path.relative_to(workspace_dir)
    except ValueError:
        print(f"Error: {file_path} is not in workspace directory")
        return True

    # Skip files larger than 10MB
    # if file_path.stat().st_size > 10 * 1024 * 1024:
    #     print(f"Skipping {relative_path}: File too large")
    #     return True
        
    # Skip system files
    if any(part.startswith('.') for part in relative_path.parts):
        print(f"Skipping {relative_path}: System file/directory")
        return True
        
    # Skip common binary/executable files
    binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin'}
    if file_path.suffix.lower() in binary_extensions:
        print(f"Skipping {relative_path}: Binary file")
        return True
        
    return False

def process_workspace():
    workspace_dir = Path("workspace").resolve()
    if not workspace_dir.exists():
        print("Workspace directory not found")
        return

    gen_struct_path = '.github/scripts/ai/gen_struct.py'

    # Process each file in workspace recursively
    for root, dirs, files in os.walk(workspace_dir):
        for filename in files:
            file_path = Path(root) / filename
            print(f"Processing: {file_path}")

            # Check if file should be skipped
            if should_skip_file(file_path, workspace_dir):
                continue

            # Get AI suggested filename
            result = get_ai_filename(file_path, gen_struct_path)
            
            if result and result.get('new_filename'):
                new_name = result['new_filename']
                new_path = file_path.parent / new_name
                
                # Rename the file
                try:
                    file_path.rename(new_path)
                    print(f"Renamed {file_path.name} to {new_name}")
                    print(f"Reason: {result.get('reason', 'No reason provided')}")
                except Exception as e:
                    print(f"Error renaming {file_path}: {e}")

    print("Workspace processing completed")

if __name__ == "__main__":
    process_workspace()