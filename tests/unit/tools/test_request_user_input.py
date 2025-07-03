import pytest
from katalyst.coding_agent.tools.request_user_input import request_user_input
import json

pytestmark = pytest.mark.unit


def test_request_user_input_valid(monkeypatch):
    # Use the legacy user_input_fn parameter to avoid terminal menu issues
    def mock_input(prompt):
        return "1"  # Select first option
    
    question = "What is your favorite color?"
    suggestions = ["Red", "Blue", "Green"]
    result = request_user_input(question, suggestions, user_input_fn=mock_input)
    data = json.loads(result)
    assert data["question_to_ask_user"] == question
    assert data["user_final_answer"] == "Red"


def test_request_user_input_custom(monkeypatch):
    # Use the legacy user_input_fn parameter to enter custom answer
    inputs = ["4", "Purple"]  # Select "Let me enter my own answer", then enter "Purple"
    input_iter = iter(inputs)
    
    def mock_input(prompt):
        return next(input_iter)
    
    question = "What is your favorite color?"
    suggestions = ["Red", "Blue", "Green"]
    result = request_user_input(question, suggestions, user_input_fn=mock_input)
    data = json.loads(result)
    assert data["user_final_answer"] == "Purple"


def test_request_user_input_missing_question():
    suggestions = ["Yes", "No"]
    result = request_user_input("", suggestions)
    data = json.loads(result)
    assert data["user_final_answer"].startswith("[ERROR]")


def test_request_user_input_missing_suggestions():
    question = "Proceed?"
    result = request_user_input(question, None)
    data = json.loads(result)
    assert data["user_final_answer"].startswith("[ERROR]")
