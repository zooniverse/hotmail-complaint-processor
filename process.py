import email
import re

import boto3

from panoptes_client import Panoptes, User


S3_EMAIL_BUCKET = 'zooniverse-replies'
S3_EMAIL_PREFIX = 'hotmail-complaints/'

s3 = boto3.resource('s3')

addresses_to_unsubscribe = set()
processed_s3_keys = []

for s3_obj in s3.Bucket(S3_EMAIL_BUCKET).objects.filter(
    Prefix=S3_EMAIL_PREFIX,
):
    print("Processing {}".format(s3_obj.key))
    processed_s3_keys.append(s3_obj.key)

    report_email = email.message_from_bytes(s3_obj.get()['Body'].read())
    for report_part in report_email.walk():
        if not report_part.get_content_type() == 'message/rfc822':
            continue
        original_message = report_part.get_payload()[0]
        subscriber_address_match = re.match(
            r"<(?P<email>(.*@.*))>",
            original_message['X-HmXmrOriginalRecipient'],
        )
        addresses_to_unsubscribe.add(subscriber_address_match.group('email'))

# TODO: Unsubscribe the users with panoptes_client

# TODO: Delete objects from S3
