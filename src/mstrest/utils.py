# Standard Library Imports
import asyncio
import aiohttp

# Local

from .client import Report

def filter_elements(response, element_name):

	"""
	Filters down a response from the MSTR Report API to a single value
	in an effort to be able to use it as a view filter.
	"""
	for val, id in get_elements(response):
		if val == element_name:
			return (val, id)

	return (None, None)

def get_elements(response):

	"""
	Gets the single element response from
	a report that only has one attribute.
	"""

	meta_attributes = response['result']['definition']['attributes']
	if len(meta_attributes) != 1:
		raise ValueError('Expected only one attribute for this parsing function.')

	elements = response['data']['root']['children']

	for element in elements:
		yield (element['name'], element['id'])


def build_view_filter(attribute_id, attribute_name, element_id, element_name):

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

