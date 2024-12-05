from app import extract_text_from_image

# Path to the test text file
file_path = 'test_homework.txt'

# Test the text extraction function
text, error = extract_text_from_image(file_path)

if error:
    print(f"Error: {error}")
else:
    print(f"Extracted Text: {text}")
