// Copyright 2024-2024 © openage authors. See copying.md for legal info.

// Simple tool that attaches to running openage process and spawns units

#include <iostream>
#include <fstream>
#include <string>
#include <cstdlib>
#include <sys/stat.h>

// Find process PID by name
pid_t find_openage_pid() {
	FILE *pipe = popen("pgrep -f 'openage.*main'", "r");
	if (!pipe) {
		return 0;
	}

	char buffer[128];
	pid_t pid = 0;
	if (fgets(buffer, 128, pipe) != nullptr) {
		pid = std::atoi(buffer);
	}

	pclose(pipe);
	return pid;
}

int main(int argc, char **argv) {
	if (argc < 2) {
		std::cout << "Openage Unit Spawner - Attach to Running Process\n";
		std::cout << "=================================================\n\n";
		std::cout << "Usage: " << argv[0] << " <entity_type> [owner] [ne] [se] [up]\n\n";
		std::cout << "This tool attaches to the running openage process.\n";
		std::cout << "Make sure the game is running first!\n\n";
		return 0;
	}

	// Find openage process
	pid_t pid = find_openage_pid();
	if (pid == 0) {
		std::cerr << "ERROR: No running openage game found!\n";
		std::cerr << "Please start game first: cd bin && ./run main --modpacks hd_base\n";
		return 1;
	}

	std::cout << "Found running openage process: PID " << pid << "\n";

	// Parse arguments
	const char *nyan_entity = argv[1];
	uint64_t owner = 0;
	double ne = 5.0;
	double se = 5.0;
	double up = 0.0;

	if (argc >= 3) {
		owner = std::atoll(argv[2]);
	}
	if (argc >= 4) {
		ne = std::atof(argv[3]);
	}
	if (argc >= 5) {
		se = std::atof(argv[4]);
	}
	if (argc >= 6) {
		up = std::atof(argv[5]);
	}

	// Write spawn command to file for game to read
	std::ofstream cmd_file("/tmp/openage_spawn_" + std::to_string(pid) + ".cmd");
	if (!cmd_file.is_open()) {
		std::cerr << "ERROR: Could not create command file!\n";
		return 1;
	}

	cmd_file << nyan_entity << "\n";
	cmd_file << owner << "\n";
	cmd_file << ne << "\n";
	cmd_file << se << "\n";
	cmd_file << up << "\n";
	cmd_file.close();

	std::cout << "Spawn command written to file.\n";
	std::cout << "Note: Game needs to read this file (not yet implemented).\n";
	std::cout << "Entity: " << nyan_entity << "\n";
	std::cout << "Owner: " << owner << "\n";
	std::cout << "Position: (" << ne << ", " << se << ", " << up << ")\n";

	std::cout << "\n⚠️  Limitation: This requires game engine to periodically check for spawn commands.\n";
	std::cout << "   (File-based IPC approach - game polling not yet added)\n";

	return 0;
}
