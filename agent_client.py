"""
SMTP Mail Agent/Client
"""
import sys
from exceptions.py import EarlyTerminationError, SocketError, SMTPBreakOfProtocolError

def SMTP_agent_client_engine():
    """Engine for prompting a command-line user for email data and sending the email using SMTP."""

    # Initialize email for user to fill
    email = Email()

    # Fill email with user input
    try:
        email.fill()
    # Terminate program if encounter early EOF
    except EarlyTerminationError:
        return

    # Send email to command-line-argument-specified address
    server_hostname, welc_sock_port_num = sys.argv[1], int(sys.argv[2])
    try:
        email.send(server_hostname, welc_sock_port_num)
    # Terminate on SocketErrors and SMTPBreakOfProtocolErrors
    # (having already closed whatever connection and alerted the user)
    except SocketError:
        return
    except SMTPBreakOfProtocolError:
        return

if __name__ == "__main__":
    SMTP_agent_client_engine()
