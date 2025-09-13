import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Escopo necessário para enviar e-mails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    creds = None
    # O arquivo 'token.pickle' armazena o token de acesso do usuário.
    # Ele será criado após a primeira autorização.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Se não houver credenciais válidas, inicie o fluxo de autorização.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # O nome do arquivo com as credenciais
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Salve as credenciais para futuras execuções
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    # Constrói o serviço do Gmail para testes
    service = build('gmail', 'v1', credentials=creds)
    print("Autenticação bem-sucedida! O arquivo 'token.pickle' foi gerado.")

if __name__ == '__main__':
    main()
