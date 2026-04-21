import re
with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'_\([\'"](.*?)[\'"]\)', text)
for m in matches:
    print(m)
