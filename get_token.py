from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_token():
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: 'credentials.json' file not found!")
                print("Please download credentials.json from Google Cloud Console and place it in this directory.")
                print("Follow instructions in README.md to set up Gmail API.")
                return False
                
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        print("Authentication successful! token.json file created.")
        return True
    else:
        print("Token is already valid.")
        return True

if __name__ == '__main__':
    print("-" * 50)
    print("Gmail API Token Generator")
    print("-" * 50)
    print("This script will help you obtain a token.json file for Gmail Remote Controller.")
    print("A browser window will open. Please login and grant the requested permissions.")
    print()
    
    if get_gmail_token():
        print("\nSetup complete! You can now run the main remote_control.py script.")
        print("Make sure to configure your email in the CONFIG dictionary at the top of remote_control.py")
    else:
        print("\nSetup failed. Please check the error messages above.")
