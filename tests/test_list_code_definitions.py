import os
from katalyst_agent.tools.list_code_definitions import list_code_definition_names

def write_sample_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

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
    assert '<definition type="class"' in result
    assert '<definition type="function"' in result
    os.remove(fname)

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
    assert '<definition type="class"' in result
    assert '<definition type="function"' in result
    os.remove(fname)

if __name__ == "__main__":
    test_python()
    test_javascript()
    print("All tests passed.") 