def divide_two_numbers():
    try:
        num1 = float(input("Enter the first number: "))
        num2 = float(input("Enter the second number: "))
        if num2 == 0:
            print("Error: Division by zero is not allowed.")
            return
        result = num1 / num2
        print(f"Result of dividing {num1} by {num2} is {result}")
    except ValueError:
        print("Invalid input. Please enter valid numbers.")

if __name__ == "__main__":
    divide_two_numbers()
