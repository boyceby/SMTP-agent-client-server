"""
SMTP Mail Server
"""

import re
import sys
from socket import socket, AF_INET, SOCK_STREAM, getfqdn, gethostname
from email import Email
from message import Message
from parse import RemainingString
from exceptions import *

def SMTP_server_engine():
    """Engine for a SMTP mail server process.
    This engine is primarily implemented as a state machine with five states: STATE_0, STATE_1, STATE_2,
    STATE_3, and STATE_4. In STATE_0, the state machine expects a 'HELO' message (and continues to STATE_1
    on receipt of one). In STATE_1, the state machine expects a 'MAIL FROM' command message (and continues
    to STATE_2 on receipt of one). In STATE_2, the state machine expects a 'RCPT TO' command (and continues
    to STATE_3 in receipt of one). In STATE_3, the state machine expects either a 'RCPT TO' command (remains
    at STATE_3) or a 'DATA' command (continues to STATE_4). In STATE_4, the state machine expects either a
    message data line (remains at STATE_4) or an end-of-message-data sequence (continues to STATE_1). In
    addition, the state machine will accept and handle a valid 'QUIT' command in any one of its states.
    """

    ########################## States ##########################
    # The states in which the state machine expects:
    STATE_0 = 0 # a 'HELO' message (continues to STATE_1)
    STATE_1 = 1 # a 'MAIL FROM' command (continues to STATE_2)
    STATE_2 = 2 # a 'RCPT TO' command (continues to STATE_3)
    STATE_3 = 3 # either a 'RCPT TO' command (remains at STATE_3) or a 'DATA' command (continues to STATE_4)
    STATE_4 = 4 # either a message data line (remains at STATE_4) or an end-of-message-data sequence (continues to STATE_1)
    # NOTE: a 'QUIT' command is valid in any state
    #############################################################

    ########################## Message Strings & More ##########################
    # "220 <server hostname + domain name>" greeting message
    GREETING_220_MSG = ("220 " + getfqdn() + "\n").encode()
    # "221 <server hostname> closing connection" message
    CLOS_CON_221_MSG = ("221 " + gethostname() + " closing connection\n").encode()
    # "250 Hello <client domain name> pleased to meet you" acknowledgement messsage start and end (unencoded)
    HELO_ACK_250_MSG_START_UNENC, HELO_ACK_250_MSG_END_UNENC = "250 Hello ", " pleased to meet you\n"
    # "250 OK" message
    OK_250_MSG = ("250 OK\n").encode()
    # "354 Start mail input; end with <CRLF>.<CRLF>\n" message
    START_MAIL_354_MSG = ("354 Start mail input; end with <CRLF>.<CRLF>\n").encode()
    # "500 Syntax error: command unrecognized" error message
    SYN_COM_UNREC_ERR_500_MSG = ("500 Syntax error: command unrecognized\n").encode()
    # "501 Syntax error in parametrs or arguments" error message
    SYN_PARAM_ARG_ERR_501_MSG = ("501 Syntax error in parameters or arguments\n").encode()
    # "503 Bad sequence of commands" error message
    BAD_SEQ_COM_ERR_503_MSG  = ("503 Bad sequence of commands\n").encode()
    # End-of-message-data sequence - <CRLF>.<CRLF>
    # (used at / checked against the beginning of a new line)
    EOMD_SEQ = ".\n"
    ###############################################################################

    ############################## Main Server Mechanism ##############################

    # Create welcoming socket, bind command-line-argument-specified
    # port number, and initiate TCP connection request listening process
    try:
        welcome_port_number = int(sys.argv[1])
        welcoming_socket = socket(AF_INET, SOCK_STREAM)
        welcoming_socket.bind(('', welcome_port_number))
        welcoming_socket.listen(1)
    # Alert and terminate on error
    except Exception as e:
        print("Error initializing welcoming socket. "
                "Terminating program. Exception encountered: "
                + str(e))
        return

    while True:

        # Await connection at welcoming socket and create connection socket on connection
        try:
            connection_socket, client_address = welcoming_socket.accept()
        # Alert and await new connection on error
        except Exception as e:
            print("Error establishing connection with client. "
                    "Awaiting new connection. "
                    "Exception encountered: "
                    + str(e))
            continue

        # Send 220 "greeting" message
        try:
            send_msg(GREETING_220_MSG, connection_socket)
        # Await new connection on error
        # (having already closed connection and alerted user)
        except SocketError:
            continue

        # Initiate state machine, receiving and sending messages through connection socket:

        state = STATE_0
        current_email = Email()
        sock_stream_rem_string = RemainingString("")

        while True:

            try:

                # If necessary, draw from socket stream to obtain a complete client SMTP message
                if not sock_stream_rem_string.contains_complete_msg():
                    sock_stream_rem_string.append(recv_msg(connection_socket, state).decode())
                    continue
                else:
                    msg_str = sock_stream_rem_string.consume_and_get_msg()

                # Gather email data from client message, store email data when applicable,
                # update state machine state as appropriate, and send relevant response
                # messages (all based on the current state of the state machine)
                if state == STATE_0:

                    msg = Message(msg_str)

                    if not msg.is_recognized():
                        send_msg(SYN_COM_UNREC_ERR_500_MSG, connection_socket)
                        continue
                    elif not msg.is_helo_msg():
                        if msg.is_quit_cmd():
                            if msg.has_valid_params_args():
                                send_msg(CLOS_CON_221_MSG, connection_socket)
                                connection_socket.close()
                                break
                            else:
                                send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                                continue
                        else:
                            send_msg(BAD_SEQ_COM_ERR_503_MSG, connection_socket)
                            continue
                    elif not msg.has_valid_params_args():
                        send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                        continue
                    else:
                        send_msg((HELO_ACK_250_MSG_START_UNENC
                            + client_address[0]
                            + HELO_ACK_250_MSG_END_UNENC).encode(),
                            connection_socket)
                        state = STATE_1
                        continue

                elif state == STATE_1:

                    msg = Message(msg_str)

                    if not msg.is_recognized():
                        send_msg(SYN_COM_UNREC_ERR_500_MSG, connection_socket)
                        continue
                    elif not msg.is_mail_from_cmd():
                        if msg.is_quit_cmd():
                            if msg.has_valid_params_args():
                                send_msg(CLOS_CON_221_MSG, connection_socket)
                                connection_socket.close()
                                break
                            else:
                                send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                                continue
                        else:
                            send_msg(BAD_SEQ_COM_ERR_503_MSG, connection_socket)
                            continue
                    elif not msg.has_valid_params_args():
                        send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                        continue
                    else:
                        current_email.set_reverse_path(re.search("<.*>", msg_str)[0])
                        send_msg(OK_250_MSG, connection_socket)
                        state = STATE_2
                        continue

                elif state == STATE_2:

                    msg = Message(msg_str)

                    if not msg.is_recognized():
                        send_msg(SYN_COM_UNREC_ERR_500_MSG, connection_socket)
                        continue
                    elif not msg.is_rcpt_to_cmd():
                        if msg.is_quit_cmd():
                            if msg.has_valid_params_args():
                                send_msg(CLOS_CON_221_MSG, connection_socket)
                                connection_socket.close()
                                break
                            else:
                                send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                                continue
                        else:
                            send_msg(BAD_SEQ_COM_ERR_503_MSG, connection_socket)
                            continue
                    elif not msg.has_valid_params_args():
                        send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                        continue
                    else:
                        current_email.add_forward_path(re.search("<.*>", msg_str)[0])
                        send_msg(OK_250_MSG, connection_socket)
                        state = STATE_3
                        continue

                elif state == STATE_3:

                    msg = Message(msg_str)

                    if not msg.is_recognized():
                        send_msg(SYN_COM_UNREC_ERR_500_MSG, connection_socket)
                        continue
                    elif msg.is_quit_cmd():
                        if msg.has_valid_params_args():
                            send_msg(CLOS_CON_221_MSG, connection_socket)
                            connection_socket.close()
                            break
                        else:
                            send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                            continue
                    elif msg.is_rcpt_to_cmd():
                        if not msg.has_valid_params_args():
                            send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                            continue
                        else:
                            current_email.add_forward_path(re.search("<.*>", msg_str)[0])
                            send_msg(OK_250_MSG, connection_socket)
                            continue
                    elif msg.is_data_cmd():
                        if not msg.has_valid_params_args():
                            send_msg(SYN_PARAM_ARG_ERR_501_MSG, connection_socket)
                            continue
                        else:
                            send_msg(START_MAIL_354_MSG, connection_socket)
                            state = STATE_4
                            continue
                    else:
                        send_msg(BAD_SEQ_COM_ERR_503_MSG, connection_socket)
                        continue

                elif state == STATE_4:

                    if msg_str == EOMD_SEQ:
                        for ff_name in current_email.domain_specific_forward_file_names():
                            with open("forward/" + ff_name, 'a+') as forward_file:
                                for line in current_email.forward_file_ready_text_lines():
                                    forward_file.write(line)
                        send_msg(OK_250_MSG, connection_socket)
                        current_email = Email()
                        state = STATE_1
                        continue
                    else:
                        current_email.add_message_line(msg_str)
                        continue

            # If a SocketError is encountered, await new connection and reset state machine
            # (having already closed connection and alerted user)
            except SocketError:
                break

  ###################################################################################

############################## Helper procedures/functions ##############################

def send_msg(msg, connection_socket):
    """Given an encoded message and a connection socket, sends the message into the socket.
    If an exception is raised as a result of the sending process, this procedure closes
    the connection socket, prints a descriptive 1-line error message, and raises a
    SocketError."""
    try:
        connection_socket.send(msg)
    except Exception:
        connection_socket.close()
        print("Error sending message. Closing connection and awating new connection. "
                "Message intended to be sent: " + msg.decode().rstrip("\n"))
        raise SocketError()

def recv_msg(connection_socket, state):
    """Given a connection socket and the current state of the server state machine,
    receives an enconded message from the socket and returns it. If an exception is
    raised as a result of the receiving process, this function closes the connection
    socket, prints a descriptive 1-line error message, and raises a SocketError."""
    try:
        msg = connection_socket.recv(1024)
    except Exception as e:
        connection_socket.close()
        print("Error receiving client message in STATE_"
                + state + " at " + time.asctime()
                + ". Exception encountered: "
                + str(e))
        raise SocketError()
    return msg

##########################################################################################

if __name__ == "__main__":
    SMTP_server_engine()
