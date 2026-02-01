// Copyright 2023-2023 the openage authors. See copying.md for legal info.

#include "tests.h"

#include <memory>
#include <vector>

#include "assets/mod_manager.h"
#include "coord/phys.h"
#include "cvar/cvar.h"
#include "event/event_loop.h"
#include "gamestate/component/internal/activity.h"
#include "gamestate/component/internal/ownership.h"
#include "gamestate/component/internal/position.h"
#include "gamestate/component/types.h"
#include "gamestate/entity_factory.h"
#include "gamestate/event/drag_select.h"
#include "gamestate/event/process_command.h"
#include "gamestate/event/send_command.h"
#include "gamestate/event/spawn_entity.h"
#include "gamestate/event/wait.h"
#include "gamestate/game.h"
#include "gamestate/game_entity.h"
#include "gamestate/game_state.h"
#include "gamestate/map.h"
#include "gamestate/manager.h"
#include "gamestate/terrain_factory.h"
#include "log/log.h"
#include "log/message.h"
#include "time/clock.h"
#include "time/time_loop.h"

#include "gamestate/demo/demo_0.h"


namespace openage::gamestate::tests {

void simulation_demo(int demo_id, const util::Path &path) {
	switch (demo_id) {
	case 0:
		simulation_demo_0(path);
		break;

	default:
		log::log(MSG(err) << "Unknown renderer demo requested: " << demo_id << ".");
		break;
	}
}

uint64_t spawn_nyan_entity(const util::Path &path,
                           const std::vector<std::string> &modpacks,
                           const std::string &nyan_entity,
                           uint64_t owner_id,
                           double ne,
                           double se,
                           double up) {
	auto cvar = std::make_shared<cvar::CVarManager>(path);
	auto time_loop = std::make_shared<time::TimeLoop>();
	time_loop->start();

	auto event_loop = std::make_shared<openage::event::EventLoop>();
	auto entity_factory = std::make_shared<gamestate::EntityFactory>();
	auto terrain_factory = std::make_shared<gamestate::TerrainFactory>();

	// Register the event handlers required by the activity/command systems.
	// This mirrors the minimal setup that GameSimulation normally does.
	event_loop->add_event_handler(std::make_shared<gamestate::event::DragSelectHandler>());
	event_loop->add_event_handler(std::make_shared<gamestate::event::SpawnEntityHandler>(event_loop, entity_factory));
	event_loop->add_event_handler(std::make_shared<gamestate::event::SendCommandHandler>());
	event_loop->add_event_handler(std::make_shared<gamestate::event::ProcessCommandHandler>());
	event_loop->add_event_handler(std::make_shared<gamestate::event::WaitHandler>());

	auto converted_mod_dir = path / "assets" / "converted";
	auto mod_manager = std::make_shared<assets::ModManager>(converted_mod_dir);
	auto available_modpacks = mod_manager->enumerate_modpacks(converted_mod_dir);
	for (const auto &mod : available_modpacks) {
		mod_manager->register_modpack(mod);
	}

	// Always load the engine modpack and the requested extra modpacks.
	std::vector<std::string> mods{"engine"};
	mods.insert(mods.end(), modpacks.begin(), modpacks.end());
	mod_manager->activate_modpacks(mods);

	auto game = std::make_shared<gamestate::Game>(event_loop,
	                                              mod_manager,
	                                              entity_factory,
	                                              terrain_factory);
	auto state = game->get_state();

	// Ensure the owner exists.
	(void) state->get_player(owner_id);

	auto map = state->get_map();
	if (not map) {
		throw Error{MSG(err) << "No map has been initialized."};
	}

	coord::phys3 pos{coord::phys_t{ne}, coord::phys_t{se}, coord::phys_t{up}};
	auto map_size = map->get_size();
	if (not(pos.ne >= 0
	        and pos.ne < map_size[0]
	        and pos.se >= 0
	        and pos.se < map_size[1])) {
		throw Error{MSG(err) << "Spawn position is outside the map: " << pos
		                     << " (map size: " << map_size << ")"};
	}

	// Create entity and set basic components.
	auto entity = entity_factory->add_game_entity(event_loop, state, owner_id, nyan_entity);
	auto now = time_loop->get_clock()->get_time();

	auto entity_pos = std::dynamic_pointer_cast<component::Position>(
		entity->get_component(component::component_t::POSITION));
	entity_pos->set_position(now, pos);
	entity_pos->set_angle(now, coord::phys_angle_t::from_int(315));

	auto entity_owner = std::dynamic_pointer_cast<component::Ownership>(
		entity->get_component(component::component_t::OWNERSHIP));
	entity_owner->set_owner(now, owner_id);

	auto activity = std::dynamic_pointer_cast<component::Activity>(
		entity->get_component(component::component_t::ACTIVITY));
	activity->init(now);
	entity->get_manager()->run_activity_system(now);

	state->add_game_entity(entity);

	log::log(MSG(info) << "Spawned entity " << nyan_entity << " as id=" << entity->get_id()
	                   << " at " << pos << " (owner=" << owner_id << ")");

	time_loop->stop();
	return entity->get_id();
}

} // namespace openage::gamestate::tests
