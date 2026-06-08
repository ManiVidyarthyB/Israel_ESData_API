import boto3

from botocore.exceptions import ClientError

from dotenv import load_dotenv
import os

load_dotenv()

SENDER = "Email Alert System @EZ360 <alert@ez360.tv>"
RECIPIENT = "salehs@ez360.tv"
AWS_REGION = os.getenv("AWS_REGION")
CHARSET = "UTF-8"

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Create a new SES resource and specify a region.
client = boto3.client(
    'ses',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)


class email_alert_EZ360:
    def __init__(self):
        print('init Email')

    def send(self, subject, message):
        subject = subject
        body_text = ''
        body_html = """<html>
                            <head></head>
                            <body>
                              <h1>System Failure Warning</h1>
                              <p>%s</p>
                            </body>
                            </html>
            """ % message
        # Try to send the email.
        try:
            # Provide the contents of the email.
            response = client.send_email(
                Destination={
                    'ToAddresses': [
                        RECIPIENT,
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': body_html,
                        },
                        'Text': {
                            'Charset': CHARSET,
                            'Data': body_text,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': subject,
                    },
                },
                Source=SENDER,
                # If you are not using a configuration set, comment or delete the
                # following line
                # ConfigurationSetName=CONFIGURATION_SET,
            )
        # Display an error if something goes wrong.
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            print("Email sent! Message ID:"),
            print(response['MessageId'])


if __name__ == '__main__':
    t = email_alert_EZ360()
    t.send('Test of EZ360 Email', 'this is a test message')


