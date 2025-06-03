def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Create a KATALYST.md file with instructions
/exit      Exit the agent
/mode      Change the current mode
(Type your coding task or command below)
""")

def handle_init_command():
    with open("KATALYST.md", "w") as f:
        f.write("# Instructions for Katalyst\n")
    print("KATALYST.md created.")

def handle_mode_command(user_input, project_state, save_project_state):
    # Robust /mode command: show current, set, or handle invalid input
    parts = user_input.split(" ", 1)
    if len(parts) == 1 and parts[0] == "/mode":
        print("Usage: /mode [architect|code] or /mode to see current.")
        return project_state
    elif len(parts) == 2:
        _, new_mode_str = parts
        new_mode = new_mode_str.strip().lower()
        if new_mode in ["architect", "code"]:
            save_project_state(project_state)
            print(f"Mode switched to: {new_mode}")
        else:
            print(f"Invalid mode: '{new_mode}'. Available modes: 'architect', 'code'.")
        return project_state
    else:
        print("Usage: /mode [architect|code] or /mode to see current.")
        return project_state 