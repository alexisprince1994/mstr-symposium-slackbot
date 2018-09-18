import json



class SlackMessage(object):

	def __init__(self, text, *attachments):
		self.text = text
		self.attachments = [attachment for attachment in attachments]

	def add_attachments(self, *attachments):

		if attachments is None:
			raise TypeError("No attachments found to add.")
		for attachment in attachments:
			self.attachments.append(attachment.to_json())
		
	def to_json(self):
		return {'text': self.text, 'attachments': self.attachments}

	def __repr__(self):
		return str(self.to_json())


class SlackAttachment(object):

	def __init__(self, title=None, text=None, *fields):
		self.title = title
		self.text = text
		self.fields = [field for field in fields]
		
	def add_fields(self, *fields):
		for field in fields:
			self.fields.append(field.to_json())

	def to_json(self):
		response = {'title': self.title, 'text': self.text, 'fields': self.fields}
		if len(self.fields) == 0:
			response.pop('fields')

		return response


	def __repr__(self):
		return str(self.to_json())


class SlackField(object):

	def __init__(self, title=None, value=None, short=True):
		self.title = title
		self.value = value
		self.short = short

	def to_json(self):
		return {'title': self.title, 'value': self.value, 'short': self.short}

	def __repr__(self):
		return str(self.to_json())

def format_number(number, number_format, negative_format):

	
	if number >= 0:
		return number_format.format(number)
	else:
		return negative_format.format(abs(number))


def create_product_analysis(avg_units, stdev_units, *, title=None, text=None):

	title = title or 'Product Volume Analysis'
	text = text or 'How much volume in units we are selling monthly'
	fields = [('Avg Units Last 365', avg_units, '{:,.0f}', '-{:,.0f}'),
		('StDev Units Last 365', stdev_units, '{:,.1f}', '-{:,.1f}')]

	output = {'title': title, 'text': text, 'fields': []}
	for field in fields:
		header, val, pos_format, neg_format = field
		val = format_number(val, pos_format, neg_format)
		output['fields'].append({'title': header, 'value': val, 'short': True})

	return output


def create_customer_analysis(overall, regional, *, title=None, text=None):
	title = title or 'Customer Sales Summary'
	text = text or "Summary of customer's business for the last year"
	fields = [('Customer Sales Rank (Overall)', overall, '{:,.0f}', '-{:,.0f}'),
	('Customer Sales Rank (Regional)', regional, '{:,.0f}', '-{:,.0f}')]

	output = {'title': title, 'text': text, 'fields': []}
	for field in fields:
		header, val, pos_format, neg_format = field
		val = format_number(val, pos_format, neg_format)
		output['fields'].append({'title': header, 'value': val, 'short': True})

	return output


def create_slack_price_request(app_response, price_ui, product_ui, customer_ui):

	units = app_response['price_request']['requested_units']
	product_name = app_response['price_request']['product_name']
	request_date = app_response['price_request']['request_date']
	request_reason = app_response['price_request']['request_reason'] or 'No request reason provided.'

	actions = create_action_buttons(app_response['post_route'], app_response['actions'])

	
	output = {'text': 'Product Pricing Approval Form',
	'attachments': [
		{'title': '{:,.0f}'.format(units) + ' units of {} product requested on {}'.format(
			product_name, request_date),
		'text': request_reason}
	]}

	output['attachments'].append(price_ui)
	output['attachments'].append(product_ui)
	output['attachments'].append(customer_ui)
	output['attachments'].append(actions)

	return output



def create_action_buttons(post_route, actions):

	action_bar = SlackActionBar(post_route, actions[0], actions[1])
	return action_bar.to_json()


class SlackPriceAnalysis:

	def __init__(self, current_price=None, requested_price=None, current_margin=None,
		requested_margin=None, current_profit=None, requested_profit=None, *, 
		title=None, text=None):

		self.title = title or 'Price Delta Analysis'
		self.text = text or 'Difference between normal price and requested'
		self.price_analysis = SlackAttachment(self.title, self.text)
		self.current_price = SlackField('Normal Price', current_price)
		self.requested_price = SlackField('Requested', requested_price)
		self.current_margin = SlackField('Normal Margin', current_margin)
		self.requested_margin = SlackField('Requested Margin', requested_margin)
		self.current_profit = SlackField('Normal Gross Profit', current_profit)
		self.requested_profit = SlackField('Requested Gross Profit', requested_profit)

	def to_json(self):
		self.price_analysis.add_fields(self.current_price, self.requested_price,
			self.current_margin, self.requested_margin,
			self.current_profit, self.requested_profit)
		return self.price_analysis.to_json()

class SlackProductAnalysis:

	def __init__(self, avg_units, stdev_units, *, title=None, text=None):
		self.title = title or 'Product Volume Analysis'
		self.text = text or 'How much volume in units we are selling monthly'
		self.product_analysis = SlackAttachment(self.title, self.text)
		self.avg_units = SlackField('Avg Units Last 365', avg_units)
		self.stdev_units = SlackField('StDev Units Last 365', stdev_units)

	def to_json(self):
		self.product_analysis.add_fields(self.avg_units, self.stdev_units)
		return self.product_analysis.to_json()

class SlackCustomerAnalysis:

	def __init__(self, overall, regional, *, title=None, text=None):
		self.title = title or 'Customer Sales Summary'
		self.text = 'Summary of customers business for the last year'
		self.customer_analysis = SlackAttachment(self.title, self.text)
		self.overall = SlackField('Customer Sales Rank (Overall)', overall)
		self.regional = SlackField('Customer Sales Rank (Regional)', regional)

	def to_json(self):
		self.customer_analysis.add_fields(self.overall, self.regional)
		return self.customer_analysis.to_json()

class SlackActionBar:

	def __init__(self, route, approve_action, deny_action):
		
		self.approve_button = SlackButton(name=approve_action, value=route, text='Approve', 
			style='primary')
		self.deny_button = SlackButton(name=deny_action, value=route, text='Deny', style='danger')
		

	def to_json(self):
		return {
		'fallback': 'some default',
		'callback_id': 'post_to_app',
		'actions': [
			self.approve_button.to_json(),
			self.deny_button.to_json()
		]}
		


class SlackButton(object):
	

	def __init__(self, name, value, text=None, style=None, confirm=None, callback_id=None):
		self.name = name
		self.value = value
		self.text = text
		self.style = style
		self.confirm = confirm
		self.callback_id = callback_id
		self.type = 'button'


	def to_json(self):
		"""
		Returns the SlackButton object as a dictionary so it is 
		serializable. Deletes unused attributes so Slack's 
		API can handle the defaults.
		"""

		data_dict = {
			'name': self.name,
			'value': self.value,
			'text': self.text or self.value,
			'style': self.style,
			'confirm': self.confirm,
			'type': self.type,
			'callback_id': self.callback_id,
		}

		dict_out = {}

		for key, val in data_dict.items():
			if val is not None:
				dict_out[key] = val

		return dict_out
