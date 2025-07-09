from PIL import Image
import pytesseract

# Optional: set the path to the tesseract executable if not in PATH
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

image = Image.open("Screenshot_28.png")
text = pytesseract.image_to_string(image, lang='eng+rus')

print(text)