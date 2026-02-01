add_sources(libopenage
    definitions.cpp
    entity_factory.cpp
	game_entity.cpp
    game_state.cpp
	game.cpp
	manager.cpp
    map.cpp
	player.cpp
    simulation.cpp
	terrain_chunk.cpp
    terrain_factory.cpp
    terrain_tile.cpp
	terrain.cpp
    types.cpp
	world.cpp
	universe.cpp
)

# Create spawn_tool executable
add_executable(spawn_tool
    spawn_tool.cpp
)

target_link_libraries(spawn_tool
    PRIVATE
    libopenage
)

# Install spawn_tool to bin directory
install(
    TARGETS spawn_tool
    RUNTIME DESTINATION bin
)

add_subdirectory(activity/)
add_subdirectory(api/)
add_subdirectory(component/)
add_subdirectory(demo/)
add_subdirectory(event/)
add_subdirectory(system/)
