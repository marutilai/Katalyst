def main():
    numbers = input("Enter numbers separated by spaces: ")
    numbers_list = numbers.split()
    total = 0
    for num in numbers_list:
        try:
            total += float(num)
        except ValueError:
            print(f"'{num}' is not a valid number and will be ignored.")
    print(f"The sum of the entered numbers is: {total}")

if __name__ == "__main__":
    main()
