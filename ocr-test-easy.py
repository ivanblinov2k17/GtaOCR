import easyocr
reader = easyocr.Reader(['en', 'ru'])
results = reader.readtext('Screenshot_28.png')

for bbox, text, confidence in results:
    print(f'Text: {text} | Confidence: {confidence:.2f}')