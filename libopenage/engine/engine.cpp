// Copyright 2023-2024 the openage authors. See copying.md for legal info.

#include "engine.h"

#include <chrono>
#include <fcntl.h>
#include <sstream>
#include <vector>
#include <future>
#include <memory>
#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>

#include "log/log.h"
#include "gamestate/component/internal/commands/types.h"
#include "gamestate/types.h"
#include "log/message.h"

#include "coord/phys.h"
#include "cvar/cvar.h"
#include "event/event_loop.h"
#include "gamestate/component/internal/ownership.h"
#include "gamestate/component/internal/position.h"
#include "gamestate/component/types.h"
#include "gamestate/event/send_command.h"
#include "gamestate/event/spawn_entity.h"
#include "gamestate/game.h"
#include "gamestate/game_entity.h"
#include "gamestate/game_state.h"
#include "gamestate/simulation.h"
#include "presenter/presenter.h"
#include "time/clock.h"
#include "time/time_loop.h"


namespace openage::engine {

Engine::Engine(mode mode,
               const util::Path &root_dir,
               const std::vector<std::string> &mods,
               const renderer::window_settings &window_settings) :
	running{true},
	run_mode{mode},
	root_dir{root_dir},
	threads{} {
	log::log(INFO
	         << "launching engine with root directory"
	         << root_dir);

	// read and apply the configuration files
	this->cvar_manager = std::make_shared<cvar::CVarManager>(this->root_dir["cfg"]);
	cvar_manager->load_all();

	// time loop
	this->time_loop = std::make_shared<time::TimeLoop>();

	// game simulation
	// this is run in the main thread
	this->simulation = std::make_shared<gamestate::GameSimulation>(this->root_dir,
	                                                               this->cvar_manager,
	                                                               this->time_loop);
	this->simulation->set_modpacks(mods);

	// presenter (optional)
	if (this->run_mode == mode::FULL) {
		this->presenter = std::make_shared<presenter::Presenter>(this->root_dir,
		                                                         this->simulation,
		                                                         this->time_loop);
	}

	// spawn thread to run time loop
	this->threads.emplace_back([&]() {
		this->time_loop->run();

		this->time_loop.reset();
	});

	// if presenter is used, run it in a separate thread
	if (this->run_mode == mode::FULL) {
		this->threads.emplace_back([&]() {
			this->presenter->run(window_settings);

			// Make sure that the presenter gets destructed in the same thread
			// otherwise OpenGL complains about missing contexts
			this->presenter.reset();
			this->running = false;
		});
	}

	// Start IPC server for cross-process spawning
	this->ipc_socket_fd = -1;
	this->ipc_server_thread = std::jthread([this]() {
		this->run_ipc_server();
	});

	log::log(INFO << "Using " << this->threads.size() + 2 << " threads "
	              << "(" << std::jthread::hardware_concurrency() << " available)");
}

void Engine::run_ipc_server() {
	// Socket path
	const char *socket_path = "/tmp/openage_spawn.sock";

	// Remove old socket file if exists
	unlink(socket_path);

	// Create Unix domain socket
	this->ipc_socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (this->ipc_socket_fd < 0) {
		log::log(MSG(err) << "Failed to create IPC socket");
		return;
	}

	// Bind to socket path
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);

	if (bind(this->ipc_socket_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
		log::log(MSG(err) << "Failed to bind IPC socket");
		close(this->ipc_socket_fd);
		return;
	}

	// Listen for connections
	if (listen(this->ipc_socket_fd, 5) < 0) {
		log::log(MSG(err) << "Failed to listen on IPC socket");
		close(this->ipc_socket_fd);
		return;
	}

	// Set socket to non-blocking
	fcntl(this->ipc_socket_fd, F_SETFL, O_NONBLOCK);

	log::log(MSG(info) << "IPC socket server started: " << socket_path);

	// Accept connections loop
	char buffer[2048];
	while (this->running) {
		// Accept client connection (with timeout)
		struct timeval tv;
		tv.tv_sec = 0;
		tv.tv_usec = 100000; // 100ms timeout

		fd_set readfds;
		FD_ZERO(&readfds);
		FD_SET(this->ipc_socket_fd, &readfds);

		int select_result = select(this->ipc_socket_fd + 1, &readfds, nullptr, nullptr, &tv);

		if (select_result > 0) {
			int client_fd = accept(this->ipc_socket_fd, nullptr, nullptr);
			if (client_fd >= 0) {
				// Read command
				ssize_t bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);
				if (bytes_read > 0) {
					buffer[bytes_read] = '\0';

					std::string command(buffer);

					auto split = [](const std::string &s, char delim) {
						std::vector<std::string> parts;
						parts.reserve(8);
						size_t start = 0;
						while (true) {
							size_t pos = s.find(delim, start);
							if (pos == std::string::npos) {
								parts.push_back(s.substr(start));
								break;
							}
							parts.push_back(s.substr(start, pos - start));
							start = pos + 1;
						}
						return parts;
					};

					std::string response = "0|ERROR: Invalid command";
					auto parts = split(command, '|');

					// spawn|<nyan_entity>|<owner>|<ne>|<se>|<up>
					if (parts.size() >= 6 && parts[0] == "spawn") {
						try {
							auto nyan_entity = parts[1];
							auto owner = static_cast<size_t>(std::stoull(parts[2]));
							double ne = std::stod(parts[3]);
							double se = std::stod(parts[4]);
							double up = std::stod(parts[5]);

							coord::phys3 pos{coord::phys_t{ne}, coord::phys_t{se}, coord::phys_t{up}};

							// Wait for the simulation to be ready
							auto game = this->simulation->get_game();
							if (!game) {
								response = "0|ERROR: Game not started yet";
							}
							else {
								// Create a promise to receive the entity ID from the event handler
								auto result_promise = std::make_shared<std::promise<uint64_t>>();
								auto result_future = result_promise->get_future();

								// Build event parameters
								openage::event::EventHandler::param_map::map_t params{
									{"position", pos},
									{"owner", owner},
									{"nyan_entity", nyan_entity},
									{"result_promise", result_promise},
								};

								// Queue the spawn event on the event loop
								auto current_time = this->time_loop->get_clock()->get_time();
								this->simulation->get_event_loop()->create_event(
									"game.spawn_entity",
									this->simulation->get_spawner(),
									game->get_state(),
									current_time,
									params);

							// Wait for the event to be processed (with timeout)
							auto status = result_future.wait_for(std::chrono::seconds(10));
								if (status == std::future_status::ready) {
									uint64_t entity_id = result_future.get();
									response = std::to_string(entity_id)
									           + "|SUCCESS: Spawned " + nyan_entity;
								}
								else {
									response = "0|ERROR: Spawn timed out for " + nyan_entity;
								}
							}
						}
						catch (const std::exception &e) {
							response = std::string{"0|ERROR: Spawn parse failed: "} + e.what();
						}
					}
					// move|<entity_id>|<ne>|<se>|<up>
					else if (parts.size() >= 5 && parts[0] == "move") {
						try {
							auto entity_id = static_cast<uint64_t>(std::stoull(parts[1]));
							double ne = std::stod(parts[2]);
							double se = std::stod(parts[3]);
							double up = std::stod(parts[4]);

							coord::phys3 target{coord::phys_t{ne}, coord::phys_t{se}, coord::phys_t{up}};

							auto game = this->simulation->get_game();
							if (!game) {
								response = "0|ERROR: Game not started yet";
							}
							else {
							auto gstate = game->get_state();
							const auto &entities = gstate->get_game_entities();
								auto id = static_cast<gamestate::entity_id_t>(entity_id);
								if (!entities.contains(id)) {
									response = "0|ERROR: Entity does not exist";
								}
								else {
									auto ent = entities.at(id);
									if (!ent) {
										response = "0|ERROR: Entity is null";
									}
									else if (!ent->has_component(gamestate::component::component_t::COMMANDQUEUE)) {
										response = "0|ERROR: Entity has no command queue";
									}
									else if (!ent->has_component(gamestate::component::component_t::MOVE)) {
										response = "0|ERROR: Entity cannot move";
									}
									else {
										openage::event::EventHandler::param_map::map_t params{
										{"type", gamestate::component::command::command_t::MOVE},
										{"target", target},
										{"entity_ids", std::vector<gamestate::entity_id_t>{id}},
									};

									auto current_time = this->time_loop->get_clock()->get_time();
									this->simulation->get_event_loop()->create_event(
										"game.send_command",
										std::static_pointer_cast<openage::event::EventEntity>(this->simulation->get_commander()),
										gstate,
										current_time,
										params);

									response = "1|SUCCESS: Move queued";
									}
								}
							}
						}
						catch (const std::exception &e) {
							response = std::string{"0|ERROR: Move parse failed: "} + e.what();
						}
					}
					// stop|<entity_id>
					else if (parts.size() >= 2 && (parts[0] == "stop" || parts[0] == "idle")) {
						try {
							auto entity_id = static_cast<uint64_t>(std::stoull(parts[1]));

							auto game = this->simulation->get_game();
							if (!game) {
								response = "0|ERROR: Game not started yet";
							}
							else {
								auto gstate = game->get_state();
							const auto &entities = gstate->get_game_entities();
								auto id = static_cast<gamestate::entity_id_t>(entity_id);
								if (!entities.contains(id)) {
									response = "0|ERROR: Entity does not exist";
								}
								else {
									auto ent = entities.at(id);
									if (!ent) {
										response = "0|ERROR: Entity is null";
									}
									else if (!ent->has_component(gamestate::component::component_t::COMMANDQUEUE)) {
										response = "0|ERROR: Entity has no command queue";
									}
									else {
										openage::event::EventHandler::param_map::map_t params{
										{"type", gamestate::component::command::command_t::IDLE},
										{"entity_ids", std::vector<gamestate::entity_id_t>{id}},
									};

									auto current_time = this->time_loop->get_clock()->get_time();
									this->simulation->get_event_loop()->create_event(
										"game.send_command",
										std::static_pointer_cast<openage::event::EventEntity>(this->simulation->get_commander()),
										gstate,
										current_time,
										params);

									response = "1|SUCCESS: Stop queued";
									}
								}
							}
						}
						catch (const std::exception &e) {
							response = std::string{"0|ERROR: Stop parse failed: "} + e.what();
						}
					}
					// attack|<entity_id>|<target_entity_id>
					else if (parts.size() >= 3 && parts[0] == "attack") {
						try {
							auto entity_id = static_cast<uint64_t>(std::stoull(parts[1]));
							auto target_id = static_cast<uint64_t>(std::stoull(parts[2]));

							auto game = this->simulation->get_game();
							if (!game) {
								response = "0|ERROR: Game not started yet";
							}
							else {
								auto gstate = game->get_state();
								const auto &entities = gstate->get_game_entities();
								auto id = static_cast<gamestate::entity_id_t>(entity_id);
								auto tid = static_cast<gamestate::entity_id_t>(target_id);
								if (!entities.contains(id)) {
									response = "0|ERROR: Entity does not exist";
								}
								else if (!entities.contains(tid)) {
									response = "0|ERROR: Target entity does not exist";
								}
								else {
									auto ent = entities.at(id);
									auto target_ent = entities.at(tid);
									if (!ent) {
										response = "0|ERROR: Entity is null";
									}
									else if (!target_ent) {
										response = "0|ERROR: Target entity is null";
									}
									else if (!ent->has_component(gamestate::component::component_t::COMMANDQUEUE)) {
										response = "0|ERROR: Entity has no command queue";
									}
									else if (!ent->has_component(gamestate::component::component_t::MOVE)) {
										response = "0|ERROR: Entity cannot move";
									}
									else if (!target_ent->has_component(gamestate::component::component_t::POSITION)) {
										response = "0|ERROR: Target entity has no position";
									}
									else {
										// Resolve target position and queue a MOVE toward it.
										auto now = this->time_loop->get_clock()->get_time();
										auto target_pos_comp = std::dynamic_pointer_cast<gamestate::component::Position>(
											target_ent->get_component(gamestate::component::component_t::POSITION));
										auto target_pos = target_pos_comp->get_positions().get(now);

										openage::event::EventHandler::param_map::map_t params{
											{"type", gamestate::component::command::command_t::MOVE},
											{"target", target_pos},
											{"entity_ids", std::vector<gamestate::entity_id_t>{id}},
										};

										auto current_time = this->time_loop->get_clock()->get_time();
										this->simulation->get_event_loop()->create_event(
											"game.send_command",
											std::static_pointer_cast<openage::event::EventEntity>(this->simulation->get_commander()),
											gstate,
											current_time,
											params);

										response = "1|SUCCESS: Attack-move queued toward entity " + std::to_string(target_id);
									}
								}
							}
						}
						catch (const std::exception &e) {
							response = std::string{"0|ERROR: Attack parse failed: "} + e.what();
						}
					}
					// patrol|<entity_id>|<ne1>|<se1>|<up1>[|<ne2>|<se2>|<up2>...]
					else if (parts.size() >= 5 && parts[0] == "patrol") {
						try {
							auto entity_id = static_cast<uint64_t>(std::stoull(parts[1]));

							// Parse waypoints (groups of 3 coordinates after entity_id).
							size_t coord_count = parts.size() - 2;
							if (coord_count % 3 != 0 || coord_count < 3) {
								response = "0|ERROR: Patrol needs at least one waypoint (groups of ne,se,up)";
							}
							else {
								std::vector<coord::phys3> waypoints;
								waypoints.reserve(coord_count / 3);
								for (size_t i = 2; i < parts.size(); i += 3) {
									double ne = std::stod(parts[i]);
									double se = std::stod(parts[i + 1]);
									double up = std::stod(parts[i + 2]);
									waypoints.push_back(coord::phys3{coord::phys_t{ne}, coord::phys_t{se}, coord::phys_t{up}});
								}

								auto game = this->simulation->get_game();
								if (!game) {
									response = "0|ERROR: Game not started yet";
								}
								else {
									auto gstate = game->get_state();
									const auto &entities = gstate->get_game_entities();
									auto id = static_cast<gamestate::entity_id_t>(entity_id);
									if (!entities.contains(id)) {
										response = "0|ERROR: Entity does not exist";
									}
									else {
										auto ent = entities.at(id);
										if (!ent) {
											response = "0|ERROR: Entity is null";
										}
										else if (!ent->has_component(gamestate::component::component_t::COMMANDQUEUE)) {
											response = "0|ERROR: Entity has no command queue";
										}
										else if (!ent->has_component(gamestate::component::component_t::MOVE)) {
											response = "0|ERROR: Entity cannot move";
										}
										else {
											auto current_time = this->time_loop->get_clock()->get_time();
											// Ensure deterministic ordering: events at equal times can execute in any order.
											// We schedule the queue-clear at current_time and the subsequent MOVE commands
											// at monotonically increasing times.
											auto step = time::time_t::from_double(0.001);

											// First clear the queue.
											openage::event::EventHandler::param_map::map_t idle_params{
												{"type", gamestate::component::command::command_t::IDLE},
												{"entity_ids", std::vector<gamestate::entity_id_t>{id}},
											};
											this->simulation->get_event_loop()->create_event(
												"game.send_command",
												std::static_pointer_cast<openage::event::EventEntity>(this->simulation->get_commander()),
												gstate,
												current_time,
												idle_params);

											// Then queue a MOVE for each waypoint.
											for (size_t i = 0; i < waypoints.size(); ++i) {
												auto t = current_time + (step * (i + 1));
												const auto &wp = waypoints[i];
												openage::event::EventHandler::param_map::map_t move_params{
													{"type", gamestate::component::command::command_t::MOVE},
													{"target", wp},
													{"entity_ids", std::vector<gamestate::entity_id_t>{id}},
												};
												this->simulation->get_event_loop()->create_event(
													"game.send_command",
													std::static_pointer_cast<openage::event::EventEntity>(this->simulation->get_commander()),
													gstate,
													t,
													move_params);
											}

											response = "1|SUCCESS: Patrol queued with "
											           + std::to_string(waypoints.size()) + " waypoint(s)";
										}
									}
								}
							}
						}
						catch (const std::exception &e) {
							response = std::string{"0|ERROR: Patrol parse failed: "} + e.what();
						}
					}
					// state|entities
					else if (parts.size() >= 2 && parts[0] == "state" && parts[1] == "entities") {
						auto game = this->simulation->get_game();
						if (!game) {
							response = "0|ERROR: Game not started yet";
						}
						else {
							// Optional filters: key=value pairs after "state|entities".
							// Supported keys: owner, id, has, limit
							bool filter_owner = false;
							size_t owner_filter = 0;
							bool filter_id = false;
							uint64_t id_filter = 0;
							std::string has_filter;
							bool filter_limit = false;
							size_t limit = 0;

							for (size_t i = 2; i < parts.size(); ++i) {
								auto &kv = parts[i];
								auto eq = kv.find('=');
								if (eq == std::string::npos) {
									continue;
								}
								auto key = kv.substr(0, eq);
								auto value = kv.substr(eq + 1);
								try {
									if (key == "owner") {
										owner_filter = static_cast<size_t>(std::stoull(value));
										filter_owner = true;
									}
									else if (key == "id") {
										id_filter = static_cast<uint64_t>(std::stoull(value));
										filter_id = true;
									}
									else if (key == "has") {
										has_filter = value;
									}
									else if (key == "limit") {
										limit = static_cast<size_t>(std::stoull(value));
										filter_limit = true;
									}
								}
								catch (...) {
									// ignore bad filter
								}
							}

							auto gstate = game->get_state();
							auto now = this->time_loop->get_clock()->get_time();

							std::ostringstream ss;
							ss << "{\"entities\":[";
							bool first = true;
							size_t emitted = 0;
							for (const auto &kv : gstate->get_game_entities()) {
								const auto &entity = kv.second;
								if (!entity) {
									continue;
								}

								if (filter_id && entity->get_id() != static_cast<gamestate::entity_id_t>(id_filter)) {
									continue;
								}

								if (!entity->has_component(gamestate::component::component_t::POSITION)) {
									continue;
								}
								if (!entity->has_component(gamestate::component::component_t::OWNERSHIP)) {
									continue;
								}
								auto pos_comp = std::dynamic_pointer_cast<gamestate::component::Position>(
									entity->get_component(gamestate::component::component_t::POSITION));
								auto owner_comp = std::dynamic_pointer_cast<gamestate::component::Ownership>(
									entity->get_component(gamestate::component::component_t::OWNERSHIP));

								if (!pos_comp || !owner_comp) {
									continue;
								}

								auto pos = pos_comp->get_positions().get(now);
								auto owner = owner_comp->get_owners().get(now);

								if (filter_owner && static_cast<size_t>(owner) != owner_filter) {
									continue;
								}

								bool can_move = entity->has_component(gamestate::component::component_t::MOVE);
								bool selectable = entity->has_component(gamestate::component::component_t::SELECTABLE);

								if (!has_filter.empty()) {
									if (has_filter == "move" && !can_move) {
										continue;
									}
									if (has_filter == "selectable" && !selectable) {
										continue;
									}
								}

								if (!first) {
									ss << ',';
								}
								first = false;

								ss << "{\"id\":" << entity->get_id();
								ss << ",\"owner\":" << owner;
								ss << ",\"can_move\":" << (can_move ? "true" : "false");
								ss << ",\"selectable\":" << (selectable ? "true" : "false");
								ss << ",\"pos\":{\"ne\":" << pos.ne.to_double();
								ss << ",\"se\":" << pos.se.to_double();
								ss << ",\"up\":" << pos.up.to_double() << "}}";

								++emitted;
								if (filter_limit && emitted >= limit) {
									break;
								}
							}
							ss << "]}";

							response = "1|" + ss.str();
						}
					}

					write(client_fd, response.c_str(), response.length());
					close(client_fd);
				}
			}
		}

		// Small sleep to reduce CPU usage
		std::this_thread::sleep_for(std::chrono::milliseconds(50));
	}

	// Cleanup
	close(this->ipc_socket_fd);
	unlink(socket_path);
	log::log(MSG(info) << "IPC socket server stopped");
}

void Engine::loop() {
	// Run the main game simulation loop:
	this->simulation->run();

	// After stopping, clean up the simulation
	this->simulation.reset();

	if (this->run_mode != mode::FULL) {
		this->running = false;
	}
}

} // namespace openage::engine
