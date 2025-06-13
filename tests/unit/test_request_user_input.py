import pytest
from src.coding_agent.tools.request_user_input import request_user_input
import json


def test_request_user_input_valid(monkeypatch):
    # Simulate user selecting the first suggestion
    monkeypatch.setattr("builtins.input", lambda _: "1")
    question = "What is your favorite color?"
    suggestions = ["Red", "Blue", "Green"]
    result = request_user_input(question, suggestions)
    data = json.loads(result)
    assert data["question_to_ask_user"] == question
    assert data["user_final_answer"] in suggestions


def test_request_user_input_custom(monkeypatch):
    # Simulate user typing a custom answer
    monkeypatch.setattr("builtins.input", lambda _: "Purple")
    question = "What is your favorite color?"
    suggestions = ["Red", "Blue", "Green"]
    result = request_user_input(question, suggestions)
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
