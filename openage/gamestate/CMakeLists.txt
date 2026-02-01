add_cython_modules(
	api.pyx
	tests.pyx
)

# Note: game_control module needs to link to libopenage.so
# to access global variables. pyext_link_libraries() function
# has issues with path quoting. Manual linking may be needed.

add_py_modules(
	__init__.py
)
