import boto3
import os
import json
import logging
import uuid
import time




logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb")


def handler(event, context):

    table = os.environ.get("TABLE_NAME")
    site_url = os.environ.get("WEB_URL")
    logging.info(f"## Loaded table name from environemt variable DDB_TABLE: {table}")
    if event["body"]:
        item = json.loads(event["body"])
        logging.info(f"## Received payload: {item}")
        firstName = str(item["firstName"])
        lastName = str(item["lastName"])
        eventID = str(item["eventID"])
        gmt_time = time.gmtime()
        now = time.strftime('%a, %d %b %Y %H:%M:%S +0000', gmt_time)
        id = firstName + lastName + eventID
        dynamodb_client.put_item(
            TableName=table,
            Item={"id": {"S": id}, "registrationTime": {"S": now}, "firstName": {"S": firstName},"lastName": {"S": lastName}, "eventID": {"S": eventID}},
        )
        message = "Successfully registred: " + firstName + " " +  lastName + " to event: " + eventID
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": site_url},
            "body": json.dumps({"body": message}),
        }
    else:
        logging.info("## Received request without a payload")
        message = "Request contains no body!"
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": site_url},
            "body": json.dumps({"body": message}),
        }
