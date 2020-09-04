"""
Python slack message class for use w/ dad joke bot
"""
import random
import json


DAD_JOKES = [
    'A termite walks into a bar and asks, "Is the bar tender here?"',
    'MOM: "How do I look?" DAD: "With your eyes."',
    "What is Beethoven’s favorite fruit? A ba-na-na-na.",
    "Two guys walk into a bar, the third one ducks.",
    "What is the best time to go to the dentist? Tooth hurt-y.",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "You're American when you go into the bathroom, and you're American when you come out, but do you know what you are while you're in there? European.",
    "Did you know the first French fries weren't actually cooked in France? They were cooked in Greece.",
    "Want to hear a joke about a piece of paper? Never mind... it's tearable.",
    "I just watched a documentary about beavers. It was the best dam show I ever saw!",
    "If you see a robbery at an Apple Store does that make you an iWitness?",
    "Spring is here! I got so excited I wet my plants!",
    "What’s Forrest Gump’s password? 1forrest1",
    "I bought some shoes from a drug dealer. I don't know what he laced them with, but I was tripping all day!",
    "When a dad drives past a graveyard: Did you know that's a popular cemetery? Yep, people are just dying to get in there!",
    "I have a BA, MS, and PH.D, but my friends still call me an idiot. It's a third degree burn.",
]


class SlackButton(object):
    def __init__(
        self,
        name: str,
        value: str,
        text: str = None,
        style: str = None,
        confirm: dict = None,
        callback_id: str = None,
    ):
        self.name = name
        self.value = value
        self.text = text
        self.style = style
        self.confirm = confirm
        self.callback_id = callback_id
        self.type = "button"

    def to_dict(self):
        """
		Returns the SlackButton object as a dictionary so it is 
		serializable. Deletes unused attributes so Slack's 
		API can handle the defaults.
		"""

        data_dict = {
            "name": self.name,
            "value": self.value,
            "text": self.text or self.value,
            "style": self.style,
            "confirm": self.confirm,
            "type": self.type,
            "callback_id": self.callback_id,
        }

        dict_out = {}

        for key, val in data_dict.items():
            if val is not None:
                dict_out[key] = val

        return dict_out


class InteractiveRequest(object):

    """
	A class used to wrap a request sent by Slack's API as a result of 
	using the interactive message API. 
	"""

    def __init__(self, request):
        """
		:param request: object, request object from Slack that is generated
			as a result of using the interactive message API.
		"""

        self.request = request
        self.payload = json.loads(self.request.form.get("payload"))
        self.actions = self.payload.get("actions")
        self.channel_id = self.payload.get("channel").get("id")
        self.team_id = self.payload.get("team").get("id")
        self.token = self.payload.get("token")
        self.msg_type = self.payload.get("type")
        self.action_ts = self.payload.get("action_ts")
        self.message_ts = self.payload.get("message_ts")
        self.response_url = self.payload.get("response_url")
        self.callback_id = self.payload.get("callback_id")
        self.original_message = self.payload.get("original_message")

        # Attributes that will be used later
        self.return_message = None

    def _validate_token(self, verification_token: str):

        """
		:param verification_token: str, system's secret token used to 
			authenticate Slack's requests.
		"""

        if self.token != verification_token:
            error_msg = "Invalid token. {} was sent".format(self.token)
            return (error_msg, 403)

        return (None, None)

    def _validate_teamid(self, team_id: str):

        """
		:param team_id: str, authorized team id to verify the request against.
		"""

        if self.team_id != team_id:
            error_msg = "Unauthorized team usage. Team {} has not been approved".format(
                self.team_id
            )
            return (error_msg, 403)

        return (None, None)

    def _validate_msg_type(self, msg_type: str = "interactive_message"):

        """
		:param msg_type: str, expected message type from the Slack API
		"""

        if self.msg_type != msg_type:
            error_msg = "{} type expected. Got {}".format(msg_type, self.msg_type)
            return (error_msg, 403)

        return (None, None)

    def _validate_callback_id(self, callback_id: str):

        """
		:param callback_id: str, expected callback to be sent with the original request
			and points to a valid handler.
		"""

        if self.callback_id != callback_id:
            error_msg = "Incorrect callback assigned. Got {}".format(self.callback_id)
            return (error_msg, 403)

        return (None, None)

    def validate_request(
        self,
        verification_token: str,
        team_id: str,
        callback_id: str,
        msg_type="interactive_message",
    ):

        """
		:param verification_token: str, valid token kept server side to ensure
			the requests are valid
		:param team_id: str, valid team id to ensure only the proper teams have accessed
			the bot as users can be in multiple teams.
		:param callback_id: str, expects the callback_id of the action handler on the 
			original request.
		:param msg_type: str, the message type of the expected API response.
		"""

        error_msg, status_code = self._validate_token(verification_token)

        if error_msg is not None:
            return (error_msg, status_code)

        error_msg, status_code = self._validate_teamid(team_id)

        if error_msg is not None:
            return (error_msg, status_code)

        error_msg, status_code = self._validate_msg_type(msg_type)

        if error_msg is not None:
            return (error_msg, status_code)

        error_msg, status_code = self._validate_callback_id(callback_id)

        if error_msg is not None:
            return (error_msg, status_code)

        return (None, None)


class InteractiveButtonRequest(InteractiveRequest):
    def __init__(self, *args, **kwargs):
        """
		Uses the parent's constructor and assigns a static variable for 
		expected number of actions (since you can only click on one button)
		"""
        super().__init__(*args, **kwargs)

        self.expected_actions = 1

        # Attribute that is getting assigned later.
        self.action = None
        self.action_value = None

    def _validate_actions(self):

        if self.actions is None:
            error_msg = "No actions found"
            return (error_msg, 403)

        if len(self.actions) != self.expected_actions:
            error_msg = "Unexpected number of actions. Got {} and expected {}".format(
                self.actions, self.expected_actions
            )
            return (error_msg, 403)

        try:
            self.action = self.actions[0]
            self.action_value = self.action["value"]
        except IndexError:
            raise IndexError(
                "Passed validation check but index value of 0 wasnt found. \
				Self.actions has length {} and I was expecting length 1.".format(
                    len(self.actions)
                )
            )
        except KeyError:
            raise KeyError(
                'Slacks API expects there to be a key "value" for the \
				value of the action taken by the user. If youre seeing this, \
				slacks API probably changed.'
            )

        return (None, None)

    def validate_request(self, *args, **kwargs):
        """
		Adds additional request validation to ensure that we have matching number
		of actions.
		"""

        error_msg, status_code = super().validate_request(*args, **kwargs)

        if error_msg is not None:
            return (error_msg, status_code)

        error_msg, status_code = self._validate_actions()

        if error_msg is not None:
            return (error_msg, status_code)

        return (None, None)

    def build_response(self, new_attachments: list):

        # Deleting the actions from the original message so the user
        # can't send us through an endless loop.
        if "actions" in self.return_message["attachments"][0]:
            self.return_message["attachments"][0].pop("actions")

        for new_attachment in new_attachments:
            self.return_message["attachments"].append(new_attachment)


class DadJokeMessage(object):

    """
	Instanciates a message object to create
	the data joke.
	"""

    def __init__(self, joketext, response_type="in_channel"):
        self.text = "*Your random Dad Joke is: *"
        self.joketext = joketext
        self.response_type = response_type

        # Attachments that are updated in create_attachment method
        self.attachment = None

    def create_attachment(self):

        """
		Creates a JSON serializable object to be sent along with the request back to Slack
		"""

        good_joke_button = SlackButton(
            name="goodJokeButton", value="good_joke", text="Great Joke!"
        )
        good_joke_dict = good_joke_button.to_dict()
        bad_joke_button = SlackButton(
            name="badJokeButton", value="bad_joke", text="Bad Joke!!"
        )
        bad_joke_dict = bad_joke_button.to_dict()

        self.attachment = {
            "text": self.text,
            "attachments": [
                {
                    "attachment_type": "default",
                    "callback_id": "voteonjoke",
                    "text": self.joketext,
                    "actions": [good_joke_dict, bad_joke_dict,],
                }
            ],
        }

        return self.attachment
