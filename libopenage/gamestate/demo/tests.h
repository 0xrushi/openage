// Copyright 2023-2023 the openage authors. See copying.md for legal info.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "../../util/compiler.h"
// pxd: from libopenage.util.path cimport Path
// pxd: from libcpp.string cimport string
// pxd: from libcpp.vector cimport vector
// pxd: from libc.stdint cimport uint64_t


namespace openage {
namespace util {
class Path;
} // namespace util

namespace gamestate::tests {

// pxd: void simulation_demo(int demo_id, Path path) except +
OAAPI void simulation_demo(int demo_id, const util::Path &path);

/**
 * Create a minimal gamestate instance, spawn a nyan entity, and return its ID.
 *
 * This is meant for prototyping Python-side tooling and is not a stable gameplay API.
 *
 * pxd:
 *
 * uint64_t spawn_nyan_entity(Path path,
 *                            vector[string] modpacks,
 *                            string nyan_entity,
 *                            uint64_t owner_id,
 *                            double ne,
 *                            double se,
 *                            double up) except +
 */
OAAPI uint64_t spawn_nyan_entity(const util::Path &path,
                                const std::vector<std::string> &modpacks,
                                const std::string &nyan_entity,
                                uint64_t owner_id,
                                double ne,
                                double se,
                                double up);

} // namespace gamestate::tests
} // namespace openage
