import json
import requests
from .parser import Attribute, Metric

class MstrClient(object):

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
		self.session = requests.session()
		self.auth_token = None
		self.cookies = None

		# Report gets generated from the post request
		self.report = None

	def login(self, username: str, password: str, *, re_auth: bool=False):

		"""
		Authentication that stores the token in self.auth_token.
		Expected response status codes are the below:
			204 - Good request, token in header
			401 - Bad credentials, no token
			503 - MSTR Server is down.
		"""

		# Trying to log in when you're already logged in 
		# unless manually specified.
		if self.auth_token is not None and not re_auth:
			return

		# Username and password are required params
		if username is None or password is None:
			raise TypeError('Username and password are both required. \
				{} was provided for username and {} was \
				provided for password'.format(username, password))

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

		
		response = self.session.post(self.base_url + '/auth/login', data=payload)

		# Expected HTTP Reponse by MSTR's API for success.
		self.auth_token = response.headers.get('X-MSTR-AuthToken')
		# self.cookies = dict(response.cookies)

		return response
		

	def logout(self):

		if self.auth_token is None:
			raise TypeError('No auth token found. Cannot log out if not currently logged in.')

		response = self.session.post(self.base_url + '/auth/logout', 
			headers={'X-MSTR-AuthToken': self.auth_token})

		if response.status_code != requests.codes.ok:
			response.raise_for_status()

		self.auth_token = None
		return response


	# TO DO
	# IMPLEMENT THIS CLASS AS A CONTEXT MANAGER

	# @contextmanager
	# def auth(self, *args, **kwargs):
	# 	try:
	# 		self.login(*args, **kwargs)
	# 		yield self
	# 	finally:
	# 		self.logout()



	def create_report_instance(self, report_id: str, **kwargs):

		self.report = Report(report_id, project_id=self.project_id, 
			auth_token=self.auth_token, base_url=self.base_url, **kwargs)


class Report:

	def __init__(self, report_id: str, project_id: str, auth_token: str, base_url: str, 
		requested_objects: dict=None, page_limit: int=-1, *, view_filters=None):

		self.report_id = report_id
		self.project_id = project_id
		self.auth_token = auth_token
		self.base_url = base_url
		self.request_headers = {'X-MSTR-AuthToken': auth_token, 
			'X-MSTR-ProjectID': project_id, 'reportId': report_id,
			'Content-Type': 'application/json'}
		
		self.report_url = '{}/reports/{}/instances'.format(base_url, report_id)
		self.definition_url = '{}/reports/{}'.format(base_url, report_id)
		self.page_limit = page_limit
		self.view_filters = view_filters if view_filters is not None else []
		

		# Initialized in the create method for paging behavior.
		self.offset = None
		self.instance_id = None

		# The definition of the report from the post method (actually used)
		self.report_definition = {'attributes': {},
			'metrics': {}}

	def __repr__(self):
		return '<Report(report_id={}, project_id={}, auth_token={},\
		base_url={}, requested_objects={}, page_limit={})>'.format(
			self.report_id, self.project_id, self.auth_token, 
			self.base_url, self.requested_objects, self.page_limit)
		

	@classmethod
	def from_client(cls, report_id, client, *args, **kwargs):

		return cls(report_id=report_id, project_id=client.project_id,
			auth_token=client.auth_token, base_url=client.base_url,
			*args, **kwargs)


	def get_definition(self, session):

		"""
		Gets the definition of a report, including attributes and elements of them.
		This will allow for a dynamic way to determine the ID needed to use 
		view filters on report objects.
		"""

		response = session.get(self.definition_url, headers=self.request_headers)

		definition = response.json()['result']['definition']['availableObjects']
		

		for attribute in definition['attributes']:
			self.report_definition['attributes'][attribute['name']] = Attribute.from_dict(attribute)
		  

		for metric in definition.get('metrics', []):
			self.report_definition['metrics'][metric['name']] = Metric.from_dict(metric)

		return response

	def create(self, session, view_filter: dict=None, attributes: dict=None, metrics: dict=None):

		"""
		Creates a report instance in the i server.
		"""

		if self.instance_id is not None:
			raise TypeError('Create called more than once for the same instance.\
				Per the MSTR documentation, call create once and fetch to retrieve\
				outstanding results if using paging.')
			return None

		params = {'limit': self.page_limit}
		body = {'viewFilter': view_filter, 'requestedObjects': {'attributes': attributes, 'metrics': metrics}}

		# Cleaning up of the request and deleting things
		# so the MSTR API doesn't freak out.
		if view_filter is None:
			body.pop('viewFilter')

		if metrics is None and attributes is None:
			body.pop('requestedObjects')

		else:
			if metrics is None:
				body['requestedObjects'].pop('metrics')
			else:
				body['requestedObjects'].pop('attributes')

		if body:
			response = session.post(self.report_url, 
				headers=self.request_headers, params=params,
				data=json.dumps(body))
		else:
			response = session.post(self.report_url, 
				headers=self.request_headers, params=params)

		if response.status_code == 200:
			# Ensuring we declare our offset so we don't keep raiding the same data.
			self.instance_id = response.json()['instanceId']
			if self.page_limit != -1:
				self.offset = self.page_limit
				
		return response

	def fetch(self, session, *, re_read: bool=False):

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
		response = session.get(fetch_url, headers=self.request_headers, params=params)

		if self.page_limit != -1:
			self.offset += self.page_limit

		return response


class FilteringReport(Report):

	"""
	Used for finding the appropriate ID of an element
	that will be used for filtering later.
	"""

	def __init__(self, *args, **kwargs):

		super().__init__(*args, **kwargs)

		# Initialized later in the create method
		self.attribute_id = None
		self.attribute_name = None

	def create(self, session, attribute_id, attribute_name):

		if self.instance_id is not None:
			raise TypeError('Create called more than once for the same instance.\
				Per the MSTR documentation, call create once and fetch to retrieve\
				outstanding results if using paging.')
			return None

		self.attribute_id = attribute_id
		self.attribute_name = attribute_name

		params = {'limit': self.page_limit}

		body = {
		'requestedObjects': 
			{
				'attributes': [
						{'id': attribute_id, 'name': attribute_name}
					]
				}
			}

		response = session.post(self.report_url,
			headers=self.request_headers, data=json.dumps(body))

		if response.status_code == 200:
			
			# Ensuring we declare our offset so we don't keep raiding the same data.
			self.instance_id = response.json()['instanceId']
			if self.page_limit != -1:
				self.offset = self.page_limit
		
			
		return response

	
	def build_view_filter(self, response, element_name):

		"""
		Top level function that returns an element ID for the 
		element name passed in. If the element name
		is not one of the options from the report,
		a ValueError is thrown.
		"""

		for val, id in self._get_elements(response):
			if val == element_name:
				element_id = id
				break
		else:
			raise ValueError('ID not found for attribute element {}'.format(
				element_name))

		attribute_node = response['result']['definition']['attributes']
		attribute_id = attribute_node[0]['id']
		attribute_name = attribute_node[0]['name']

		view_filter = FilteringReport._build_view_filter(attribute_id,
			attribute_name, element_id, element_name)

		return view_filter
	
	def _get_elements(self, response):

		"""
		Gets the single element response from
		a report that only has one attribute.
		"""

		meta_attributes = response['result']['definition']['attributes']
		if len(meta_attributes) != 1:
			raise ValueError('Expected only one attribute for this parsing function.')

		elements = response['result']['data']['root']['children']

		for element in elements:
			yield (element['element']['name'], element['element']['id'])

	
	def _filter_elements(self, response, element_name):

		"""
		Filters down a response from the MSTR Report API to a single value
		in an effort to be able to use it as a view filter.
		"""
		for val, id in get_elements(response):
			if val == element_name:
				return id

		return None

	@staticmethod
	def _build_view_filter(attribute_id, attribute_name, element_id, element_name):

		view_filter = {
			'operator': 'Equals',
			'operands': [
				{
					'type': 'attribute',
					'id': attribute_id,
					'name': attribute_name
				},
				{
					'type': 'elements',
					'elements': [
						{
							'id': element_id,
							'name': element_name
						}
					]
				}
			]
		}

		return view_filter