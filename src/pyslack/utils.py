

def build_price_request_buttons():

	approve_button = SlackButton(name="approveButton", value="approve_button", text="Approve", style="primary")
	deny_button = SlackButton(name="denyButton", value="deny_button", text="Deny", style="danger")
	review_later_button = SlackButton(name="reviewLaterButton", value="review_later_button", text="Review Later")

	buttons = [approve_button, deny_button, review_later_button]

	return [button.to_dict() for button in buttons]


# view_filter_example = {
# 	"viewFilter": {
# 		# Attribute goes here
# 		"operands": [
# 			{
# 				"type": "attribute",
# 				"id": "whatever the attribute id is",
# 				"name": "Item"
# 			},
# 			{
# 				"type": "elements",
# 				"elements": [
# 					"id": "whatever the attribute id is:element number",
# 					"name": "Art As Experience"
# 				]
# 			}
# 		]
# 	}
# }