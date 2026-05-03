# import requests
# api = '8218f62e9e79da400690bee6b0dd983cafbba098'
# url1 = 'https://www.tribuneindia.com'
# url = f'https://endpoint.apivoid.com/urlrep/v1/pay-as-you-go/?key={api}&url={url1}'
#
# js = requests.get(url).json()
# print(js)
# print(js['data']['report']['domain_blacklist']['detections'])
# print(js['data']['report']['risk_score']['result'])
#
# need_to_be_true = ['is_url_accessible', 'is_domain_ipv4_assigned', 'is_domain_ipv4_valid']
# unknown = []
#
# checks = js['data']['report']['security_checks']
#
# for i in list(checks)[:31]:
#     if checks[i] and checks[i] not in need_to_be_true:
#         unknown.append(i)
# for i in need_to_be_true:
#     if not checks[i]:
#         unknown.append(i)
#
# print(checks['is_domain_very_recent'])
# print(checks['is_domain_recent'])
#
# print(js['data']['report']['server_details']['ip'])
#
# from pygooglenews import GoogleNews
#
# import datetime
#
# import pandas as pd
#
# gn = GoogleNews(lang='en', country='IN')
#
# df = gn.top_news()
# # print(df['entries'][0])
# # for i in df['entries'][0]:
# #     print(i)
# print(df['entries'][0]['title_detail'])
# print(df['entries'][0]['summary'])
#
#
#
#
# input_query = """
# i have two sentences
# sentence1 = "modi is visiting drdo"
# sentence2 = "modi is visiting brdo"
# based on the contextual similarity, is the first statement true based on second statement?, just say yes or no"""
#
# bard = Bard(token=token)
#
# print(bard.get_answer(input_text=input_query)['content'])
# from bs4 import BeautifulSoup
# headline = "massive floods in delhi"
# url = f"https://www.google.com/search?q={headline}"
# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
# }
# response = requests.get(url, headers=headers)
# # soup = BeautifulSoup(response.content, 'html.parser')
# # print(soup.prettify())
# import pandas as pd
#
# # Load the CSV file into a DataFrame
# df = pd.read_csv('C:/Users/vixha/downloads/firstphase.csv')
#
# print(df.keys())
#
# # Drop rows where all elements are missing
# # df_cleaned = df.dropna()
# #
# # # Save the cleaned DataFrame to a new CSV file
# # df_cleaned.to_csv('C:/Users/vixha/downloads/output.csv', index=False)
#
# print("Empty rows have been removed and the cleaned CSV file is saved as 'output.csv'.")
import os

#
# import pandas as pd
#
# # Load the CSV file into a DataFrame
# df = pd.read_csv('C:/Users/vixha/downloads/output.csv')
# # df = df[~df['Branch Name'].isin(['CIV', 'CHE', 'ANE'])]
# df = df.drop(columns=[ 'OC\nGIRLS', 'BC_A\nBOYS', 'BC_A\nGIRLS',
#        'BC_B\nBOYS', 'BC_B\nGIRLS', 'BC_C\nBOYS', 'BC_C\nGIRLS',
#        'BC_D\nGIRLS', 'BC_E\nBOYS', 'BC_E\nGIRLS', 'SC\nBOYS', 'SC\nGIRLS',
#        'ST\nBOYS', 'ST\nGIRLS', 'EWS\nGEN OU', 'EWS\nGIRLS OU'])


# df = df.sort_values(by='BC_D\nBOYS')
# Save the filtered DataFrame to a new CSV file
# df.to_csv('filtered_output.csv', index=False)
# Display the DataFrame before

# Filter out rows where the 'Inst\nCode' column has the value 'Inst'
# df_cleaned = df[df['Inst\nCode'] != 'Inst\nCode']
#
# # Save the cleaned DataFrame to a new CSV file
# import pandas as pd
# import matplotlib.pyplot as plt
# from fpdf import FPDF
#
# # Function to create a table in a PDF
# def create_pdf(data, output_filename):
#     pdf = FPDF()
#     pdf.add_page()
#
#     # Set font
#     pdf.set_font("Arial", size=12)
#
#     # Add a cell
#     pdf.cell(200, 10, txt="CSV Data", ln=True, align='C')
#
#     # Set column width
#     col_width = pdf.w / (len(data.columns) + 1)
#
#     # Set row height
#     row_height = pdf.font_size * 1.5
#
#     # Add column names
#     for col in data.columns:
#         pdf.cell(col_width, row_height, col, border=1)
#     pdf.ln(row_height)
#
#     # Add data
#     for row in data.itertuples():
#         for item in row[1:]:
#             pdf.cell(col_width, row_height, str(item), border=1)
#         pdf.ln(row_height)
#
#     # Save the PDF
#     pdf.output(output_filename)
#
# # Load the CSV file into a DataFrame
# df = pd.read_csv('C:/Users/vixha/downloads/output1.csv')
#
# # Create the PDF
# create_pdf(df, 'C:/Users/vixha/downloads/output.pdf')
#
# print("The CSV file has been converted to a PDF and saved as 'output.pdf'.")

# df.to_csv('C:/Users/vixha/downloads/output1.csv', index=False)

# Display the DataFrame after removing rows


# import pandas as pd
# from fpdf import FPDF
#
# class PDF(FPDF):
#     def header(self):
#         self.set_font('Arial', 'B', 12)
#         self.cell(0, 10, 'CSV Data', 0, 1, 'C')
#
#     def footer(self):
#         self.set_y(-15)
#         self.set_font('Arial', 'I', 8)
#         self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
#
#     def chapter_title(self, title):
#         self.set_font('Arial', 'B', 12)
#         self.cell(0, 10, title, 0, 1, 'L')
#         self.ln(10)
#
#     def add_table(self, df):
#         self.set_font('Arial', 'B', 12)
#         effective_page_width = self.w - 2 * self.l_margin
#         col_width = effective_page_width / len(df.columns)
#         row_height = self.font_size * 1.5
#
#         # Add column headers
#         for col in df.columns:
#             self.cell(col_width, row_height, col, border=1)
#         self.ln(row_height)
#
#         # Add data rows
#         self.set_font('Arial', '', 10)
#         for row in df.itertuples(index=False):
#             for item in row:
#                 x_before_cell = self.get_x()
#                 y_before_cell = self.get_y()
#                 self.multi_cell(col_width, row_height, str(item), border=1)
#                 x_after_cell = self.get_x()
#                 y_after_cell = self.get_y()
#                 self.set_xy(x_after_cell, y_before_cell)
#             self.ln(row_height)
#
# # Load the CSV file into a DataFrame
# df = pd.read_csv('C:/Users/vixha/downloads/output1.csv')
#
#
# # Create PDF
# pdf = PDF()
# pdf.add_page()
# pdf.chapter_title('Filtered and Sorted Data')
# pdf.add_table(df)
#
# # Save the PDF
# pdf.output('C:/Users/vixha/downloads/output.pdf')
#
# print("The CSV file has been converted to a PDF and saved as 'output.pdf'.")

#
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
#
# # Path to your service account JSON key file
# SERVICE_ACCOUNT_FILE = 'C://Users/vixha/Downloads/retool-integration-432509-28976e4b3428.json'
#
# # The ID of the folder where you want to upload files
# FOLDER_ID = '1eA4_NxfSPBDRd4_AMqBFvOlJz3KmbJxj'
#
# # Authenticate and create the Drive service
# SCOPES = ['https://www.googleapis.com/auth/drive.file']
# credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# service = build('drive', 'v3', credentials=credentials)
#
# # List of file paths to upload
# file_paths = ['C:/Users/vixha/PycharmProjects/pythonProject/textfiles/hello.txt']
# def upload_files_to_drive(file_paths, folder_id):
#     for file_path in file_paths:
#         file_metadata = {
#             'name': file_path.split('/')[-1],
#             'parents': [folder_id]
#         }
#         media = MediaFileUpload(file_path)
#         file = service.files().create(
#             body=file_metadata,
#             media_body=media,
#             fields='id'
#         ).execute()
#         print(f"Uploaded {file_path} with File ID: {file.get('id')}")
#
# # Upload the files
#
# def list_files(folder_id):
#     query = f"'{folder_id}' in parents"
#     results = service.files().list(q=query, fields="files(id, name)").execute()
#     files = results.get('files', [])
#
#     if not files:
#         print('No files found in the folder.')
#     else:
#         for file in files:
#             print(f'File Name: {file.get("name")}, File ID: {file.get("id")}')

# list_files(FOLDER_ID)
# fx = open("C://Users/vixha/Downloads/summary.txt", encoding='utf-8')
# x = fx.read()
# for i in range(2,42):
#     fa = open(f'C://Users/vixha/pycharmprojects/pythonProject/texts/{i-1}-chat.txt', mode='w', encoding='utf-8')
#     fa.write(x.split(f"{i}: ")[0].split(f"{i-1}: ")[1])
# #
# fa = open(f'C://Users/vixha/pycharmprojects/pythonProject/texts/1-chat.txt', mode='w', encoding='utf-8')
# fa.write(x.split(f"{2}: ")[0])
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
#
# # Path to your service account JSON key file
# SERVICE_ACCOUNT_FILE = 'C://Users/vixha/Downloads/data-totality-432606-f3-c131fe3d030b.json'
#
# # The ID of the folder where you want to upload files
# FOLDER_ID = '1iUYrQXQ6W9oVhwq681JyanrfV_rOrXGO'
#
# # Authenticate and create the Drive service
# SCOPES = ['https://www.googleapis.com/auth/drive.file']
# credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# service = build('drive', 'v3', credentials=credentials)
#
# # List of file paths to upload
# def upload_files_to_drive(file_paths, folder_id):
#     for file_path in file_paths:
#         file_metadata = {
#             'name': file_path.split('/')[-1],
#             'parents': [folder_id]
#         }
#         media = MediaFileUpload(file_path)
#         file = service.files().create(
#             body=file_metadata,
#             media_body=media,
#             fields='id'
#         ).execute()
#         print(f"Uploaded {file_path} with File ID: {file.get('id')}")
#
# # Upload the files
#
# def list_files(folder_id):
#     query = f"'{folder_id}' in parents"
#     results = service.files().list(q=query, fields="files(id, name)").execute()
#     files = results.get('files', [])
#
#     if not files:
#         print('No files found in the folder.')
#     else:
#         for file in files:
#             print(f'File Name: {file.get("name")}, File ID: {file.get("id")}')
#
# # list_files(FOLDER_ID)
# files = []
# for i in range(2,42):
#     files.append(f'C:/Users/vixha/PycharmProjects/pythonProject/texts/{i-1}-chat.txt')

# for i in files:
#     x = open(i, 'r', encoding='utf-8')
#     d = x.read()
#     c = d.split(" ")[0]
#     print(c, len(d))
#     a = input()
#     fc = open(f'C:/Users/vixha/PycharmProjects/pythonProject/imp_files/{c}.txt', 'w', encoding='utf-8')
#     fc.write(d)
# upload_files_to_drive(files, folder_id=FOLDER_ID)

# # print(os.listdir("C:/Users/vixha/PycharmProjects/pythonProject/imp_files"))
# for i in os.listdir("C:/Users/vixha/PycharmProjects/pythonProject/imp_files"):
#     files.append("C:/Users/vixha/PycharmProjects/pythonProject/imp_files/" + i)
#
# upload_files_to_drive(files, folder_id=FOLDER_ID)

# import requests
# from bs4 import BeautifulSoup
#
# # URL of the webpage
# url = "https://www.eventbrite.com/help/en-us/topics/managing-orders/"
#
# # Send a GET request to fetch the content of the page
# response = requests.get(url)
#
# # Parse the HTML content with BeautifulSoup
# soup = BeautifulSoup(response.text, 'html.parser')
#
# # Extract the heading
# heading = soup.find('h3')  # Assuming the heading is in an <h1> tag, adjust as needed
#
# # Extract the links and text
# links = soup.find_all('a')  # Assuming links are in <a> tags
#
# # Print the extracted content in the desired format
# print(f"**{heading.text.strip()}**\n")
#
# links = links[3:-29]
# act_links = []
# texts = []
# for link in links:
#     href = link.get('href')
#     act_links.append("https://www.eventbrite.com" + href)
#     text = link.text.strip()
#     texts.append(text)
#
#
#
# for i,j in zip(act_links, texts):
#     print(j)
#     url = i
#     response = requests.get(url)
#     response.encoding = response.apparent_encoding
#     soup = BeautifulSoup(response.text, 'html.parser')
#     content_div = soup.find('div', class_="Articles-module--content-wrap--c54c6")
#     all_text = content_div.get_text(separator="\n").strip()
#     fs = open('current3.txt', 'a', encoding=response.encoding)
#     fs.write("**"+j+"**"+'\n')
#     fs.write(all_text)
#     fs.write('\n\n')


import flask