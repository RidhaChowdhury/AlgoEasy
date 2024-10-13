import json
import sys
import io
import traceback
import inspect
from typing import get_type_hints


def cast_inputs(solution, inputs):
    """Cast inputs based on the type hints from the solution function."""
    signature = inspect.signature(solution)
    parameters = signature.parameters

    casted_inputs = []
    for i, (name, param) in enumerate(parameters.items()):
        hint = param.annotation  # Get the type hint
        if hint != inspect._empty:  # If a type hint is provided
            casted_inputs.append(hint(inputs[i]))  # Cast input to the hinted type
        else:
            casted_inputs.append(inputs[i])  # No hint, use the input as-is

    return casted_inputs


def run_tests(solution):
    test_cases = generate_test_cases()
    results = []

    for inputs, expected in test_cases:
        # Cast inputs based on type hints in the solution function
        casted_inputs = cast_inputs(solution, inputs)

        # Reset stdout and stderr for each test case
        new_stdout = io.StringIO()
        new_stderr = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = new_stdout
        sys.stderr = new_stderr
        expected_str = str(expected)

        try:
            # Execute the user's solution with the casted inputs
            result = solution(*casted_inputs)

            # Convert the result to a string for comparison
            result_str = str(result)

            # Test case results with stdout/stderr for each test case
            results.append({
                'test_result': {
                    'inputs': inputs,
                    'expected': expected_str,
                    'result': result_str,
                    'passed': result_str == expected_str
                },
                'stdout': new_stdout.getvalue().strip().splitlines(),
                'stderr': new_stderr.getvalue().strip().splitlines()
            })
        except Exception as e:
            # Capture user error tracebacks only
            user_error = traceback.format_exc(limit=0)
            results.append({
                'test_result': {
                    'inputs': inputs,
                    'expected': expected_str,
                    'result': str(e),
                    'passed': False
                },
                'stdout': new_stdout.getvalue().strip().splitlines(),
                'stderr': [user_error.strip()]  # Capture the error as stderr
            })

        finally:
            # Restore the original stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    return results


def generate_test_cases():
    # Load the test cases from the JSON file
    with open("test_cases.json", "r") as f:
        test_cases = json.load(f)
    return test_cases


if __name__ == "__main__":
    import user_code  # Directly import the user's code

    # Run the tests and capture results
    test_results = run_tests(user_code.solution)

    # Combine the test results into a JSON object
    combined_result = {
        'test_cases': test_results
    }

    # Output the combined JSON object
    print(json.dumps(combined_result))
