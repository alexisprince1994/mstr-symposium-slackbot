# Microstrategy Symposium Presentation Materials
Slackbot Application for Presentation at Microstrategy Symposium

This is a slackbot that interacts with a frontend application, as well as Microstrategy to allow for a business user
to consolidate their decision making process to one location. 

This application builds an example use case using another application I wrote, but can be easily substituted for
another application and fields.

# Required Environment/Config Variables
The following environment variables must be set for this to work.

# Custom Application Variables
SLACK_AUTH_TOKEN 

APP_URL

# Slack Variables
CLIENT_ID

CLIENT_SECRET

VERIFICATION_TOKEN

SLACK_TEAM_ID 

SLACK_BOT_OATH_TOKEN

# Microstrategy Settings for any application
MSTR_PROJECT_ID

MSTR_BASE_URL 
(Typically in the form of https://env-xxxxx.customer.cloud.microstrategy.com/MicroStrategyLibrary/api)

MSTR_USERNAME

MSTR_PASSWORD


For every report you want to interact with and filter on, the following attributes are required
Report ID, Attribute Name (if filtering), Attribute ID (if filtering).
Attribute ID is not required, but if not provided, an extra get request will need to be sent to find it.
If not doing something dynamic, I'd suggest hard coding to avoid network latency.

# My Application Microstrategy Variables
MSTR_PRODUCT_REPORT_ID

MSTR_PRODUCT_ATTRIBUTE_NAME

MSTR_PRODUCT_ATTRIBUTE_ID

MSTR_CUSTOMER_REPORT_ID

MSTR_CUSTOMER_ATTRIBUTE_NAME

MSTR_CUSTOMER_ATTRIBUTE_ID
