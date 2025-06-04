def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Create a KATALYST.md file with instructions
/exit      Exit the agent
(Type your coding task or command below)
""")

def handle_init_command():
    with open("KATALYST.md", "w") as f:
        f.write("# Instructions for Katalyst\n")
    print("KATALYST.md created.") 