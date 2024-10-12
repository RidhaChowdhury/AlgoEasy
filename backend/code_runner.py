import json

def run_tests(solution):
    test_cases = generate_test_cases()
    results = []
    
    for inputs, expected in test_cases:
        try:
            result = solution(*inputs)
            results.append({
                'inputs': inputs,
                'expected': expected,
                'result': result,
                'passed': result == expected
            })
        except Exception as e:
            results.append({
                'inputs': inputs,
                'expected': expected,
                'result': str(e),
                'passed': False
            })
    
    return json.dumps(results)

def generate_test_cases():
    return [
        ((1,), "1"),
        ((3,), "Fizz"),
        ((5,), "Buzz"),
        ((15,), "FizzBuzz"),
        ((4,), "4")
    ]

if __name__ == "__main__":
    import user_code  # Directly import the user's code
    print(run_tests(user_code.solution))  # Run the tests on the user's solution
