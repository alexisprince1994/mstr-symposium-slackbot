import requests
from contextlib import contextmanager


PROJECT_ID = 'B7CA92F04B9FAE8D941C3E9B7E0CD754'
REPORT_ID = '772AB904445FB6AD8BC6CD8F26130049'
USERNAME = 'mstr'
PASSWORD = '1VBKF0fnHrm2'
BASE_URL = 'https://env-104516.trial.cloud.microstrategy.com/MicroStrategyLibrary/api'


class MicrostrategyBot(object):

	def __init__(self, project_id: str, base_url: str, locale: str='en-us', 
		timezone: str='PST'):

		# Project ID of the project that's going to be accessed.
		if project_id is None:
			raise TypeError('Project ID is required.')

		self.project_id = project_id

		if base_url is None:
			raise TypeError('Base URL for Microstrategy is required.')

		self.base_url = base_url

		# Using same locale for all params. Change later if this becomes a problem,
		# My guess is that this may be an issue trying to serve requests from
		# more than 1 timezone? Either way, way too complicated for an example.
		self.warehouse_data_locale = locale
		self.metadata_locale = locale
		self.messages_locale = locale
		self.number_locale = locale
		self.display_locale = locale
		self.timezone = timezone


		# According to MSTR's documentation for EnumDSSXMLApplicationType,
		# 8 is to be used for custom applications, but that doesn't seem to work.
		# Using 35, which is their Library Application Type
		self.app_type = 35

		# Coordinate w/ MSTR Admin (aka me)
		self.login_mode = 1

		# Auth token gained from the /auth/login route that is hit 
		# by the login method
		self.session = None
		self.auth_token = None
		self.cookies = None

		# Report gets generated from the post request
		self.report = None

	def login(self, username: str, password: str, *, re_auth: bool=False):

		# Trying to log in when you're already logged in 
		# unless manually specified.
		if self.auth_token is not None and not re_auth:
			return

		expected_status_codes = [204, 401]

		payload = {
			'username': username,
			'password': password,
			'loginMode': self.login_mode,
			'changePassword': False,
			'displayLocale': self.display_locale,
			'warehouseDataLocale': self.warehouse_data_locale,
			'metadataLocale': self.metadata_locale,
			'messagesLocale': self.messages_locale,
			'numberLocale': self.number_locale,
			'applicationType': self.app_type,
			'timeZone': self.timezone,
			}

		self.session = requests.session()
		response = self.session.post(self.base_url + '/auth/login', data=payload)

		if response.status_code != requests.codes.ok:
			response.raise_for_status()

		# Expected HTTP Reponse by MSTR's API for success.
		self.auth_token = response.headers.get('X-MSTR-AuthToken')
		self.cookies = dict(response.cookies)
		

	def logout(self):

		if self.auth_token is None:
			return

		response = requests.post(self.base_url + '/auth/logout', 
			headers={'X-MSTR-AuthToken': self.auth_token})

		if response.status_code != requests.codes.ok:
			response.raise_for_status()

		self.auth_token = None


	@contextmanager
	def auth(self, *args, **kwargs):
		try:
			self.login(*args, **kwargs)
			yield self
		finally:
			self.logout()



	def create_report_instance(self, report_id: str, **kwargs):

		self.report = Report(report_id, project_id=self.project_id, auth_token=self.auth_token,
			base_url=self.base_url, **kwargs)

		response = self.report.create(self.session, self.cookies)
		return response



class Report:

	def __init__(self, report_id: str, project_id: str, auth_token: str, base_url: str, 
		requested_objects: dict=None, page_limit: int=-1):

		self.request_headers = {'X-MSTR-AuthToken': auth_token, 
			'X-MSTR-ProjectID': project_id, 'reportId': report_id}
		
		self.report_url = '{}/reports/{}/instances'.format(base_url, report_id)
		self.requested_objects = requested_objects
		self.page_limit = page_limit

		# Initialized in the create method for paging behavior.
		self.offset = None
		self.instance_id = None

		

	def create(self, session, cookies: dict, view_filter: dict):

		"""
		Creates a report instance in the i server.
		"""

		if self.instance_id is not None:
			return None

		params = {'limit': self.page_limit}

		if self.requested_objects is not None:
			headers['body'] = self.requested_objects

		response = session.post(self.report_url, headers=self.request_headers, params=params, cookies=cookies)

		if response.status_code == 200:
			# Ensuring we declare our offset so we don't keep raiding the same data.
			self.instance_id = response.headers['instanceId']
			if self.page_limit != -1:
				self.offset = self.page_limit
				
		return response

	def fetch(self, session, cookies: dict, *, re_read: bool=False):

		if self.instance_id is None:
			raise TypeError('Instance ID is required to fetch from the instance. \
				Instance ID is auto-generated after using create method.')

		if self.page_limit == -1 and not re_read:
			raise ValueError('Page limit was set to read entire report on create. \
				If youd like to re-read, the data, set kwarg re_read=True')

		params = {'limit': self.page_limit}

		if self.offset:
			params['offset'] = self.offset
		
		fetch_url = '{}/{}'.format(self.report_url, self.instance_id)
		response = session.get(self.fetch_url, headers=self.request_headers, params=params)

		if self.page_limit != -1:
			self.offset += self.page_limit

		return response


if __name__ == "__main__":
	bot = MicrostrategyBot(project_id=PROJECT_ID, base_url=BASE_URL)

	try:
		bot.login(USERNAME, PASSWORD)
		
		print(bot.create_report_instance(report_id=REPORT_ID))

	finally:
		bot.logout()

