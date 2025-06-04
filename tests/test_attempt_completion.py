from katalyst_agent.tools.attempt_completion import attempt_completion

def test_attempt_completion_success():
    result = attempt_completion('Task complete!')
    assert 'success' in result and 'Task complete!' in result

def test_attempt_completion_missing():
    result = attempt_completion('')
    assert 'error' in result or 'No valid' in result 