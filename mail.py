from flask_mail import Mail

mail = Mail()


#mport os
#from dotenv import load_dotenv
#import smtplib
#from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart

## Load environment variables from .env file
#load_dotenv()

#SMTP_SERVER = os.getenv('SMTP_SERVER')
#SMTP_PORT = int(os.getenv('SMTP_PORT'))
#SMTP_USERNAME = os.getenv('MAIL_USERNAME')
#SMTP_PASSWORD = os.getenv('MAIL_PASSWORD')
#MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
#TEST_RECIPIENT = os.getenv('TEST_RECIPIENT')

#def send_test_email():
 #   try:
       # # Create the email
       # msg = MIMEMultipart()
       # msg['From'] = MAIL_DEFAULT_SENDER
       # msg['To'] = TEST_RECIPIENT
       # msg['Subject'] = 'Test Email'
       # body = 'This is a test email sent from Python using your normal provider.'
       # msg.attach(MIMEText(body, 'plain'))

        ## Connect to the server
        #with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
         #   server.starttls()  # Secure the connection
         #   server.login(SMTP_USERNAME, SMTP_PASSWORD)
#            server.sendmail(MAIL_DEFAULT_SENDER, TEST_RECIPIENT, msg.as_string())
        
  #      print('Email sent successfully!')

   # except Exception as e:
    #    print(f'Failed to send email: {e}')

#if __name__ == '__main__':
 #   send_test_email()
