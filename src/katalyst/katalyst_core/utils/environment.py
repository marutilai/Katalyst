import os


def ensure_openai_api_key(user_input_fn=input):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "\n[ERROR] OpenAI API key not found!\n"
            "Please set the OPENAI_API_KEY environment variable or add it to your .env file in this directory.\n"
            "You can get an API key from https://platform.openai.com/account/api-keys\n"
        )
        key = user_input_fn(
            "Enter your OpenAI API key (or leave blank to exit): "
        ).strip()
        if key:
            with open(".env", "a") as f:
                f.write(f"\nOPENAI_API_KEY={key}\n")
            print("API key saved to .env. Please restart Katalyst.")
            exit(1)
        exit(1)
