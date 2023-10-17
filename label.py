import os
import re  # Regular expressions library
import email
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, simpledialog
from tkhtmlview import HTMLLabel
import pandas as pd
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import email.utils

# Function to convert CSS rgb colors to hexadecimal
def css_rgb_to_hex(match):
    rgb = match.groups()
    r, g, b = map(int, rgb[:3])
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

# Function to clean HTML content
def clean_html_content(content):
    # Regular expression to find CSS rgb() colors
    css_rgb_colors = re.compile(r'rgb\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)')

    # Replace 'rgb(r, g, b)' with '#rrggbb'
    content = css_rgb_colors.sub(css_rgb_to_hex, content)

    return content

def extract_content_from_eml(file_path):
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    # Extract metadata
    metadata = {
        'subject': msg['subject'],
        'from': msg['from'],
        'to': msg['to'],
        'date': msg['date'],
        'cc': msg.get('cc'),
        'has_attachment': any(part.get_filename() for part in msg.walk() if part.get_content_maintype() == 'application'),
        'num_recipients': len(email.utils.getaddresses(msg.get_all('to', []) + msg.get_all('cc', []))),
    }

    # Extract content
    content = ''
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # check if this part is an attachment
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                charset = part.get_content_charset()
                content += part.get_payload(decode=True).decode(charset if charset else 'utf-8', 'ignore')
            elif ctype == 'text/html':
                charset = part.get_content_charset()
                html_content = part.get_payload(decode=True).decode(charset if charset else 'utf-8', 'ignore')
                soup = BeautifulSoup(html_content, 'html.parser')
                content += soup.get_text(separator=' ')
    else:
        charset = msg.get_content_charset()
        content_type = msg.get_content_type()
        raw_content = msg.get_payload(decode=True).decode(charset if charset else 'utf-8', 'ignore')
        if content_type == 'text/html':
            soup = BeautifulSoup(raw_content, 'html.parser')
            content = soup.get_text(separator=' ')
        else:
            content = raw_content

    return content.strip(), metadata


def display_html_content(root, content):
    """
    This function displays the HTML content of an email and prompts the user to enter a label.
    
    Parameters:
    root (tk.Tk): The Tkinter root window.
    content (str): The HTML content of the email.
    
    Returns:
    str: The label entered by the user.
    """
    # Create a top-level window
    top = Toplevel(root)
    top.geometry("800x600")  # Specify the size of the window
    
    # Create an HTMLLabel widget to display the content
    html_label = HTMLLabel(top, html=clean_html_content(content))
    html_label.pack(fill="both", expand=True)
    
    # Prompt the user to enter a label
    user_label = simpledialog.askstring("Input", "Enter label for this email:",
                                        parent=top)
    
    # Close the top-level window
    top.destroy()
    
    return user_label

def main_app(root, directory_path):
    csv_file_path = 'labeled_emails.csv'
    
    # Check if CSV file exists
    if os.path.exists(csv_file_path):
        email_data = pd.read_csv(csv_file_path)
        # If 'File_Name' column doesn't exist, create it and set it to NaN
        if 'File_Name' not in email_data.columns:
            email_data['File_Name'] = pd.NA  # Setting all values in the new column to NaN
            last_processed_index = -1  # Set to -1 to start from the beginning
        else:
            if not email_data.empty:
                sorted_files = sorted([f for f in os.listdir(directory_path) if f.endswith('.eml')])
                last_file_processed = email_data.iloc[-1]['File_Name']
                last_processed_index = sorted_files.index(last_file_processed)
            else:
                last_processed_index = -1
    else:
        # Create an empty DataFrame with 'File_Name' column
        email_data = pd.DataFrame(columns=['File_Name', 'Subject', 'From', 'To', 'Date', 'CC', 'Has_Attachment', 'Num_Recipients', 'Content', 'Label'])
        last_processed_index = -1

    # Get a sorted list of .eml files in the directory
    files = sorted([f for f in os.listdir(directory_path) if f.endswith('.eml')])

    # Loop through each .eml file in the directory starting from the last processed index
    for file_name in files[last_processed_index + 1:]:
        file_path = os.path.join(directory_path, file_name)
        
        # Extract content and metadata
        content, metadata = extract_content_from_eml(file_path)
        
        # Check if content is empty and skip
        if not content.strip():
            print(f"Skipping {file_name} due to empty content.")
            continue

        user_label = display_html_content(root, content)

        # If user doesn't enter a label, continue to next email
        if user_label is None or user_label == '':
            print(f"Skipping {file_name} due to no label provided.")
            continue
        
        # Add email data and label to the DataFrame
        new_row = {
            'File_Name': file_name,
            'Subject': metadata['subject'],
            'From': metadata['from'],
            'To': metadata['to'],
            'Date': metadata['date'],
            'CC': metadata['cc'],
            'Has_Attachment': metadata['has_attachment'],
            'Num_Recipients': metadata['num_recipients'],
            'Content': content,
            'Label': user_label
        }
        new_row_df = pd.DataFrame([new_row])  # Convert the dictionary to a DataFrame with a single row


        # Save to CSV after each labeling
        email_data = pd.concat([email_data, new_row_df], ignore_index=True)

    print("All emails have been processed.")




if __name__ == "__main__":
    # Create the main root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Set directory path containing the .eml files
    directory_path = 'train'  # Change this to the path of your .eml files
    main_app(root, directory_path)

    # End the Tkinter main loop
    root.quit()
