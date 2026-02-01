add_cython_modules(
	cpp_testing.pyx
	misc_cpp.pyx
)

add_py_modules(
	__init__.py
	doctest.py
	agent_control_test.py
	spawn_tool_wrapper_test.py
	list_processor.py
	main.py
	testing.py
	testlist.py
	benchmark.py
)
