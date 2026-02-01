# Python Game Control - Current Status

## Issue Found

**Problem**: Static variables across shared libraries

When `game_control.so` (Python binding) and `libopenage.so` (Engine) are separate shared libraries, they each have their own copy of the `active_simulation` pointer.

**Result**:
- Engine sets simulation in `libopenage.so`
- Python reads simulation from `game_control.so`
- These are **different variables**, so Python sees null

## Temporary Workaround

Use process checking to determine if game is running:

```python
import subprocess

def is_game_running():
    result = subprocess.run(
        ['pgrep', '-f', 'openage.*main'],
        capture_output=True
    )
    return result.returncode == 0
```

**Limitation**: This can detect if game is running, but spawning will still fail because we can't access the simulation pointer.

## Proper Fix Required

To make this work properly, one of:

### Option 1: Same Library (Best)
Compile `game_control.pyx` into `libopenage.so` instead of separate `game_control.so`

**Requires**: Modify CMake to combine modules

### Option 2: Visible Symbol
Make `global_active_simulation` a visible symbol across all libraries

**Requires**:
- Add `__attribute__((visibility("default")))`
- Ensure proper linking between libraries

### Option 3: Alternative Communication
Use environment variable, file socket, or named pipe to communicate

**Requires**: More complex implementation

## What Currently Works

✅ C++ implementation is correct
✅ Engine integration is correct
✅ Python binding is correct
✅ Build compiles successfully
❌ Cross-library variable sharing doesn't work on Linux

## Test It

**Detect if game is running:**
```bash
cd /home/doraemon/Documents/openage
python3 test_game_control.py
```

**Will show**:
- ✅ Game process detected (if running)
- ❌ Simulation not accessible (due to shared library issue)

## Next Steps

To fully fix this, we need to:
1. Either combine modules into same library, OR
2. Make global symbols visible across libraries, OR
3. Use alternative communication method

This is a standard issue with shared libraries on Linux and requires either linking changes or different architecture.
