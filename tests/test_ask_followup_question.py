import pytest
from katalyst_agent.tools.ask_followup_question import ask_followup_question

def test_ask_followup_question_valid(monkeypatch):
    # Simulate user selecting the first suggestion
    monkeypatch.setattr('builtins.input', lambda _: '1')
    question = "What is your favorite color?"
    follow_up = ["Red", "Blue", "Green"]
    result = ask_followup_question(question, follow_up, auto_approve=True)
    assert '"question":' in result and '"answer":' in result
    assert 'Red' in result or 'Blue' in result or 'Green' in result

def test_ask_followup_question_custom(monkeypatch):
    # Simulate user typing a custom answer
    monkeypatch.setattr('builtins.input', lambda _: 'Purple')
    question = "What is your favorite color?"
    follow_up = ["Red", "Blue", "Green"]
    result = ask_followup_question(question, follow_up, auto_approve=True)
    assert 'Purple' in result

def test_ask_followup_question_missing_question():
    follow_up = ["Yes", "No"]
    result = ask_followup_question("", follow_up, auto_approve=True)
    assert 'No valid question' in result or 'error' in result.lower()

def test_ask_followup_question_missing_followup():
    question = "Proceed?"
    result = ask_followup_question(question, None, auto_approve=True)
    assert 'No follow_up suggestions' in result or 'error' in result.lower() 