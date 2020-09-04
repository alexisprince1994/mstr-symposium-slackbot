# Standard Library Imports
import json
import os
import random

# Third Party Imports
import requests
from flask import (
    Blueprint,
    render_template,
    make_response,
    request,
    Response,
    current_app,
    jsonify,
)


# Local Imports
from src.pyslack import bot
from src.pricerequests.utils import respond_to_price_request
from src.pyslack.dadjokemessage import DAD_JOKES, InteractiveButtonRequest

# Get all the required secrets needed to operate nicely w/ Slack.
# I'm sure some of these aren't exactly secret, but better to keep
# them hidden instead of publishing them.
slack_secrets = {
    "client_id": os.environ.get("CLIENT_ID"),
    "client_secret": os.environ.get("CLIENT_SECRET"),
    "verification_token": os.environ.get("VERIFICATION_TOKEN"),
    "slack_team_id": os.environ.get("SLACK_TEAM_ID"),
    "slack_bot_oath_token": os.environ.get("SLACK_BOT_OAUTH_TOKEN"),
}

pybot = bot.Bot(**slack_secrets)
slack = pybot.client

slackapp = Blueprint("slackapp", __name__)


@slackapp.route("/install", methods=["GET"])
def pre_install():
    """
	This route renders the installation page with the add to slack button.
	Builds the request we send to slack for the oauth token.
	"""

    client_id = pybot.oauth["client_id"]
    scope = pybot.oauth["scope"]

    return render_template("install.html", client_id=client_id, scope=scope)


@slackapp.route("/thanks", methods=["GET", "POST"])
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

    code_arg = request.args.get("code")

    pybot.auth(code_arg)
    return render_template("thanks.html")


@slackapp.route("/prstatus", methods=["POST"])
def prstatus():

    button_event = InteractiveButtonRequest(request)
    # print('the requests payload is {}'.format(button_event.payload))
    # Ensures this isn't a random person or different service trying to
    # send requests to my server. In Bird culture, that'd be considered a dick move.
    error_msg, status_code = button_event.validate_request(
        verification_token=pybot.verification,
        team_id=pybot.team_id,
        callback_id="post_to_app",
    )

    # Returns a response if there was an error or the
    # data looks different than expected.
    if error_msg is not None:
        return make_response(error_msg, status_code)

    # Actions comes back as a list (because Slack allows for
    # 	multi-interactive messages, but when you click a button,
    # 	you only interact with 1 thing.)

    price_request_id = button_event.actions[0]["value"]
    price_request_status = button_event.actions[0]["name"].title()
    post_url = current_app.config.get("APP_URL") + "/post/{}".format(price_request_id)

    response = requests.post(
        post_url,
        headers={"X-SLACK-AUTH-TOKEN": current_app.config.get("SLACK_AUTH_TOKEN")},
        json={"action": button_event.actions[0]["name"]},
    )

    # 204 indicates success and that no payload is required.
    if response.status_code != 204:
        msg = {
            "text": "Error!",
            "attachments": [
                {
                    "text": (
                        "Looks like an error occurred and your decision wasnt saved. "
                        + "The error code is {} and the message is {}".format(
                            response.status_code, response.json().get("error_message")
                        )
                        or "Unplanned error, no message available"
                    )
                }
            ],
        }

    msg = {
        "text": "Thanks!",
        "attachments": [
            {
                "text": (
                    "Thank you for changing the status to {}! ".format(
                        price_request_status
                    )
                    + "If you would like to change your mind, please view this request in the web interface."
                    + " The ID for this request is {}".format(price_request_id)
                )
            }
        ],
    }

    return jsonify(msg)


@slackapp.route("/voteonjoke", methods=["POST"])
def voteonjoke():

    button_event = InteractiveButtonRequest(request)

    error_msg, status_code = button_event.validate_request(
        verification_token=pybot.verification,
        team_id=pybot.team_id,
        callback_id="voteonjoke",
    )

    # Takes the original message, deletes the buttons so they can't
    # vote on the same joke twice, then updates the old message
    # in place.
    button_event.return_message["attachments"][0].pop("actions")
    button_event.return_message["attachments"].append(
        {
            "text": "Thanks for voting! \
	At some point I'll get around to using this to help improve your joke experience."
        }
    )
    response = pybot.update_message(
        channel_id=button_event.channel_id,
        ts=button_event.message_ts,
        message=button_event.return_message,
        response_type="EPHEMERAL",
    )
    # print('response is {}'.format(response))
    return Response(), 200


@slackapp.route("/listening", methods=["GET", "POST"])
def listening():
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

    # Ensures to check if its not none, otherwise
    # your app will error out trying to iterate
    # over something that isn't iterable
    if request.get_json() is not None:
        if "challenge" in request.get_json():
            return make_response(
                request.get_json()["challenge"],
                200,
                {"content_type": "application/json"},
            )

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
			joke bot has a different verification token".format(
            request.form.get("token", "No Token Found!")
        )

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

    if request.form.get("command").lower() in ["/pricerequest", "/pr"]:

        if "help" in request.form.get("text").lower():
            help_text = (
                "This is the help message for reviewing price requests."
                + "\nProbably some other business relevant stuff can go here."
                + "\nMaybe something like Customer Rankings do not include inactive customers."
            )

            help_message = {
                "text": "Price Request Help",
                "attachments": [{"attachment_type": "default", "text": help_text}],
            }

            pybot.respond(
                channel_id, help_message, response_type="EPHEMERAL", user_id=user_id
            )
            return Response(), 200

        placeholder_message = {
            "text": "Price Request Analysis",
            "attachments": [
                {"attachment_type": "default", "text": "Processing your request!"}
            ],
        }
        slack_placeholder_message = pybot.respond(
            channel_id, placeholder_message, response_type="CHANNEL", user_id=user_id
        )

        msg_ts = slack_placeholder_message.get("ts")
        url = slack_placeholder_message.get("response_url")

        respond_to_price_request(request, pybot, msg_ts, current_app, response_url=url)

        return Response(), 200

        # price_message = respond_to_price_request(request, pybot)

    if request.form.get("command") == "/joke":

        message = pybot.build_joke(random.choice(DAD_JOKES))
        sent_message = pybot.respond(
            channel_id, message, response_type="EPHEMERAL", user_id=user_id
        )
        # sent_message = pybot.send_joke(channel_id, message)
        return Response(), 200

    # If somehow they send a request for something we aren't listening
    # for, we can send back some response back.
    return make_response(
        "[COMMAND NOT RECOGNIZED] These are not the droids\
		you're looking for. \
		Somehow you sent a non approved command to my server! Please don't do it again :)",
        404,
        {"X-Slack-No-Retry": 1},
    )
