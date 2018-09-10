import os
import time
from flask import Flask, request, Response, make_response, jsonify, render_template
from dadjokemessage import DAD_JOKES, InteractiveButtonRequest
import random
import json
import bot
import requests

from mstrest.parser import MstrParser
from mstrest.client import MstrClient


# from models import db, Joke, SlackUser, SlackTeam, SlackChannel, SlackUserChannel, ToldJoke, JokeVote, SlackButton

pybot = bot.Bot()
slack = pybot.client

		


# TO DO
# FOR THE LOVE OF GOD, SET UP LOGGING.


# TO DO
# IMPLEMENT DATABASE BACKEND FOR STORAGE
# OF USAGE STATS.




def build_slack_ui(pr, mstr_data):

	return 

@app.route('/install', methods=["GET"])
def pre_install():
	"""
	This route renders the installation page with the add to slack button.
	Builds the request we send to slack for the oauth token.
	"""
	client_id = pybot.oauth['client_id']
	scope = pybot.oauth['scope']

	return render_template("install.html", client_id=client_id, scope=scope)

@app.route('/thanks', methods=['GET', 'POST'])
def thanks():
	"""
	Called when a user installs the app.
	Exchanges the temporary auth code slack will
	send us for the OAuth token for user later.

	OAuth token is used when not directly responding to requests.
	If we want to send back a "hey I'm working on this" message,
	that won't require the token since Slack is already listening for the server's reponse,
	but sending back a response that requires > 3 seconds to generate 
	will require it since that'll be done async. 
	"""

	code_arg = request.args.get('code')

	pybot.auth(code_arg)
	return render_template('thanks.html')

@app.route('/pricerequest', methods=['GET', 'POST'])
def pricerequest():


	if request.get_json() is not None:
		if "challenge" in request.get_json():
			return make_response(request.get_json()['challenge'], 200,
				{'content_type': 'application/json'})

	valid_token, valid_team = pybot.is_request_valid(request)
	if not valid_token:
		msg = "Invalid slack verification token. Canobot has a different token. Try re-authenticating?"
		return make_response(msg, 403)

	form = request.form
	team_id = form.get("team_id")
	channel_id = form.get("channel_id")
	user_id = form.get("user_id")

	if form.get('command') in ['/pricerequest', '/pr']:

		pr = PriceRequest()
		req_url = 'https://mstr-symposium-demo.herokuapp.com/api/pricerequest/get'
		app_token = os.environ.get('SLACK_AUTH_TOKEN') or 'MY_HARD_TO_GUESS_SLACK_TOKEN'
		app_data = pr.get_next_price_request(req_url, app_token)
		
		if app_data.json().get('error') is not None:
			return make_response('No outstanding price requests!', 200)

		# Figure out I need to send a placeholder request so Slack won't time out on me.
		mstr_data = get_mstr_data(pr)
		ui = build_slack_ui(pr, mstr_data)
		pybot.send_price_request(channel_id, ui)
		return Response(), 200

	# In case an "unrecognized" command comes in.
	return make_response("[COMMAND NOT RECOGNIZED] These are not the droids\
		you're looking for. Somehow you sent a non approved command to my server! Rude!", 
		404, {"X-Slack-No-Retry": 1})


@app.route('/voteonjoke', methods=['POST'])
def voteonjoke():

	"""
	Handles a user clicking on an interactive message in Slack.
	"""

	button_event = InteractiveButtonRequest(request)
	# print('the requests payload is {}'.format(button_event.payload))
	# Ensures this isn't a random person or different service trying to 
	# send requests to my server. In Bird culture, that'd be considered a dick move.
	error_msg, status_code = button_event.validate_request(verification_token=pybot.verification,
		team_id=pybot.team_id, callback_id='voteonjoke')

	
	button_event.return_message = button_event.original_message
	print('keys from payload are {}'.format(', '.join([key for key in button_event.payload.keys()])))
	print('original message attachments are {}'.format(button_event.original_message['attachments']))
	print('trigger_id is {}'.format(button_event.payload['trigger_id']))


	# Returns a response if there was an error or the 
	# data looks different than expected.
	if error_msg is not None:
		return make_response(error_msg, status_code)

	
	button_event.return_message['attachments'][0].pop('actions')
	button_event.return_message['attachments'].append({'text': 'Thanks for voting! \
	At some point I\'ll get around to using this to help improve your joke experience.'})
	response = pybot.respond_to_joke_vote(button_event.channel_id, button_event.message_ts, button_event.return_message)
	# print('response is {}'.format(response))
	return Response(), 200

	if request.get_json() is not None:
		if "challenge" in request.get_json():
			return make_response(request.get_json()["challenge"], 200,
				{"content_type": "application/json"})

	valid_token, valid_team = pybot.is_request_valid(request)
	if not valid_token:
		message = "Invalid token. I have a different authorization token and \
			do not answer to you!"

		return make_response(message, 403)

	team_id = request.form.get("team_id")
	channel_id = request.form.get("channel_id")
	user_id = request.form.get("user_id")

	if request.form.get("command") == "/price-request":
		buttons = build_price_request_buttons()

	

@app.route('/listening', methods=['GET', 'POST'])
def hears():
	"""
	This route listens for incoming slash commands
	from Slack. I will eventually put an event handler
	if I start handling more than 1 event. 
	Otherwise its overkill.
	"""
	
	# prints out the form data from the request
	# slack sends us. I keep this here because
	# I always forget what info they send us.
	# print("Request.form from listening route is {}".format(request.form))
	
	slack_event = request.form
	
	# When initially installing your app (if you use events)
	# Slack will send a challenge parameter to make sure
	# your app responds. This handles that.
	if request.get_json() is not None:
		if "challenge" in request.get_json():
			return make_response(request.get_json()["challenge"], 200, 
				{"content_type": "application/json"})

	# Sends back a response assuming they send a bad token

	# TO DO:
	# Do I need to check whether the team is authorized? I think
	# the token is proof of that, but look into whether or not
	# you can send a valid token somehow but an unauthorized team.
	# Do tokens authorize use in specific channels? Do I need
	# to store tokens if they'll need to reinstall new versions anyway? 
	# How would a secure way to store tokens even be? In memory?
	# hashed in some database or something?

	valid_token, valid_team = pybot.is_request_valid(request)
	if not valid_token:
		message = "Invalid slack verification token of {}. \nDad \
			joke bot has a different verification token".format(request.form.get("token", "No Token Found!"))
		
		# By adding no retry, we turn off retrying during dev
		# get rid of the X-Slack-No-Retry after dev is done.
		return make_response(message, 403, {"X-Slack-No-Retry": 1})

	
	# Assuming they've sent a valid request with good authentication
	# Using form.get(var) instead of form[var] because if the key
	# doesn't exist, it will raise a KeyError using form[var]
	# which will bomb out my bot. 
	team_id = request.form.get("team_id")
	channel_id = request.form.get("channel_id")
	user_id = request.form.get("user_id")

	# eventually build a dictionary of command handlers based 
	# on the command sent by the user. This is overkill with one 
	# command, though.
	if request.form.get("command") == "/joke":
		message = pybot.build_joke(random.choice(DAD_JOKES))

		# Putting the sending portion into its own method and API call
		# so that I can later add async execution and a message broker
		# to allow for longer than 3 second calculations.
		# That's going to be useful for style GP stuff that
		# will be querying ambush and not just relying
		# on quick internal calculations.
		sent_message = pybot.send_joke(channel_id, message)
		return Response(), 200
		

	# If somehow they send a request for something we aren't listening
	# for, we can send back some response back.
	return make_response("[COMMAND NOT RECOGNIZED] These are not the droids\
		you're looking for. Somehow you sent a non approved command to my server! Rude!", 
		404, {"X-Slack-No-Retry": 1})


if __name__ == "__main__":
	app.run()
	