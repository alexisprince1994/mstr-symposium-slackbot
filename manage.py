from flask_script import Manager
from src import app
import unittest

manager = Manager(app)

@manager.command
def test():
	"""
	Runs tests without discovery
	"""

	tests = unittest.TestLoader().discover('tests', pattern='test*.py')
	result = unittest.TextTestRunner(verbosity=2).run(tests)

	if result.wasSuccessful():
		return 0
	return 1

if __name__ == "__main__":
	manager.run()