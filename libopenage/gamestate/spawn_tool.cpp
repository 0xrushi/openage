// Copyright 2024-2024 © openage authors. See copying.md for legal info.

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>


// Socket path (same as Engine)
const char *socket_path = "/tmp/openage_spawn.sock";


int main(int argc, char **argv) {
	if (argc < 2) {
		std::cout << "Openage Unit Spawner - C++ CLI Tool\n";
		std::cout << "================================\n\n";
		std::cout << "Usage: " << argv[0] << " <entity_type> [owner] [ne] [se] [up]\n\n";
		std::cout << "Arguments:\n";
		std::cout << "  entity_type  Fully qualified nyan object name (e.g., hd_base.data.game_entity.generic.knight.knight.Knight)\n";
		std::cout << "  owner        Owner player ID (default: 0)\n";
		std::cout << "  ne            North-East coordinate (default: 5.0)\n";
		std::cout << "  se            South-East coordinate (default: 5.0)\n";
		std::cout << "  up            Up/height coordinate (default: 0.0)\n\n";
		std::cout << "Examples:\n";
		std::cout << "  " << argv[0] << " hd_base.data.game_entity.generic.knight.knight.Knight 0 10 10\n";
		std::cout << "  " << argv[0] << " hd_base.data.game_entity.generic.archer.archer.Archer 0 20 20\n";
		std::cout << "  " << argv[0] << " hd_base.data.game_entity.generic.monk.monk.Monk\n\n";
		std::cout << "Returns:\n";
		std::cout << "  Entity ID (as integer) on success\n";
		std::cout << "  Exit code 1 on failure\n\n";
		return 0;
	}

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

	// Create socket
	int sock_fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (sock_fd < 0) {
		std::cerr << "ERROR: Failed to create socket\n";
		return 1;
	}

	// Connect to server
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);

	if (connect(sock_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
		std::cerr << "ERROR: Cannot connect to game! Is it running?\n";
		std::cerr << "Socket path: " << socket_path << "\n";
		close(sock_fd);
		return 1;
	}

	// Build spawn command: spawn|<nyan_entity>|<owner>|<ne>|<se>|<up>
	std::string command = "spawn|" + std::string(nyan_entity) + "|" +
	                       std::to_string(owner) + "|" +
	                       std::to_string(ne) + "|" +
	                       std::to_string(se) + "|" +
	                       std::to_string(up);

	// Send command
	ssize_t bytes_written = write(sock_fd, command.c_str(), command.length());
	if (bytes_written < 0) {
		std::cerr << "ERROR: Failed to send command\n";
		close(sock_fd);
		return 1;
	}

	// Read response
	char buffer[2048];
	ssize_t bytes_read = read(sock_fd, buffer, sizeof(buffer) - 1);
	if (bytes_read > 0) {
		buffer[bytes_read] = '\0';

		// Parse response: <entity_id>|<status_message>
		std::string response(buffer);
		size_t pos = response.find('|');
		if (pos != std::string::npos) {
			std::string entity_id_str = response.substr(0, pos);
			std::string message = response.substr(pos + 1);

			uint64_t entity_id = std::atoll(entity_id_str.c_str());

			// Print result to stdout (no error prefix)
			std::cout << "Entity ID: " << entity_id << "\n";
			std::cout << "Message: " << message << "\n";

			if (entity_id > 0) {
				return 0;
			} else {
				return 1;
			}
		}
	} else {
		std::cerr << "ERROR: No response from game\n";
	}

	close(sock_fd);
	return 0;
}
