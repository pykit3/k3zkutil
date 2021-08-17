import doctest

import k3zkutil


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3zkutil))
    return tests
