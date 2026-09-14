"""
Frontend DOM & JavaScript ID Integrity Test
Verifies:
1. Zero duplicate IDs in index.html.
2. All interactive elements (buttons, inputs, selects) and DOM IDs referenced in JS files exist in index.html.
"""
import re
import glob
import os

def test_no_duplicate_ids_in_index_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    all_html_ids = re.findall(r'id=["\']([^"\']+)["\']', html_content)
    duplicates = [x for x in set(all_html_ids) if all_html_ids.count(x) > 1]
    assert len(duplicates) == 0, f"Duplicate HTML IDs found: {duplicates}"


def test_js_referenced_ids_exist_in_html():
    js_files = glob.glob('src/js/*.js')
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))

    for js_path in js_files:
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Match $(...), setText(...), setCss(...), setAttr(...), getElementById(...)
        fn_ids = re.findall(r'(?:\$|setText|setCss|setAttr|getElementById)\s*\(\s*[\'"`]([a-zA-Z0-9_\-]+)[\'"`]', js_content)
        query_ids = re.findall(r'querySelector(?:All)?\s*\(\s*[\'"`]#([a-zA-Z0-9_\-]+)[\'"`]\s*\)', js_content)
        
        all_referenced_ids = set(fn_ids + query_ids)
        missing = all_referenced_ids - html_ids
        assert len(missing) == 0, f"In {js_path}, referenced IDs not in HTML: {missing}"
