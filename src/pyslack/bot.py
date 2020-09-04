"""
Python Slack Bot class to be used with DadJoke app
The bot will auth itself when the "install to slack"
button of the dad joke app is clicked and 
store the token.
"""

# Standard Library
import os

# Third Party
from slackclient import SlackClient

# Remember which teams have authorized this app
# Currently storing in memory in global scope.
# After development, move to more permanent data store.
authed_teams = {}


class Bot(object):
    def __init__(
        self,
        client_id,
        client_secret,
        verification_token,
        slack_team_id,
        slack_bot_oath_token,
    ):
        self.name = "canobot"
        self.emoji = ":robot_face:"

        # When instantiated, access the app credentials in local dev environment
        # if I ever get around to actually exporting these things.
        self.oauth = {
            "client_id": client_id,
            "client_secret": client_secret,
            # Uses the most restrictive access as possible to avoid misuse.
            "scope": "bot",
        }
        self.verification = verification_token
        self.team_id = slack_team_id
        self.bot_token = slack_bot_oath_token

        # Passing empty oath token. Will reinstantiate once we have a permanent one.
        # Slack allows you to instantiate a SlackClient object with no token
        # as long as you don't try to use it.
        self.client = SlackClient("")

    def is_request_valid(self, request):
        """
		Makes sure everything is on the up and up with the request from slack.

		:param request: obj
		"""
        is_token_valid = request.form.get("token") == self.verification
        is_team_id_valid = request.form.get("team_id") == self.team_id

        return (is_token_valid, is_team_id_valid)

    def auth(self, code):
        """
		Authenticate with OAuth and assign correct scopes.
		Save a dictionary of authed team information in memory on the bot object.
		I wonder if I should save this in a database somewhere? Once I deploy,
		will people need to re-auth my bot every time I make changes?
		If so, that'd be way too big of a PITA

		:param code: str
		"""

        auth_response = self.client.api_call(
            "oauth.access",
            client_id=self.oauth["client_id"],
            client_secret=self.oauth["client_secret"],
            code=code,
        )

        team_id = auth_response["team_id"]
        authed_teams[team_id] = {"bot_token": auth_response["bot"]["bot_access_token"]}

        # Now we reconnect to slack client w/ correct OAuth token
        self.client = SlackClient(authed_teams[team_id]["bot_token"])

    def respond(self, channel_id, message, response_type=None, user_id=None):

        if response_type.upper() not in ("CHANNEL", "EPHEMERAL"):
            raise ValueError(
                "Expected one of {} or {} for response_type. Got {}".format(
                    "CHANNEL", "EPHEMERAL", response_type
                )
            )

        if response_type == "CHANNEL":
            posted_message = self.client.api_call(
                "chat.postMessage",
                token=self.bot_token,
                channel=channel_id,
                username=self.name,
                icon_emoji=self.emoji,
                text=message.get("text"),
                attachments=message.get("attachments"),
                title=message.get("title"),
                response_type=message.get("response_type"),
            )
        else:
            posted_message = self.client.api_call(
                "chat.postEphemeral",
                token=self.bot_token,
                channel=channel_id,
                user=user_id,
                icon_emoji=self.emoji,
                text=message.get("text"),
                attachments=message.get("attachments"),
                response_type=message.get("response_type"),
            )

        return posted_message

    def update_message(self, channel_id, ts, message):

        response = self.client.api_call(
            "chat.update",
            token=self.bot_token,
            channel=channel_id,
            username=self.name,
            icon_emoji=self.emoji,
            text=message.get("text"),
            ts=ts,
            attachments=message.get("attachments"),
            response_type="CHANNEL",
        )

        return response
