#!/usr/bin/env python3
"""
Simple test to check if simulation is active.
"""

import sys
import os

# Add build directory to path
build_dir = '/home/doraemon/Documents/openage/.bin/g++-debug-Oauto-sanitize-none'
sys.path.insert(0, build_dir)

print("Importing game_control...")
try:
    import openage.gamestate.game_control as gc
    print("✅ Imported successfully")
    print(f"   Available: {dir(gc)}")

    print("\nChecking is_game_active()...")
    result = gc.is_game_active()
    print(f"   Result: {result}")

    if result:
        print("\n✅ Game IS ACTIVE!")
        print("You can now spawn units.")
    else:
        print("\n❌ Game is NOT active!")
        print("Make sure you:")
        print("  1. Started game with: cd /home/doraemon/Documents/openage/bin && ./run main --modpacks hd_base")
        print("  2. Game has fully loaded (not just starting)")
        print("  3. Using the same build we just compiled")

except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)
