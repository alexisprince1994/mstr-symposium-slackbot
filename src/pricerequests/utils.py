# Standard Library
import json
import logging
import os

import requests

# Third Party
from flask import Response, jsonify

# Local
from src.mstrest.client import FilteringReport, MstrClient, Report
from src.mstrest.parser import MstrParser
from src.pyslack.slack_ui import (
    SlackActionBar,
    create_action_buttons,
    create_customer_analysis,
    create_product_analysis,
    create_slack_price_request,
)
from zappa.async import task

# Third Party


logging.basicConfig(level=logging.DEBUG)


def respond_to_price_request(req, pybot, msg_ts, current_app, response_url):
    """
    TO DO:
            REFACTOR THIS MONSTROSITY
    """

    channel_id = req.form.get("channel_id")

    # Used as the error message template
    error_msg = {
        "text": "Uh oh! Looks like the app is down!",
        "attachments": [{"text": "Please try again later!"}],
    }

    response = requests.get(
        current_app.config["APP_URL"] + "/get",
        headers={"X-SLACK-AUTH-TOKEN": current_app.config["SLACK_AUTH_TOKEN"]},
    )

    if response.status_code != 200:
        logging.debug(
            "Status code was not 200. Status code was {}".format(response.status_code)
        )
        pybot.update_message(channel_id, msg_ts, message=error_msg)

        return None

    price_request = response.json()

    # If there are no more price requests
    if price_request.get("price_request", None) is None:
        logging.debug("No price request available.")
        caughtup_message = {
            "text": "All caught up!",
            "attachments": [
                {
                    "attachment_type": "default",
                    "text": price_request.get("error_message"),
                }
            ],
        }

        response = pybot.update_message(channel_id, msg_ts, message=caughtup_message)

        return None

    # Initializing the Microstrategy Client

    mstr = MstrClient(
        current_app.config["MSTR_PROJECT_ID"], current_app.config["MSTR_BASE_URL"]
    )
    login_response = mstr.login(
        current_app.config["MSTR_USERNAME"], current_app.config["MSTR_PASSWORD"]
    )

    # Indicates the MSTR Cloud instance isn't running.
    if login_response.status_code == 503:
        # Sends a message to Slack saying MSTR is down, then bails
        pybot.update_message(channel_id, msg_ts, message=error_msg)

        return None

    slack_ui = build_slack_ui(mstr, current_app, price_request)
    price_message = {"text": "Price Request Analysis", "attachments": slack_ui}

    pybot.update_message(channel_id, msg_ts, message=price_message)

    mstr.logout()


def build_slack_ui(mstr, current_app, price_request):

    header_ui = build_header_ui(price_request["price_request"])
    price_ui = build_price_report(price_request)

    product_ui = build_product_report(
        mstr, current_app, price_request["price_request"]["product_name"]
    )

    customer_ui = build_customer_report(
        mstr, current_app, price_request["price_request"]["customer_name"]
    )

    action_bar = build_slack_buttons(price_request)

    return [header_ui, product_ui, customer_ui, price_ui, action_bar]


def build_header_ui(pr):

    units = pr["requested_units"]
    formatted_units = format_number(units, "{:,.0f}", "-{:,.0f}")
    product_name = pr["product_name"]
    request_date = pr["request_date"]
    customer_name = pr["customer_name"]

    title = "{} of {} requested on {} by {}".format(
        formatted_units, product_name, request_date, customer_name
    )
    request_reason = pr["request_reason"] or "Request Reason not provided."
    return {"title": title, "text": request_reason}


def build_slack_buttons(app_response):

    approve, deny = app_response["actions"]
    post_route = app_response["price_request"]["id"]

    actions = SlackActionBar(post_route, approve, deny)
    return actions.to_json()


def build_price_report(app_response, *, title=None, text=None):

    # Default values for the header section.
    title = title or "Price Delta Analysis"
    text = text or "Difference between normal price and requested"

    units = app_response["price_request"]["requested_units"]
    current_price = app_response["price_request"]["current_price"]
    requested_price = app_response["price_request"]["requested_price"]
    total_cost = units * app_response["price_request"]["cost"]
    current_profit = current_price * units - total_cost
    current_margin = current_profit / (current_price * units)
    requested_profit = requested_price * units - total_cost
    requested_margin = requested_profit / (requested_price * units)

    # Formatting and Ordering
    fields = [
        ("Normal Price", current_price, "${:,.2f}", "-${:,.2f}"),
        ("Requested Price", requested_price, "${:,.2f}", "-${:,.2f}"),
        ("Normal Margin", 100 * current_margin, "{:,.2f}%", "-{:,.2f}%"),
        ("Requested Margin", 100 * requested_margin, "{:,.2f}%", "-{:,.2f}%"),
        ("Normal Gross Profit", current_profit, "${:,.0f}", "-${:,.0f}"),
        ("Requested Profit", requested_profit, "${:,.0f}", "-${:,.0f}"),
    ]

    output = {"title": title, "text": text, "fields": []}

    for field in fields:
        header, val, pos_format, neg_format = field
        val = format_number(val, pos_format, neg_format)
        output["fields"].append({"title": header, "value": val, "short": True})

    return output


def build_product_report(mstr_client, current_app, product):

    """
    Builds the product section of the final price request
    for Slack.

    """

    MSTR_PRODUCT_REPORT_ID = current_app.config.get("MSTR_PRODUCT_REPORT_ID")
    MSTR_PRODUCT_ATTRIBUTE_NAME = current_app.config.get("MSTR_PRODUCT_ATTRIBUTE_NAME")
    MSTR_PRODUCT_ATTRIBUTE_ID = current_app.config.get("MSTR_PRODUCT_ATTRIBUTE_ID")

    view_filter = filter_mstr_for_element(
        mstr_client,
        MSTR_PRODUCT_REPORT_ID,
        MSTR_PRODUCT_ATTRIBUTE_NAME,
        product,
        attribute_id=MSTR_PRODUCT_ATTRIBUTE_ID,
    )

    product_report = Report.from_client(MSTR_PRODUCT_REPORT_ID, mstr_client)
    report = product_report.create(mstr_client.session, view_filter=view_filter)
    parser = MstrParser(report.json())
    data = [row for row in parser.parse_rows()][0]["metrics"]
    slack_ui = create_product_analysis(
        avg_units=data["Avg Units Received"]["rv"],
        stdev_units=data["StDev Units"]["rv"],
    )

    return slack_ui


def build_customer_report(mstr_client, current_app, customer):
    """
    Builds the customer section of the final price request
    for Slack.

    """

    MSTR_CUSTOMER_ATTRIBUTE_NAME = current_app.config.get(
        "MSTR_CUSTOMER_ATTRIBUTE_NAME"
    )
    MSTR_CUSTOMER_REPORT_ID = current_app.config.get("MSTR_CUSTOMER_REPORT_ID")
    MSTR_CUSTOMER_ATTRIBUTE_ID = current_app.config.get("MSTR_CUSTOMER_ATTRIBUTE_ID")

    view_filter = filter_mstr_for_element(
        mstr_client,
        MSTR_CUSTOMER_REPORT_ID,
        MSTR_CUSTOMER_ATTRIBUTE_NAME,
        customer,
        attribute_id=MSTR_CUSTOMER_ATTRIBUTE_ID,
    )

    customer_report = Report.from_client(MSTR_CUSTOMER_REPORT_ID, mstr_client)
    report = customer_report.create(mstr_client.session, view_filter=view_filter)
    parser = MstrParser(report.json())

    data = [row for row in parser.parse_rows()][0]["metrics"]

    slack_ui = create_customer_analysis(
        overall=data["Overall Rank"]["rv"], regional=data["Regional Rank"]["rv"]
    )

    return slack_ui


def filter_mstr_for_element(
    mstr_client, report_id, attribute_name, element_value, *, attribute_id=None
):

    filter_report = FilteringReport.from_client(report_id, mstr_client)

    if attribute_id is None:
        filter_report.get_definition(mstr_client.session)
        for attribute in filter_report.report_definition["attributes"].values():
            if attribute.name == attribute_name:
                attribute_id = attribute.id
            break
        else:
            raise ValueError(
                "customer_attribute_name does not match any \
			attributes on this report. Please double check the attribute list \
			and check again."
            )

    report_response = filter_report.create(
        mstr_client.session, attribute_id, attribute_name
    )

    print("report_response is {}".format(report_response))
    element_view_filter = filter_report.build_view_filter(
        report_response.json(), element_value
    )
    return element_view_filter


def format_number(number, number_format, negative_format):

    if number >= 0:
        return number_format.format(number)
    else:
        return negative_format.format(abs(number))
