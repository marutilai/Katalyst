from tests.functional.test_framework import KatalystTestCase, KatalystTestRunner

# Basic Tests
basic_tests = [
    KatalystTestCase(
        name="read_readme_first_lines",
        task="read the first 5 lines of readme and tell me the first python command in that",
        expected_output="python",  # Assuming the first Python command contains "python"
    ),
    KatalystTestCase(
        name="create_math_project",
        task="create a project folder mytest and inside create 3 python scripts one for adding one for multiple one for dividing and call all of those from one main script",
        expected_files={
            "mytest/add.py": "def add",
            "mytest/multiply.py": "def multiply",
            "mytest/divide.py": "def divide",
            "mytest/main.py": "import add\nimport multiply\nimport divide",
        },
    ),
    KatalystTestCase(
        name="color_preference",
        task="Ask me for my favorite color with suggestions 'red', 'green', 'blue'. Then tell me my choice using attempt_completion.",
        expected_output="request_user_input",  # Should use request_user_input tool
        auto_approve=False,  # Requires user interaction
    ),
    KatalystTestCase(
        name="file_operations",
        task="List all files in the current directory. Then, ask me for a filename and content, and write that to the specified file. Only proceed if I confirm.",
        expected_output="list_files",  # Should use list_files tool
        auto_approve=False,  # Requires user interaction
    ),
    KatalystTestCase(
        name="todo_plan",
        task="Draft a plan for a simple to-do list application and save it as todo_plan.md. Ask me if I want to include user authentication in the plan.",
        expected_files={"todo_plan.md": "To-Do List Application"},
        auto_approve=False,  # Requires user interaction
    ),
    KatalystTestCase(
        name="project_documentation",
        task="Understand the current project structure and ask me what I want to document first. Then, create a basic test_plan.md with a title 'Project Plan'",
        expected_files={"test_plan.md": "Project Plan"},
        auto_approve=False,  # Requires user interaction
    ),
]

# Search and Read Tests
search_read_tests = [
    KatalystTestCase(
        name="search_katalyst_in_md",
        task="Search for all occurrences of the word 'Katalyst' in any .md files in the current directory and its subdirectories. Then, read the first 5 lines of README.md.",
        expected_output="Katalyst",  # Should find occurrences of Katalyst
    ),
    KatalystTestCase(
        name="find_python_imports",
        task="Find all Python files (.py) in the katalyst/coding_agent/nodes directory that import the KatalystState. For each match, show me the line number and the matching line. Then, ask me if I want to see the full content of katalyst/coding_agent/nodes/invoke_llm.py.",
        expected_output="KatalystState",
        auto_approve=False,  # Requires user interaction
    ),
]

# Code Analysis Tests
code_analysis_tests = [
    KatalystTestCase(
        name="list_write_file_definitions",
        task="List all function and class definitions in katalyst.coding_agent.tools/write_to_file.py. Then, read the content of the write_to_file function itself from that file.",
        expected_output="def write_to_file",
    ),
    KatalystTestCase(
        name="analyze_utils_directory",
        task="Analyze the katalyst/coding_agent/utils directory. For each Python file, list its function definitions. Then ask me which function from xml_parser.py I'd like to understand better.",
        expected_output="def",
        auto_approve=False,  # Requires user interaction
    ),
]

# Diff and Syntax Tests
diff_syntax_tests = [
    KatalystTestCase(
        name="change_logger_name",
        task="Read the file katalyst/coding_agent/utils/logger.py. Then, propose a diff to change the _LOGGER_NAME from 'coding_agent' to 'katalyst_logger'. Apply this diff only after my confirmation. Ensure the syntax is still valid after the change.",
        expected_output="diff",
        auto_approve=False,  # Requires user interaction
    ),
    KatalystTestCase(
        name="add_agent_version",
        task="In katalyst/coding_agent/main.py, inside the repl function's else block where initial_state is created, add a new key-value pair: 'agent_version': '1.0.0'. Use the apply_source_code_diff tool. Show me the proposed diff and apply it after my confirmation.",
        expected_output="agent_version",
        auto_approve=False,  # Requires user interaction
    ),
]

# Command Execution Tests
command_tests = [
    KatalystTestCase(
        name="list_and_create_file",
        task="List all files in the current directory using a shell command. Then, create a new file named test_output.txt containing the text 'Hello from Katalyst' using the write_to_file tool.",
        expected_files={"test_output.txt": "Hello from Katalyst"},
    )
]

# Complex Tests
complex_tests = [
    KatalystTestCase(
        name="refactor_logger_function",
        task="I want to refactor the get_logger function in katalyst/coding_agent/utils/logger.py. First, search for all files in katalyst/coding_agent that import get_logger from this path. Then, read the get_logger function itself. After that, ask me for the new desired name for this function. Finally, use apply_source_code_diff to rename the function.",
        expected_output="get_logger",
        auto_approve=False,  # Requires user interaction
    ),
    KatalystTestCase(
        name="create_and_run_sandbox",
        task="Create a new Python file katalyst/coding_agent/experiments/sandbox.py. Inside this file, write a simple function called greet(name: str) -> str that returns f'Hello, {name}!'. After writing the file, execute it with the command python katalyst/coding_agent/experiments/sandbox.py if it had a main block to print a greeting (modify it to do so if needed, then execute).",
        expected_files={"katalyst/coding_agent/experiments/sandbox.py": "def greet"},
    ),
]


def run_all_test_suites():
    """Run all test suites and generate a report."""
    all_tests = (
        basic_tests
        + search_read_tests
        + code_analysis_tests
        + diff_syntax_tests
        + command_tests
        + complex_tests
    )

    runner = KatalystTestRunner(all_tests)
    results = runner.run_all_tests()
    runner.generate_report()

    return results


if __name__ == "__main__":
    run_all_test_suites()
