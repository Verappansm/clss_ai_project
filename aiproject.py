#from langchain.agents.agent_toolkits import GmailToolkit
#from langchain.chat_models import ChatOpenAI
#from langchain.agents import AgentType, initialize_agent
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
import os
from datetime import datetime
import schedule
import time
import imaplib
import email
from email.header import decode_header
from apikey import openapi_key
import smtplib
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from database import session, Email


username="aiprojsample@gmail.com" #This is the mail that will be checked
password=""  #add your mail password....this is not ur login passsword....the method to find the password is given in the README file

os.environ['OPENAI_API_KEY'] = openapi_key

def check_for_new_email():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(username, password)
    mail.select('inbox')
    result, data = mail.search(None, 'UNSEEN')
    if result == 'OK' and data[0]:
        return data[0].split()
    return []

"""def mark_email_as_seen():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login("mverappan@gmail.com", "ifwg xeml wxvz kzut")
    mail.select('inbox')
    result, data = mail.search(None, 'UNSEEN')
    if result == 'OK' and data[0]:
        for num in data[0].split():
            mail.store(num, '+FLAGS', '\\Seen')
        print("Email marked as seen.")
    else:
        print("No unseen emails found.")
"""

def run_final():
    new_emails = check_for_new_email()
    for emailid in new_emails:
        run_email_agent(emailid)


def run_email_agent(email_id):
    
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(username, password)
    mail.select('inbox')
    result, data = mail.fetch(email_id, '(RFC822)')
    for response_part in data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            email_subject = decode_header(msg["subject"])[0][0]
            if isinstance(email_subject, bytes):
                email_subject = email_subject.decode()    # email_subject has mail subject
            email_from = msg.get("From")    #email_from has sender mail id
            

            # Initialize a variable to store the body content
            email_body = ""

            # If the email message is multipart
            if msg.is_multipart():
                for part in msg.walk():
                    # If part is text or html, extract its content
                    if part.get_content_type() == "text/plain":
                        email_body = part.get_payload(decode=True).decode()
                        break  # Exit loop after finding the text/plain part
                    elif part.get_content_type() == "text/html" and not email_body:
                        email_body = part.get_payload(decode=True).decode()
            else:
                # If the email message isn't multipart
                email_body = msg.get_payload(decode=True).decode()

    create(email_body,email_from,email_subject)
    #mark_as_seen(email_id)
    # Logout and close the connection
    mail.logout()

def create(email_body,email_from,email_subject):
    current_date = datetime.now().strftime("%B %d, %Y")
    email_format = f""" 
    <!DOCTYPE html> 
    <html> 
    <head> 
    <style> 
    table {{ width: 100%; border-collapse: collapse; }} 
    th, td {{ border: 1px solid black; padding: 8px; text-align: left; }} 
    th {{ background-color: #f2f2f2; }} 
    </style> 
    </head> 
    <body> 
    <table> 
    <tr> 
    <th>Sender Email</th> 
    <th>From Date</th> 
    <th>To Date</th> 
    <th>Current Date</th> 
    </tr> 
    <tr> 
    <td>{email_from}</td> 
    <td><!-- From_date from LLM output --></td> 
    <td><!-- To_date from LLM output --></td> 
    <td>{current_date}</td> 
    </tr> 
    </table> 
    </body> 
    </html> 
    """

    prompt_template ="Take note of this date: {current_date} and this email content: {email_body}. Now, generate an email body that includes only a table with the following columns: Sender ({email_from}),From_date, To_date, and Current_date. If necessary, calculate the From_date and To_date based on the information provided in the email.Generate the output in the form of table mentioned in {email_format}. Format all dates in {current_date}"
    
    prompt = PromptTemplate(
        input_variables=["current_date", "email_body", "email_from","email_format"],
        template=prompt_template,
    )
    llm = OpenAI(temperature=0.6)
    chain = LLMChain(llm=llm, prompt=prompt)

    email_content = chain.run({
        "current_date": current_date,
        "email_body": email_body,
        "email_from": email_from,
        "email_format": email_format
    })

    soup = BeautifulSoup(email_content, 'html.parser')
    from_date = soup.find_all('td')[1].text.strip()
    to_date = soup.find_all('td')[2].text.strip()

    # Store email in database
    email_record = Email(
        email_from=email_from,
        email_subject=email_subject,
        from_date=from_date,
        to_date=to_date
    )
    session.add(email_record)
    session.commit()
    print("Email stored in database")

    email_content=email_body+"\n \n"+email_content


    recipient_email = ""  #receipient email here
    send_email(email_content,recipient_email,email_subject)

#send email
def send_email(email_content, recipient_email,email_subject):
    msg = MIMEText(email_content)
    msg['Subject'] = email_subject
    msg['From'] = username
    msg['To'] = recipient_email
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(username, password)
    server.sendmail(username, recipient_email, msg.as_string())
    server.quit()

"""def mark_as_seen(email_id):
    # Mark the email as seen
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login("", "")
    mail.select('inbox')
    mail.store(email_id, '+FLAGS', '\\Seen')
    mail.logout()

    toolkit = GmailToolkit()
    current_date = datetime.now().strftime("%B %d, %Y")
    llm = ChatOpenAI(temperature=0.4)
    agent = initialize_agent(tools=toolkit.get_tools(), llm=llm, verbose=True, max_iterations=1000, max_execution_time=1600, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION)
    email_content = f"Use the current date: {current_date},now create a draft to ramyajaysha@gmail.com by using the content :{email_content} and transforming the data in the manner that is stated below: first display Date of 'From Date', then display Date of 'To Date', then display date of 'Current Date',then only display the 'reason' if specified ,then display the {sender_email}, provide actual dates , if necessary do calculations needed to find the dates if not specified using calendar"

    print(agent.run(email_content))
    mail.store(email_id, '+FLAGS', '\\Seen')"""



# Schedule the email check and agent run every 10 seconds
schedule.every(5).seconds.do(run_final)


# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
