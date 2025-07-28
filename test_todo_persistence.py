#!/usr/bin/env python3
"""Test script for todo persistence functionality using TodoManager"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.katalyst.katalyst_core.utils.todo_persistence import TodoManager

def test_todo_persistence():
    print("Testing Todo Persistence with TodoManager...")
    
    # Test 1: Create TodoManager and clear existing todos
    print("\n1. Creating TodoManager and clearing existing todos...")
    manager = TodoManager()
    if manager.clear():
        print("✓ Todos cleared successfully")
    else:
        print("✗ Failed to clear todos")
    
    # Test 2: Create test todos using TodoManager methods
    print("\n2. Creating test todos...")
    manager.add("Implement feature X", status="pending", priority="high", todo_id="1")
    manager.add("Fix bug Y", status="in_progress", priority="medium", todo_id="2")
    manager.add("Write documentation", status="completed", priority="low", todo_id="3")
    manager.add("Review PR", status="pending", priority="high", todo_id="4")
    
    print(f"✓ Created {len(manager.todos)} todos")
    
    # Test 3: Verify todos were saved
    print("\n3. Verifying persistence...")
    new_manager = TodoManager()
    if new_manager.load():
        print(f"✓ Loaded {len(new_manager.todos)} todos from disk")
        for todo in new_manager.todos:
            print(f"   - [{todo['status']}] {todo['content']}")
    else:
        print("✗ Failed to load todos")
    
    # Test 4: Get summary
    print("\n4. Getting todo summary...")
    summary = manager.get_summary()
    print("Summary:")
    print(summary)
    
    # Test 5: Test property accessors
    print("\n5. Testing property accessors...")
    print(f"   - Pending: {len(manager.pending)} tasks")
    print(f"   - In Progress: {len(manager.in_progress)} tasks")
    print(f"   - Completed: {len(manager.completed)} tasks")
    
    # Test 6: Update a todo
    print("\n6. Testing todo update...")
    updated = manager.update("1", status="in_progress")
    if updated:
        print(f"✓ Updated todo 1: {updated['content']} -> {updated['status']}")
    
    # Test 7: Test adding todo directly
    print("\n7. Testing direct todo addition...")
    
    # Add new todo directly
    new_todo = manager.add("New task added directly", status="pending", priority="medium", todo_id="5")
    if new_todo:
        print(f"✓ Added new todo: {new_todo['content']}")
    else:
        print("✗ Failed to add new todo")
    
    # Verify persistence
    print(f"✓ Manager now has {len(manager.todos)} todos")
    
    # Test 8: Verify final state
    print("\n8. Verifying final state...")
    final_manager = TodoManager()
    final_manager.load()
    print(f"✓ Final todo count: {len(final_manager.todos)}")
    print(f"   - Pending: {len(final_manager.pending)}")
    print(f"   - In Progress: {len(final_manager.in_progress)}")
    print(f"   - Completed: {len(final_manager.completed)}")
    
    # Test 9: Test backward compatibility
    print("\n9. Testing backward compatibility functions...")
    from src.katalyst.katalyst_core.utils.todo_persistence import (
        load_todos, save_todos, get_todo_summary, clear_todos
    )
    
    legacy_todos = load_todos()
    if legacy_todos:
        print(f"✓ Legacy load_todos() returned {len(legacy_todos)} todos")
    
    legacy_summary = get_todo_summary()
    print("✓ Legacy get_todo_summary() works")
    
    # Test 10: Clean up
    print("\n10. Final cleanup...")
    if clear_todos():
        print("✓ Cleared todos using legacy function")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_todo_persistence()