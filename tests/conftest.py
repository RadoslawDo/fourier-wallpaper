def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true",
                     help="write the generated wallpapers to tests/golden instead of comparing with them")
