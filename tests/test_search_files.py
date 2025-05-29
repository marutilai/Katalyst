import os
import shutil
from katalyst_agent.tools.search_files import regex_search_files

def setup_sample_dir():
    os.makedirs('test_search_dir', exist_ok=True)
    with open('test_search_dir/file1.py', 'w') as f:
        f.write('''
def foo():
    pass

class Bar:
    def baz(self):
        pass
''')
    with open('test_search_dir/file2.txt', 'w') as f:
        f.write('''
This is a text file.
foo bar baz
''')
    with open('test_search_dir/ignoreme.log', 'w') as f:
        f.write('Should not match this.')

def cleanup_sample_dir():
    shutil.rmtree('test_search_dir')

def test_python_function_search():
    print("Testing regex_search_files for 'def' in .py files...")
    args = {
        'path': 'test_search_dir',
        'regex': r'def ',
        'file_pattern': '*.py',
    }
    result = regex_search_files(args)
    print(result)
    assert '<match' in result
    assert 'def foo()' in result
    assert 'def baz(self):' in result

def test_no_match():
    print("Testing regex_search_files for a pattern that does not exist...")
    args = {
        'path': 'test_search_dir',
        'regex': r'not_in_file',
        'file_pattern': '*.py',
    }
    result = regex_search_files(args)
    print(result)
    assert 'No matches found' in result

if __name__ == "__main__":
    setup_sample_dir()
    try:
        test_python_function_search()
        test_no_match()
        print("All search_files tests passed.")
    finally:
        cleanup_sample_dir() 