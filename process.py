import email
import re

import boto3
import yaml

from panoptes_client import Panoptes, User

BATCH_SIZE = 50

with open('/run/secrets/config.yml', 'r') as f:
    CONFIG = yaml.load(f)

s3 = boto3.resource('s3')

addresses_to_unsubscribe = set()
processed_s3_keys = []

# Limit to avoid paging bug in Panoptes by only requesting a small number
# of users https://github.com/zooniverse/Panoptes/issues/2733
for s3_obj in s3.Bucket(CONFIG['s3']['email_bucket']).objects.filter(
        Prefix=CONFIG['s3']['email_prefix'],
).limit(
        count=BATCH_SIZE,
):
    print("Processing {}".format(s3_obj.key))
    processed_s3_keys.append(s3_obj.key)

    report_email = email.message_from_bytes(s3_obj.get()['Body'].read())
    for report_part in report_email.walk():
        if not report_part.get_content_type() == 'message/rfc822':
            continue
        original_message = report_part.get_payload()[0]
        original_recipient = original_message['X-HmXmrOriginalRecipient']
        if original_recipient:
            subscriber_address_match = re.match(
                r"<(?P<email>(.*@.*))>",
                original_recipient,
            )
            addresses_to_unsubscribe.add(
                subscriber_address_match.group('email')
            )

Panoptes.connect(**CONFIG['panoptes'])

if addresses_to_unsubscribe:
    for user in User.where(email=addresses_to_unsubscribe, page_size=BATCH_SIZE):
        if user.valid_email and user.email in addresses_to_unsubscribe:
            print("Invalidating email for {}".format(user.login))
            user.reload()
            user.valid_email = False
            user.save()

for key in processed_s3_keys:
    print("Deleting {}".format(key))
    s3.Object(CONFIG['s3']['email_bucket'], key).delete()
