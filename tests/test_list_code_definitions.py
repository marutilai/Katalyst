import os
import json
import pytest
from katalyst_agent.tools.list_code_definitions import list_code_definition_names

def write_sample_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

@pytest.fixture(autouse=True)
def cleanup_files():
    yield
    # Teardown: remove sample files if they exist
    for fname in ["test_sample.py", "test_sample.js"]:
        if os.path.exists(fname):
            os.remove(fname)

def test_python():
    py_code = '''
class MyClass:
    def method(self):
        pass

def my_function():
    pass
'''
    fname = 'test_sample.py'
    write_sample_file(fname, py_code)
    print(f"Testing Python file: {fname}")
    result = list_code_definition_names(fname)
    print(result)
    data = json.loads(result)
    defs = data['files'][0]['definitions']
    assert any(d['type'] == 'class' for d in defs)
    assert any(d['type'] == 'function' for d in defs)

def test_javascript():
    js_code = '''
class MyClass {
    method() {}
}
function myFunction() {}
'''
    fname = 'test_sample.js'
    write_sample_file(fname, js_code)
    print(f"Testing JavaScript file: {fname}")
    result = list_code_definition_names(fname)
    print(result)
    data = json.loads(result)
    defs = data['files'][0]['definitions']
    assert any(d['type'] == 'class' for d in defs)
    assert any(d['type'] == 'function' for d in defs) 