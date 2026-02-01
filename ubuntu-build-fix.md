# Ubuntu Build Fix for openage

On Ubuntu 64-bit systems, libraries are located in `/usr/lib/x86_64-linux-gnu/` but CMake expects them in `/usr/lib/`. This causes build failures with errors like:

```
No rule to make target '/usr/lib/libopusfile.so', needed by 'libopenage/libopenage.so.0'
```

## Solution

Create symlinks for all shared and static libraries:

```bash
# Symlink all .so files
sudo bash -c 'for lib in /usr/lib/x86_64-linux-gnu/*.so; do ln -sf "$lib" "/usr/lib/$(basename $lib)" 2>/dev/null; done'

# Symlink all .a files  
sudo bash -c 'for lib in /usr/lib/x86_64-linux-gnu/*.a; do ln -sf "$lib" "/usr/lib/$(basename $lib)" 2>/dev/null; done'
```

## Alternative (manual)

If you prefer to create symlinks individually:

```bash
sudo ln -sf /usr/lib/x86_64-linux-gnu/libopusfile.so /usr/lib/libopusfile.so
sudo ln -sf /usr/lib/x86_64-linux-gnu/libopus.so /usr/lib/libopus.so
sudo ln -sf /usr/lib/x86_64-linux-gnu/libutil.a /usr/lib/libutil.a
sudo ln -sf /usr/lib/x86_64-linux-gnu/librt.a /usr/lib/librt.a
# ... and so on for each missing library
```

After creating the symlinks, run:

```bash
make -j14
```

The build should now complete successfully.

---

# Python API for Programmatic Unit Control

A Python API has been added to control openage game units programmatically without requiring mouse input. This is useful for automation, testing, and scripting.

## Installation

The API is now part of openage codebase. After building:

```bash
cd bin
python3
```

## Usage

### Basic Import

```python
from openage.gamestate import spawn_unit, spawn_unit_by_name, UNIT_TYPES
```

### Spawn Unit by FQON (Fully Qualified Nyan Object Name)

```python
entity_id = spawn_unit(
    nyan_entity="hd_base.data.game_entity.generic.knight.knight.Knight",
    modpacks=["hd_base"],
    owner=0,
    ne=10.0,
    se=10.0,
    up=0.0,
)
print(f"Spawned entity with ID: {entity_id}")
```

### Spawn Unit by Common Name (Simplified)

```python
from openage.gamestate import spawn_unit_by_name

# Spawn an archer
archer_id = spawn_unit_by_name(
    "archer",
    modpacks=["hd_base"],
    ne=15.0,
    se=15.0,
)

# Spawn a knight
knight_id = spawn_unit_by_name(
    "knight",
    modpacks=["hd_base"],
    ne=20.0,
    se=20.0,
)
```

### Available Unit Types

```python
from openage.gamestate import UNIT_TYPES

print(UNIT_TYPES.keys())
# Output: dict_keys(['knight', 'archer', 'monk', 'villager', 'barracks', 'castle'])
```

### Example: Spawn Multiple Units

```python
from openage.gamestate import spawn_unit_by_name

# Spawn an army of knights
for i in range(5):
    knight_id = spawn_unit_by_name(
        "knight",
        modpacks=["hd_base"],
        ne=5.0 + i * 2,
        se=10.0 + i * 2,
    )
    print(f"Spawned knight #{i+1} with ID: {knight_id}")
```

## API Reference

### `spawn_unit(nyan_entity, modpacks, owner, ne, se, up, asset_dir, cfg_dir)`

Spawn a unit at the specified position.

- `nyan_entity` (str): Fully qualified nyan object name
- `modpacks` (list[str]): List of modpacks to load
- `owner` (int): Owner player ID (default: 0)
- `ne` (float): North-East coordinate (default: 5.0)
- `se` (float): South-East coordinate (default: 5.0)
- `up` (float): Up/height coordinate (default: 0.0)
- `asset_dir` (str): Asset directory path (optional)
- `cfg_dir` (str): Config directory path (optional)

Returns: `int` - The entity ID of the spawned unit

### `spawn_unit_by_name(unit_name, **kwargs)`

Spawn a unit by common name using predefined shortcuts.

- `unit_name` (str): Common unit name (e.g., "knight", "archer", "monk")
- `**kwargs`: Additional arguments passed to `spawn_unit()`

Returns: `int` - The entity ID of the spawned unit

### `UNIT_TYPES`

Dictionary mapping common unit names to fully qualified nyan object names.

Available shortcuts:
- `"knight"` - Knight unit
- `"archer"` - Archer unit
- `"monk"` - Monk unit
- `"villager"` - Villager unit
- `"barracks"` - Barracks building
- `"castle"` - Castle building

## Important Notes

1. **Temporary Simulation (Current Limitation)**: The current API creates a temporary simulation for spawning units that immediately exits. Entities spawned this way **don't persist in a running game instance**. You won't see the spawned units visually because they're created in a temporary simulation that's destroyed immediately after spawning.

   **To spawn units in the actual running game**, you would need to:
   - Modify `Engine` to expose the running `GameSimulation` to Python
   - Store a global reference to the live simulation
   - Create Cython bindings to send spawn/move events to that simulation
   - Handle threading issues between Python and the game loop

   This requires significant C++ modifications to the engine architecture.

2. **What the Current API Does**:
   - Useful for: Testing unit creation, validating nyan entity names, position verification
   - Not useful for: Controlling the actual running game
   - The spawned entities exist only for milliseconds before the simulation exits

3. **Modpacks Required**: You must have required modpacks converted and available in your assets folder (e.g., `hd_base`).

4. **Position Validity**: Ensure that spawn coordinates (ne, se) are within map boundaries (default map is 20x20, so valid range is 0-19 for each coordinate).

## Future Enhancements

The following features require extensive C++ modifications:

### Full Python-to-Game Integration (Advanced)

To spawn/move/select units in a running game directly from Python, you need:

**1. C++ Changes (Partially Complete)**:
- ✅ Created `libopenage/gamestate/global_simulation.h/cpp` - Global simulation accessor
- ✅ Modified `libopenage/engine/engine.cpp` - Sets/clears global reference
- ✅ Modified `libopenage/engine/engine.h` - Forward declarations
- ✅ Created `libopenage/gamestate/simulation.pxd` - Cython bindings

**2. Additional Work Needed**:
- ⏳ Create Cython bindings for `EventLoop`
- ⏳ Expose `Spawner` and `Commander` to Python
- ⏳ Create `spawn_unit()` that uses live simulation (not temporary)
- ⏳ Create `move_unit()` that sends MOVE commands via `Commander`
- ⏳ Create `select_unit()` that calls `Controller::set_selected()`
- ⏳ Handle threading between Python and game loop
- ⏳ Create `libopenage/time/time_loop.pxd`
- ⏳ Create `libopenage/cvar/cvar.pxd`
- ⏳ Create `libopenage/assets/mod_manager.pxd`

Once complete, usage would be:
```python
from openage.gamestate import get_live_game

# Get access to running game
game = get_live_game()

# Spawn unit that persists in running game
entity_id = game.spawn_unit("knight", ne=10, se=10)

# Move an existing unit
game.move_unit(entity_id, ne=20, se=20)

# Select a unit
game.select_unit(entity_id)
```

### Quick Solution (Available Now)

Use built-in game controls:
- **Ctrl+Left Click** - Spawn units (cycles through types)
- **Right Click** - Move selected units
- **Left Click** - Select units
- **Drag Left Click** - Select multiple units

### Test Unit Types

Use `python_game_control.py` script to validate units:
```bash
cd /home/doraemon/Documents/openage/bin
python3 /home/doraemon/Documents/openage/python_game_control.py
```

This tests that all unit types work without requiring full game.

## Example Script

See `game_api_example.py` in the project root for a complete working example demonstrating all features.

**Important**: The example script must be run from the compiled `bin` directory:

```bash
cd /home/doraemon/Documents/openage/bin
python3 /home/doraemon/Documents/openage/game_api_example.py
```

The API modules are compiled and installed in the `bin` directory, so Python needs to be run from there to find them.

### Simple Test Script

For quick validation, use `simple_game_control.py`:

```bash
python3 /home/doraemon/Documents/openage/simple_game_control.py
```

This script tests all unit types and shows you what's available.
