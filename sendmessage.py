import os
import time

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class sendMessage:
    def __init__(self, news, title, emails, handles):
        self.true_news = news
        self.fake_news = title
        self.emails = emails
        self.handles = handles
        self.instagram = 'https://www.instagram.com/'
        self.twitter = 'https://twitter.com/'
        self.facebook = 'https://www.facebook.com/'
        self.mail = os.environ.get('GMAIL_ADDRESS', '')
        self.instagram_handle = ''
        self.twitter_handle = ''
        self.facebook_handle = ''
        # self.driver = Chrome(service=Service(ChromeDriverManager().install()))

    def segregate_handles(self):
        for i in self.handles:
            if i.find('instagram') != -1 and i.count('/')<5:
                x = i
                com = i.find('com')
                com += 4
                stc = com
                while com < len(x) and x[com] != '/' and x[com] != '?':
                    com += 1
                x = x[stc:com]
                self.instagram_handle = x

            if i.find('twitter') != -1 and i.count('/')<5:
                x = i
                com = i.find('com')
                com += 4
                stc = com
                while com < len(x) and x[com] != '/' and x[com] != '?':
                    com += 1
                x = x[stc:com]
                self.twitter_handle = x

            if i.find('facebook') != -1 and i.count('/')<5:
                x = i
                com = i.find('com')
                com += 4
                stc = com
                while com < len(x) and x[com] != '/' and x[com] != '?':
                    com += 1
                x = x[stc:com]
                self.facebook_handle = x

    def segregate_emails(self):
        self.emails = set(self.emails)
        self.emails = list(self.emails)[:3]

    def send_email(self):
        for i in self.emails:
            sender_email = self.mail
            sender_password = os.environ.get('GMAIL_APP_PASSWORD', '')
            receiver_email = i
            subject = 'Test Email'
            message = 'This is a test email sent from Python.'

            email_message = MIMEMultipart()
            email_message['From'] = sender_email
            email_message['To'] = receiver_email
            email_message['Subject'] = subject
            email_message.attach(MIMEText(message, 'plain'))

            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
            smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
            smtp_connection.starttls()

            smtp_connection.login(sender_email, sender_password)

            smtp_connection.sendmail(sender_email, receiver_email, email_message.as_string())

            smtp_connection.quit()

    def send_on_instagram(self):
        self.driver = Chrome(service=Service(ChromeDriverManager().install()))
        username = os.environ.get('INSTAGRAM_USERNAME', '')
        password = os.environ.get('INSTAGRAM_PASSWORD', '')
        self.driver.get(self.instagram)
        self.driver.set_window_size(500, 600)
        time.sleep(6)
        username_element = self.driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[1]/div/label/input')
        password_element = self.driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[2]/div/label/input')
        login_element = self.driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[3]/button')
        username_element.send_keys(username)
        password_element.send_keys(password)

        login_element.send_keys(Keys.ENTER)
        time.sleep(6)
        not_now1 = self.driver.find_element(By.CSS_SELECTOR, "div[role='button']")
        not_now1.send_keys(Keys.ENTER)
        time.sleep(6)
        not_now2_div = self.driver.find_element(By.CSS_SELECTOR, 'div[class="_a9-z"]')
        not_now2 = not_now2_div.find_elements(By.CSS_SELECTOR, 'button')[1]
        not_now2.send_keys(Keys.ENTER)
        time.sleep(4)
        input_element = self.driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Search input"]')
        print(self.instagram_handle)
        input_element.send_keys(self.instagram_handle)
        time.sleep(3)
        input_element_div = self.driver.find_element(By.CSS_SELECTOR, "div[role='none']")
        input_element = input_element_div.find_element(By.CSS_SELECTOR, 'a')
        input_element.send_keys(Keys.ENTER)
        time.sleep(5)
        message_element = self.driver.find_elements(By.CSS_SELECTOR, "div[role='button']")[2]
        message_element.send_keys(Keys.ENTER)
        time.sleep(5)
        send_text_element = self.driver.find_element(By.CSS_SELECTOR, 'div[role="textbox"]')
        send_text_element.send_keys(self.true_news + ' ' + self.fake_news)
        send_text_element.send_keys(Keys.ENTER)

        time.sleep(2)
        self.driver.quit()

    def send_on_twitter(self):
        username = os.environ.get('TWITTER_USERNAME', '')
        password = os.environ.get('TWITTER_PASSWORD', '')
        
        self.driver.get(self.twitter)
        # time.sleep(300)
        # login_element = self.driver.find_element(By.XPATH, '/ html / body / div[1] / div / div / div[1] / div / div[1] / div / div / div / div / div[2] / div / div / div[1] / a')
        # login_element.send_keys(Keys.ENTER)
        time.sleep(5)
        email_element = self.driver.find_element(By.CSS_SELECTOR, 'input[autocorrect="on"]')
        email_element.send_keys(username)
        email_element.send_keys(Keys.ENTER)
        time.sleep(5)
        password_element = self.driver.find_element(By.NAME, 'password')
        password_element.send_keys(password)
        password_element.send_keys(Keys.ENTER)
        time.sleep(5)
        search_element = self.driver.find_element(By.CSS_SELECTOR, "a[href='/explore']")
        search_element.send_keys(Keys.ENTER)
        time.sleep(7)
        input_element = self.driver.find_element(By.CSS_SELECTOR, 'input')
        input_element.send_keys(self.twitter_handle)
        time.sleep(4)
        user_element = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="TypeaheadUser"]')
        user_element.send_keys(Keys.ENTER)
        time.sleep(3)
        next_element = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"]')
        next_element.send_keys(Keys.ENTER)
        time.sleep(3)
        text_input = self.driver.find_element(By.CSS_SELECTOR, 'div[role="textbox"]')
        text_input.send_keys(self.true_news + ' ' +self.fake_news)
        text_input.send_keys(Keys.ENTER)
        time.sleep(3)
        # self.driver.quit()

    def send_on_facebook(self):
        username = os.environ.get('FACEBOOK_USERNAME', '')
        password = os.environ.get('FACEBOOK_PASSWORD', '')
        self.driver.get(self.facebook)
        email_element = self.driver.find_element(By.XPATH, '//*[@id="email"]')
        email_element.send_keys(username)
        password_element = self.driver.find_element(By.XPATH, '//*[@id="pass"]')
        password_element.send_keys(password)
        login_element = self.driver.find_element(By.CSS_SELECTOR, 'button')
        login_element.send_keys(Keys.ENTER)
        time.sleep(10000)
        input_element = self.driver.find_element(By.CSS_SELECTOR, 'input[dir="ltr"]')
        input_element.send_keys(self.facebook_handle)
        input_element.send_keys(Keys.ENTER)
        time.sleep(6)
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, 'a[class ="x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g xt0b8zv x1s688f xq9mrsl"]')
            element.send_keys(Keys.ENTER)
        except:
            d_elem = self.driver.find_element(By.CSS_SELECTOR, 'div[class="x78zum5 x1n2onr6 xh8yej3"]')
            print(d_elem, d_elem.text)
            element = d_elem.find_element(By.CSS_SELECTOR, 'a[class="x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz xt0b8zv xzsf02u x1s688f"]')
            print(element, element.text)
            element.send_keys(Keys.ENTER)

        time.sleep(7000)
        message_element = ''
        message_elements = self.driver.find_element(By.CSS_SELECTOR,
                                              'diiv[aria-label="Message"]')
        # if len(message_elements) > 1:
        #     message_element = message_elements[1]
        # else:
        #     message_element = message_elements[0]
        message_elements.send_keys(Keys.ENTER)
        time.sleep(5)

        text_elements = self.driver.find_element(By.CSS_SELECTOR,
                                           'div[aria-label = "Message"]')
        text_element = ""
        # if len(text_elements) > 1:
        #     text_element = text_elements[1]
        # else:
        #     text_element = text_elements[0]

        text_elements.send_keys(self.true_news + ' ' + self.fake_news)
        text_elements.send_keys(Keys.ENTER)
        time.sleep(2)
        # self.driver.quit()

    def run(self):
        self.segregate_handles()
        self.segregate_emails()
        try:
            self.send_email()
        except:
            pass
        # try:
        #     self.send_on_facebook()
        # except:
        #     pass
        # try:
        #     self.send_on_instagram()
        # except:
        #     pass
        # try:
        #     self.send_on_twitter()
        # except:
        #     pass
        


# sendMessage('your account has been deleted by instagram ', 'ignore this', ['murthyshreeya@gmail.com'], []).run()


