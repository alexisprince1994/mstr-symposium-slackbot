# Standard Library Imports
import json
import requests
import unittest
from unittest.mock import patch


# Local Imports
from src.mstrest.client import MstrClient, Report, FilteringReport
from src.mstrest.parser import MstrParser
from tests.expected_results import (expected_response_multiple_attributes,
	expected_response_single_attribute, expected_response_no_metric)

# TO DO
# I INCORRECTLY THOUGHT THE INSTANCE ID WAS IN THE HEADERS
# OF THE RESPONSE, AND IT ISN'T. GO THROUGH
# AND FIX THE TESTS TO LOOK THERE INSTEAD.

class TestFilteringReport(unittest.TestCase):

	PROJECT_ID = 'TEST'
	BASE_URL='MY/FAKE/URL'

	VALID_REPORT_ID = 'valid report id'
	INVALID_REPORT_ID = 'invalid report id'

	# Utility Method for Mocking response.json() from
	# the requests package.

	def mock_json(self, data):

		return unittest.mock.Mock(return_value=data)

	@classmethod
	def setUpClass(cls):

		with open('tests/response_no_metrics.json') as f:
			cls.real_example_response = json.load(f)

		cls.client = MstrClient(project_id=cls.PROJECT_ID, 
			base_url=cls.BASE_URL)
		# Assuming we're in a logged in state.
		cls.client.auth_token = 'fake auth token'
		cls.report = FilteringReport.from_client(cls.VALID_REPORT_ID, cls.client)
	
		
	@patch('src.mstrest.client.requests.Session.post')
	def test_create(self, mock_post):

		attribute_id = 'a valid attribute ID'
		attribute_name = 'a valid attribute name'
		instance_id = 'a valid instance id'
		mock_post.return_value.status_code = 200
		mock_post.return_value.json = self.mock_json({'instanceId': instance_id})

		response = self.report.create(requests.session(), 
			attribute_id, attribute_name)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['instanceId'], instance_id)
		self.assertEqual(attribute_id, self.report.attribute_id)
		self.assertEqual(attribute_name, self.report.attribute_name)

	def test_get_elements(self):

		gen = self.report._get_elements(self.real_example_response)

		data = list(gen)
		self.assertEqual(len(data), 4)
		# Expecting the results to be tuples of length 2
		# containing the value and ID
		for row in data:
			self.assertTrue(len(row), 2)

	def test_build_view_filter_no_match(self):

		with self.assertRaises(ValueError):
			self.report.build_view_filter(self.real_example_response,
			'NOT A REAL ELEMENT VALUE')

		with self.assertRaises(ValueError):
			self.report.build_view_filter(self.real_example_response,
				4)

	def test_build_view_filter_success(self):

		# All this function does is formats it nicely into
		# a serializable data structure, so calling this in the
		# test is just to make sure it doesn't error out given
		# a good value.
		self.report.build_view_filter(self.real_example_response, 
			'Books')


class TestReport(unittest.TestCase):

	PROJECT_ID = 'TEST'
	BASE_URL='MY/FAKE/URL'

	VALID_REPORT_ID = 'valid report id'
	INVALID_REPORT_ID = 'invalid report id'

	def setUp(self):

		self.client = MstrClient(project_id=self.PROJECT_ID, 
			base_url=self.BASE_URL)
		# Assuming we're in a logged in state.
		self.client.auth_token = 'fake auth token'
		self.report = Report.from_client(self.VALID_REPORT_ID, self.client)

	def tearDown(self):

		self.client = None

	@patch('src.mstrest.client.requests.Session.post')
	def test_create_report_instance_bad_report_id(self, mock_post):

		mock_post.return_value.status_code = 400

		report = Report.from_client(self.INVALID_REPORT_ID, self.client)
		response = report.create(requests.session())

		self.assertEqual(response.status_code, 400)


	@patch('src.mstrest.client.requests.Session.get')
	def test_get_definition(self, mock_get):
		
		mock_get.return_value.status_code = 200

		response = self.report.get_definition(requests.session())

		self.assertEqual(response.status_code, 200)

	@patch('src.mstrest.client.requests.Session.post')
	def test_create_report_instance(self, mock_post):

		mock_post.return_value.status_code = 200
		mock_post.return_value.headers = {'instanceId': 'valid instance id'}

		response = self.report.create(requests.session())

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.headers['instanceId'], 'valid instance id')

	@patch('src.mstrest.client.requests.Session.post')
	def test_create_report_instance_called_twice(self, mock_post):

		mock_post.return_value.status_code = 200
		mock_post.return_value.headers = {'instanceId': 'valid instance id'}

		response = self.report.create(requests.session())

		with self.assertRaises(TypeError):
			self.report.create(requests.session())

	@patch('src.mstrest.client.requests.Session.post')
	@patch('src.mstrest.client.requests.Session.get')
	def test_fetch_successful_paging(self, mock_get, mock_post):

		self.report.page_limit = 400
		mock_post.return_value.status_code = 200
		mock_post.return_value.json = unittest.mock.Mock(
			return_value={'instanceId': 'valid instance id'})
		

		self.report.create(requests.session())

		# Offset should equal page limit prior to fetching
		self.assertEqual(self.report.offset, 400)
		
		mock_get.return_value.status_code = 200

		response = self.report.fetch(requests.session())
		self.assertEqual(response.status_code, 200)

		# Offset should equal offset + page limit after fetching
		self.assertEqual(self.report.offset, 800)

	@patch('src.mstrest.client.requests.Session.post')
	@patch('src.mstrest.client.requests.Session.get')
	def test_fetch_successful_reread_no_limit(self, mock_get, mock_post):

		initial_offset = self.report.offset
		mock_post.return_value.status_code = 200
		mock_post.return_value.headers = {'instanceId': 'valid instance id'}

		self.report.create(requests.session())

		
		mock_get.return_value.status_code = 200

		response = self.report.fetch(requests.session(), re_read=True)
		self.assertEqual(response.status_code, 200)

		# Offset shouldn't be touched due to re_reading the entire thing
		self.assertEqual(self.report.offset, initial_offset)



	@patch('src.mstrest.client.requests.Session.post')
	def test_create_report_instance_with_paging(self, mock_post):

		self.report.page_limit = 400
		mock_post.return_value.status_code = 200
		mock_post.return_value.json = unittest.mock.Mock(
			return_value={'instanceId': 'valid instance id'})

		response = self.report.create(requests.session())

		# Checking to see if state is taken care of properly first

		self.assertEqual(self.report.offset, 400)
		self.assertEqual(self.report.instance_id, 'valid instance id')

		# Comparing return values

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['instanceId'], 'valid instance id')


class TestMstRestClient(unittest.TestCase):

	PROJECT_ID = 'TEST'
	BASE_URL='MY/FAKE/URL'

	def setUp(self):

		self.client = MstrClient(project_id=self.PROJECT_ID, 
			base_url=self.BASE_URL)

	def tearDown(self):

		self.client = None

	@patch('src.mstrest.client.requests.Session.post')
	def test_logout_before_login(self, mock_post):

		# Shouldn't need to patch it, since I check for missing credentials prior to calling,
		# but I want to make sure I'm not sending rogue requests out during tests.

		mock_post.return_value.status_code = 401
		mock_post.return_value.ok = False

		with self.assertRaises(TypeError):
			self.client.logout()


	@patch('src.mstrest.client.requests.Session.post')
	def test_successful_logout(self, mock_post):

		# Must be logged in to log out, so faking the token
		self.client.auth_token = 'fake auth token'

		mock_post.return_value.status_code = 204
		mock_post.return_value.ok = True

		response = self.client.logout()

		# Initial checks to ensure state is handled correctly
		self.assertIsNone(self.client.auth_token)

		# Ensures the response codes are actually what we expected
		self.assertEqual(response.status_code, 204)
		self.assertEqual(response.ok, True)



	@patch('src.mstrest.client.requests.Session.post')
	def test_login_no_credentials(self, mock_post):

		# Shouldn't need to patch it, since I check for missing credentials prior to calling,
		# but I want to make sure I'm not sending rogue requests out during tests.
		
		with self.assertRaises(TypeError):
			self.client.login()

		with self.assertRaises(TypeError):
			self.client.login('valid_username', None)

		with self.assertRaises(TypeError):
			self.client.login(None, 'valid_password')

	@patch('src.mstrest.client.requests.Session.post')
	def test_good_login(self, mock_post):

		fake_token = 'my fake token'
		expected_response_status = 204
		is_ok = True

		mock_post.return_value.ok = is_ok
		mock_post.return_value.status_code = expected_response_status
		mock_post.return_value.headers = {'X-MSTR-AuthToken': fake_token}

		self.client.login('user', 'password')
		self.assertEqual(fake_token, self.client.auth_token)



class ParserBaseClass:


	def pairwise_generator(self, iterable):

		"""
		Creates a generator that yields (previous, current) tuple per element.

		Returns None if the element doesn't make sense (first iteration previous=None)

		Does not produce an element at the end of iteration
		for prev=last element, current=None as this would hinder the use case.

		Also, this may or may not have come from stack overflow
		"""

		iterable = iter(iterable)

		prv = None
		for item in iterable:
			yield (prv, item)
			prv = item

	
	def test_has_metrics(self):

		rows = list(self.parser.parse_rows())

		for row in rows:
			self.assertIn('metrics', row.keys())			

	def test_equal_number_attributes(self):

		rows = list(self.parser.parse_rows())

		pairs = self.pairwise_generator(rows)

		for prev_row, current_row in pairs:
			current_row.pop('metrics')
			if prev_row is not None:
				self.assertEqual(len(prev_row), len(current_row), 
					'Differing number of attributes parsed. \
					{} from item 1 and {} from item 2'.format(
						len(prev_row), len(current_row)))


	def test_equal_number_metrics(self):

		rows = list(self.parser.parse_rows())
		pairs = self.pairwise_generator(rows)

		for prev_row, current_row in pairs:
			if prev_row is not None:
				prev_metrics = prev_row['metrics']
				current_metrics = current_row['metrics']

				self.assertEqual(len(prev_metrics), len(current_metrics), 
					'Differing number of metrics parsed. \
					{} from item 1 and {} from item 2'.format(
						len(prev_metrics), len(current_metrics)))


class ParserTestRealExample(ParserBaseClass, unittest.TestCase):

	@classmethod
	def setUpClass(cls):

		with open('tests/real_example.json') as f:
			cls.real_example = json.load(f)

		cls.parser = MstrParser(cls.real_example)

	def test_response_real_example_length(self):

		rows = list(self.parser.parse_rows())
		self.assertEqual(len(rows), 12, 
			'Request contained 12 records, parsed values were {}'.format(len(rows)))
		
	def test_num_metrics_parsed(self):

		self.assertEqual(len(self.parser.metrics), 4, 
			'Request contained 4 metrics. Parsed number was {}'.format(
				len(self.parser.metrics)))

	def test_num_attributes_parsed(self):

		self.assertEqual(len(self.parser.attributes), 1, 
			'Requested contained 1 attribute. Parsed numbers was {}'.format(
				len(self.parser.attributes)))


class ParserTestNoMetrics(unittest.TestCase):

	@classmethod
	def setUpClass(cls):

		with open('tests/response_no_metrics.json') as f:
			cls.response_no_metrics = json.load(f)

		cls.parser = MstrParser(cls.response_no_metrics)

	def test_response_no_metrics(self):

		rows = list(self.parser.parse_rows())
		self.assertEqual(rows, expected_response_no_metric,
			'Parsed output does not match for a response missing metrics.')

	def test_response_no_metrics_same_length(self):

		rows = list(self.parser.parse_rows())
		self.assertEqual(len(rows), len(expected_response_no_metric),
			f'Expected rows dont have same row count as parsed rows. \
			Expected {len(rows)} and got {len(expected_response_no_metric)}')


class ParserTestSingleAttribute(ParserBaseClass, unittest.TestCase):

	@classmethod
	def setUpClass(cls):

		with open('tests/response_single_attribute.json') as f:
			cls.response_single_attribute = json.load(f)

		cls.parser = MstrParser(cls.response_single_attribute)

	def test_response_single_attribute(self):

		rows = list(self.parser.parse_rows())
		self.assertEqual(rows, expected_response_single_attribute,
			'Parsed output does not match expected output.')

	def test_response_single_attribute_same_length(self):

		rows = list(self.parser.parse_rows())
		self.assertEqual(len(rows), len(expected_response_single_attribute),
			f'Expected rows dont have same row count as parsed rows. \
			Expected {len(rows)} and got {len(expected_response_single_attribute)}')


class ParserTestMultipleAttributes(ParserBaseClass, unittest.TestCase):

	@classmethod
	def setUpClass(cls):

		with open('tests/response_multiple_attributes.json') as f:
			cls.response_multiple_attributes = json.load(f)

		cls.parser = MstrParser(cls.response_multiple_attributes)

	def test_response_multiple_attributes(self):
		
		# returns a generator, so we need to ensure we dont try to
		# iterate over it twice.
		rows = list(self.parser.parse_rows())

		self.assertEqual(rows, expected_response_multiple_attributes, 
			'Parsed output doesnt match expected output.')
		
	def test_response_multiple_attributes_same_length(self):
		
		rows = list(self.parser.parse_rows())
		self.assertEqual(len(rows), len(expected_response_multiple_attributes),
			f'Expected rows dont have same row count as parsed rows. \
			Expected {len(rows)} and got {len(expected_response_multiple_attributes)}')


if __name__ == "__main__":
	unittest.main()
