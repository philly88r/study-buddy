import pytesseract
from PIL import Image

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_tesseract():
    try:
        # Print Tesseract version to confirm it's installed
        print("Tesseract Version:", pytesseract.get_tesseract_version())
        
        # You can uncomment and modify this part to test with an actual image
        # image_path = "path_to_your_test_image.png"
        # img = Image.open(image_path)
        # text = pytesseract.image_to_string(img)
        # print("Extracted text:", text)
        
        print("Tesseract is working correctly!")
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_tesseract()
