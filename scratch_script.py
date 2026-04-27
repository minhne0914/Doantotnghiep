import re

filepath = 'd:/doanhieu/doanhieu/home/views.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'from django.utils.translation import gettext_lazy as _' not in content:
    content = content.replace('from django.shortcuts import render', 'from django.shortcuts import render\nfrom django.utils.translation import gettext_lazy as _')

content = re.sub(r'items\.append\(([\'\"].+?[\'\"])\)', r'items.append(_(\1))', content)
content = re.sub(r'advices\.append\(([\'\"].+?[\'\"])\)', r'advices.append(_(\1))', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
