import re
import os

def clean_base64_from_markdown(file_path):
    """Convert base64 image data in markdown file to text links."""
    try:
        # Read the markdown file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match markdown image with base64 data
        pattern = r'!\[([^\]]*)\]\(data:image/png;base64,[A-Za-z0-9+/=]+\)'
        
        # Replace base64 content with text link, keeping the alt text
        def replace_with_link(match):
            alt_text = match.group(1)
            if alt_text:
                return f'[{alt_text}]'
            return '[图片]'  # Default text if no alt text is found
            
        cleaned_content = re.sub(pattern, replace_with_link, content)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
            
        print(f"Successfully cleaned {file_path}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def process_directory(directory):
    """Process all markdown files in a directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') and '.github' not in root:
                file_path = os.path.join(root, file)
                clean_base64_from_markdown(file_path)

if __name__ == "__main__":
    # You can either process a single file
    # clean_base64_from_markdown("path/to/your/file.md")
    
    # Or process all markdown files in a directory
    process_directory("./") 