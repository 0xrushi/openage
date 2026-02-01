#!/usr/bin/env python3
"""
Test script for Python game control.

Run this while openage game is running to test spawning units.
"""

import sys
import os
import time
import subprocess

# Add build directory to Python path (this is where compiled modules are)
build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '.bin/g++-debug-Oauto-sanitize-none')
sys.path.insert(0, build_dir)

# Import game control directly from build directory
import openage.gamestate.game_control as gc

spawn_unit = gc.spawn_unit
is_game_active = gc.is_game_active


def check_game_process():
    """Check if openage game process is running."""
    try:
        # Look for openage main process
        result = subprocess.run(
            ['pgrep', '-f', 'openage.*main'],
            capture_output=True,
            text=True
        )
        running = result.returncode == 0
        print(f"[DEBUG] Game process check: {running}")
        return running
    except Exception as e:
        print(f"[DEBUG] Could not check process: {e}")
        return False


def test_game_active():
    """Test if game is active."""
    print("=" * 60)
    print("Testing: Is game active?")
    print("=" * 60)

    # Check via process
    import subprocess
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'openage.*main'],
            capture_output=True,
            text=True
        )
        process_running = result.returncode == 0
        print(f"[DEBUG] Game process running: {process_running}")
    except Exception as e:
        print(f"[DEBUG] Could not check process: {e}")
        process_running = False

    # Check via Python API
    try:
        active = is_game_active()
        print(f"[DEBUG] Python is_game_active(): {active}")
    except Exception as e:
        print(f"[DEBUG] Could not call is_game_active(): {e}")
        active = False

    # Use either check
    running = active or process_running

    if not running:
        print("\n❌ No game is currently running!")
        print("Please start the game first:")
        print("  cd /home/doraemon/Documents/openage/bin")
        print("  ./run main --modpacks hd_base")
        print("\nTIP: Make sure you're using the freshly compiled build!")
        return False

    print("\n✅ Game is running!")
    return True


def test_spawn_single():
    """Test spawning a single unit."""
    print("\n" + "=" * 60)
    print("Testing: Spawn single unit")
    print("=" * 60)

    try:
        entity_id = spawn_unit(
            nyan_entity="hd_base.data.game_entity.generic.knight.knight.Knight",
            owner=0,
            ne=10.0,
            se=10.0,
            up=0.0
        )

        print(f"✅ Spawned unit with ID: {entity_id}")
        return True

    except Exception as e:
        print(f"❌ Failed to spawn unit: {e}")
        return False


def test_spawn_army():
    """Test spawning multiple units."""
    print("\n" + "=" * 60)
    print("Testing: Spawn army (10 units)")
    print("=" * 60)

    spawned = 0
    failed = 0

    for i in range(10):
        try:
            entity_id = spawn_unit(
                nyan_entity="hd_base.data.game_entity.generic.knight.knight.Knight",
                owner=0,
                ne=10.0 + i * 2,
                se=10.0 + i * 2,
                up=0.0
            )

            print(f"✅ Spawned unit {i+1}/10 (ID: {entity_id})")
            spawned += 1
            time.sleep(0.5)  # Small delay between spawns

        except Exception as e:
            print(f"❌ Failed to spawn unit {i+1}/10: {e}")
            failed += 1

    print(f"\nSpawned: {spawned}, Failed: {failed}")
    return spawned > 0


def test_spawn_circle():
    """Test spawning units in a circle pattern."""
    print("\n" + "=" * 60)
    print("Testing: Spawn units in circle (20 units)")
    print("=" * 60)

    import math

    center_x, center_y = 20.0, 20.0
    radius = 10.0

    spawned = 0
    for i in range(20):
        angle = (2 * math.pi * i) / 20
        ne = center_x + radius * math.cos(angle)
        se = center_y + radius * math.sin(angle)

        try:
            entity_id = spawn_unit(
                nyan_entity="hd_base.data.game_entity.generic.knight.knight.Knight",
                owner=0,
                ne=ne,
                se=se,
                up=0.0
            )

            print(f"✅ Spawned unit {i+1}/20 at ({ne:.1f}, {se:.1f}) (ID: {entity_id})")
            spawned += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"❌ Failed to spawn unit {i+1}/20: {e}")

    print(f"\nSpawned: {spawned}/20")
    return spawned > 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("Openage Python Game Control Test")
    print("=" * 60)

    # Test 1: Check if game is active
    if not test_game_active():
        sys.exit(1)

    # Test 2: Spawn single unit
    if not test_spawn_single():
        print("\n❌ Single unit test failed!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

    # Ask if user wants to run more tests
    print("\nDo you want to run more tests?")
    print("  1. Spawn army (10 units)")
    print("  2. Spawn circle (20 units)")
    print("  3. Exit")

    try:
        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            test_spawn_army()
        elif choice == "2":
            test_spawn_circle()
        else:
            print("Exiting...")
    except KeyboardInterrupt:
        print("\n\nExiting...")


if __name__ == "__main__":
    main()
