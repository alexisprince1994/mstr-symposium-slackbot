import os


class ProductionConfig(object):

	DEBUG = False
	TESTING = False
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///test.db'

	# Once this actually moves to an actual production environment in any kind of way,
	# I need to remove these terrible secret keys.
	SECRET_KEY = 'secret key'
	
	# Settings for interacting with the frontend
	SLACK_AUTH_TOKEN = os.environ.get('SLACK_AUTH_TOKEN')
	APP_URL = 'https://mstr-symposium-demo.herokuapp.com/api/pricerequest'

	# Settings to work with Slack
	CLIENT_ID = os.environ.get('CLIENT_ID')
	CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
	VERIFICATION_TOKEN = os.environ.get('VERIFICATION_TOKEN')
	SLACK_TEAM_ID = os.environ.get('SLACK_TEAM_ID')
	SLACK_BOT_OATH_TOKEN = os.environ.get('SLACK_BOT_OATH_TOKEN')

	# Settings for the Microstrategy Environment
	MSTR_PROJECT_ID = 'B7CA92F04B9FAE8D941C3E9B7E0CD754'
	MSTR_BASE_URL = 'https://env-108710.customer.cloud.microstrategy.com/MicroStrategyLibrary/api'
	MSTR_PRODUCT_REPORT_ID = '7ACA2CD211E8B468C0000080EF058762'
	MSTR_PRODUCT_ATTRIBUTE_NAME = 'Item'
	MSTR_PRODUCT_ATTRIBUTE_ID = '8D679D4211D3E4981000E787EC6DE8A4'
	MSTR_CUSTOMER_REPORT_ID = 'A356B50211E8B469C0000080EF058660'
	MSTR_CUSTOMER_ATTRIBUTE_NAME = 'Supplier'
	MSTR_CUSTOMER_ATTRIBUTE_ID = '8D679D5011D3E4981000E787EC6DE8A4'
	MSTR_USERNAME = 'mstr'
	MSTR_PASSWORD = os.environ.get('MSTR_PASSWORD')

class DevelopmentConfig(ProductionConfig):

	DEBUG = True
	# When doing work on static js files, template reload
	# is needed to see those changes. Flask combined with the 
	# unpredictable browser behavior means both auto reload
	# needs to be on, and send file age needs to be 0.
	TEMPLATES_AUTO_RELOAD = True
	SEND_FILE_MAX_AGE_DEFAULT = 0
	SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

	# Making sure requests don't fail during development/testing.
	# Real app token gets overwritten for the production environment.
	SLACK_AUTH_TOKEN = os.environ.get('SLACK_AUTH_TOKEN') or 'MY_HARD_TO_GUESS_SLACK_TOKEN'

class SqlDebuggingConfig(DevelopmentConfig):

	SQLALCHEMY_ECHO = True

class TestingConfig(ProductionConfig):

	TESTING = True
	WTF_CSRF_CHECK_DEFAULT = False
	LOGIN_DISABLED = True
