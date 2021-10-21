"""
Email
"""

import re
import base64
import mimetypes
from socket import socket, AF_INET, SOCK_STREAM, getfqdn, gethostname

class Email:
    """A class used by agent_client and server to temporarily store and manipulate email data as an email object."""

    # String used at the beginning of a new line to insert or
    # check for the end-of-message-data sequence <CRLF>.<CRLF>
    EOMD_SEQ = ".\n"

    def __init__(self):
        self._reverse_path = ""
        self._forward_paths = []
        self._subject = ""
        self._message_lines = []
        self._attachment_filename = ""

    def set_reverse_path(self, reverse_path):
        self._reverse_path = reverse_path

    def add_forward_path(self, forward_path):
        self._forward_paths.append(forward_path)

    def set_forward_paths(self, forward_paths):
        self._forward_paths = forward_paths

    def set_subject(self, subject):
        self._subject = subject

    def add_message_line(self, message_line):
        self._message_lines.append(message_line)

    def set_attachment_filename(self, attachment_filename):
        self._attachment_filename = attachment_filename

    def domain_specific_forward_file_names(self):
        """Returns as a set the set of domain names found amongst the forward paths that are associated
            with the email at hand (for purposes of domain-specific forward file creation)."""
        return {re.search("@.*>", forward_path)[0][1:-1] for forward_path in self._forward_paths}

    def forward_file_ready_text_lines(self):
        '''Generator generating line strings that, when iterated through, can be used collectively
            to textually represent the details of the email in the format:
                From: <reverse-path>
                To: <forward-path-1>
                          .
                          .
                          .
                To: <forward-path-n>
                These are two sample message data lines included
                for illustrative purposes.'''
        for message_line in self._message_lines:
            yield message_line

    def fill(self):
        """Method for soliciting, obtaining, and storing email data from a command-line user."""
        self._fill_reverse_path()
        self._fill_forward_paths()
        self._fill_subject()
        self._fill_message_lines()
        self._fill_attachment_filename()

    def _fill_reverse_path(self):
        while True:
            try:
                mailbox_input_string = input("From:\n")
            except EOFError:
                raise EarlyTerminationError()
            else:
                try:
                    mailbox_input_string_rem_string = RemainingString(mailbox_input_string)
                    parse_mailbox(mailbox_input_string_rem_string)
                except ParsingError as e:
                    print("Invalid <mailbox> provided for reverse-path: error parsing for <" 
                          + str(e) + "> production rule.")
                else:
                    if mailbox_input_string_rem_string.has_further_chars():
                        print("Invalid <mailbox> provided for reverse-path: error parsing for <" 
                              "mailbox> production rule.")
                    else:
                        self.set_reverse_path("<" + mailbox_input_string + ">")
                        break

    def _fill_forward_paths(self):
        while True:
            try:
                mailboxes_input_string = input("To:\n")
            except EOFError:
                raise EarlyTerminationError()
            else:
                try:
                    parse_comma_sep_mailboxes(RemainingString(mailboxes_input_string))
                except ParsingError as e:
                    print("Invalid <mailbox> sequence for forward-paths: error parsing for <" 
                          + str(e) + "> production rule.")
                else:
                    forward_paths = ["<" + mailbox.strip() + ">" for mailbox in mailboxes_input_string.split(",")]
                    self.set_forward_paths(forward_paths)
                    break

    def _fill_subject(self):
        try:
            subject = input("Subject:\n")
        except EOFError:
            raise EarlyTerminationError()
        else:
            self.set_subject(subject)

    def _fill_message_lines(self):
        print("Message:")
        while True:
            try:
                line = input() + "\n"
            except EOFError:
                raise EarlyTerminationError()
            else:
                if line == Email.EOMD_SEQ:
                    break
                else:
                    self.add_message_line(line)

    def _fill_attachment_filename(self):
        print("Attachment:")
        try:
            # Assumes a valid filename
            filename = input()
        except EOFError:
            raise EarlyTerminationError()
        else:
            self.set_attachment_filename(filename)

    def send(self, server_hostname, welc_sock_port_num):
        """Method for sending a complete email to the address specified by the provided (string) server
        hostname and (integer) welcoming socket port number using SMTP."""

        # Create client socket and initiate connection with specified server
        try:
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((server_hostname, welc_sock_port_num))
        # Raise SocketError exception on error
        except Exception as e:
            print("Error creating client socket and/or initiating connection. Exception raised: " + str(e) + "\n")
            raise SocketError()

        # Receive and validate server's 220 response code greeting message
        self._receive_and_validate("220", client_socket, None, None)

        # Send "HELO" message
        sent_msg = self._send_msg(self._get_helo_msg(), client_socket)
        # Receive and validate server's 250 response code acknowledgement message
        self._receive_and_validate("250", client_socket, "HELO", sent_msg)

        # Send "MAIL FROM" command message
        sent_msg = self._send_msg(self._get_mail_from_cmd(), client_socket)
        # Receive and validate server's 250 response code message
        self._receive_and_validate("250", client_socket, "MAIL_FROM", sent_msg)

        # Send "RCPT TO" command messages, receive and validate server's 250 response code messagess
        for rcpt_to_cmd in self._get_rcpt_to_cmds():
            # Send "RCPT TO" command message
            sent_msg = self._send_msg(rcpt_to_cmd, client_socket)
            # Receive an validate server's 250 response code message
            self._receive_and_validate("250", client_socket, "RCPT_TO", sent_msg)

        # Send "DATA" command message
        sent_msg = self._send_msg(self._get_data_cmd(), client_socket)
        # Receive and validate server's 354 response code message
        self._receive_and_validate("354", client_socket, "DATA", sent_msg)

        # Send SMTP message data lines followed by end-of-message-data sequence
        for data_line in self._get_SMTP_MIME_message_data_lines():
            self._send_msg(data_line, client_socket)
        self._send_msg(self._get_eomd_seq(), client_socket)
        # Receive and validate server's 250 response code message
        self._receive_and_validate("250", client_socket, "MESSAGE_DATA", None)

        # Send "QUIT" command message
        sent_msg = self._send_msg(self._get_quit_cmd(), client_socket)
        # Receive and validate server's 221 response code closing message
        self._receive_and_validate("221", client_socket, "QUIT", sent_msg)


    def _send_msg(self, msg, client_socket):
        """Given an encoded message, sends this message into the provided client socket and returns it.
        Raises a SocketError if any exceptions are encountered as a result of the sending process. Before
        raising any exceptions, this procedure will close the socket's connection and print a descriptive
        1-line error message."""
        try:
            client_socket.send(msg)
        except Exception:
            client_socket.close()
            print("Error sending the following message: " + msg.decode().rstrip("\n") + "\n")
            raise SocketError()
        return msg

    def _receive_and_validate(self, expected_msg_type, client_socket, sent_msg_type, sent_msg):
        """Given a message type, a client socket, and the prior (encoded) message sent into the client
        socket (along with its type), recieves a message from the socket and validates that that message
        conforms to the SMTP protocol grammar production rule associated with the provided expected message
        type. Raises a SMTPBreakOfProtocolError if this is not found to be the case. Raises a SocketError in
        the case that an exception occurs while trying to receive from the client socket. Before raising
        any exceptions, this procedure will close the socket's connection and print a descriptive 1-line
        error message. The message types should be provided as strings based on the following tables:
            Expected Message Types:
                220 response code greeting message -> "220"
                221 response code closing message -> "221"
                250 response code message -> "250"
                354 response code message -> "354"
            Sent Message Types:
                HELO message -> "HELO"
                MAIL FROM command message -> "MAIL_FROM"
                RCPT TO command message -> "RCPT_TO"
                DATA command message -> "DATA"
                Message data line messages -> "MESSAGE_DATA"
                QUIT command message -> "QUIT"
        If no prior message was sent, provide None for sent_msg_type and sent_msg. In the case that
        the sent message type is of type "MESSAGE_DATA", None should be provided for sent_msg.
        """

        # Receive message:
        try:
            msg_str = client_socket.recv(1024).decode()
        except Exception:
            # Determine appropriate output on error
            if (sent_msg_type == "HELO"
                    or sent_msg_type == "MAIL_FROM"
                    or sent_msg_type == "RCTP_TO"
                    or sent_msg_type == "DATA"
                    or sent_msg_type == "QUIT"):
                rec_error_output = ("Error receiving server response. Sent: "
                        + sent_msg.decode().rstrip("\n"))
            elif sent_msg_type == "MESSAGE_DATA":
                rec_error_output = ("Error receiving server response after "
                        "sending message data.")
            elif sent_msg_type == None:
                rec_error_output = "Error receiving server greeting."
            # Close connection, alert, and raise exception
            client_socket.close()
            print(rec_error_output)
            raise SocketError()

        # Validate that message is of expected type:
        try:
            # Determine appropriate parsing procedure
            if expected_msg_type == "220":
                parsing_procedure = parse_220_resp_code_msg
            elif expected_msg_type == "221":
                parsing_procedure = parse_221_resp_code_msg
            elif expected_msg_type == "250":
                parsing_procedure = parse_250_resp_code_msg
            elif expected_msg_type == "354":
                parsing_procedure = parse_354_resp_code_msg
            # Parse received message string
            parsing_procedure(RemainingString(msg_str))
        except ParsingError:
            # Determine appropriate output on error
            if (sent_msg_type == "HELO"
                    or sent_msg_type == "MAIL_FROM"
                    or sent_msg_type == "RCPT_TO"
                    or sent_msg_type == "DATA"
                    or sent_msg_type == "QUIT"):
                val_error_output = ("unexpected server response. Sent "
                        + sent_msg.decode().rstrip("\n") + ". Received: "
                        + msg_str.rstrip("\n"))
            elif sent_msg_type == "MESSAGE_DATA":
                val_error_output = ("Unexpected server response. Sent message data. "
                "Received: " + msg_str.rstrip("\n"))
            elif sent_msg_type == None:
                val_error_output = ("Unexpected server greeting. Received: "
                    + msg_str.rstrip("\n"))
            # Close connection, alert, and raise exception
            client_socket.close()
            print(val_error_output)
            raise SMTPBreakOfProtocolError()

    def _get_helo_msg(self):
        return ("HELO " + getfqdn() + "\n").encode()

    def _get_mail_from_cmd(self):
        return ("MAIL FROM: " + self._reverse_path + "\n").encode()

    def _get_rcpt_to_cmds(self):
        for forward_path in self._forward_paths:
            yield ("RCPT TO: " + forward_path + "\n").encode()

    def _get_data_cmd(self):
        return ("DATA\n").encode()

    def _get_SMTP_message_data_lines(self):
        """Generator generating line strings that, when iterated through, can be used collectively
            to textually represent the data of the email in the format:
                From: <reverse-path>
                To: <forward-path-1>, <forward-path-2>, ..., <forward-path-n>
                Subject: Arbitrary Subject Text
                These are three sample SMTP message data body lines included
                for illustrative purposes. Note the blank line preceding
                these lines."""
        yield ("From: " + self._reverse_path + "\n").encode()
        yield ("To: " + ", ".join(self._forward_paths) + "\n").encode()
        yield ("Subject: " + self._subject + "\n").encode()
        yield ("\n").encode()
        for message_line in self._message_lines:
            yield (message_line).encode()

    def _get_SMTP_MIME_message_data_lines(self):
        """Generator generating line strings that, when iterated through, can be used collectively
            to obtain the ordered set of multipart MIME-encoded data lines representing the email
            at hand. The lines generated will be in the format:
                From: <reverse-path>
                To: <forward-path-1>, <forward-path-2>, ..., <forward-path-n>
                Subject: Arbitrary Subject Text
                MIME-Version: 1.0
                Content-Type: multipart/mixed; boundary=98766789
                --98766789
                Content-Transfer-Encoding: quoted-printable
                Content-Type: text/plain
                These are two sample SMTP message data body lines included
                for illustrative purposes.
                --98766789
                Content-Transfer-Encoding: base64
                Content-Type: *DEPENDENT ON TYPE OF ATTACHMENT*
                base64 encoding of attachment ---------------
                ---------------------------------------------
                ---------------------------------------------
                ---------------------------------------------
                ---------------------------------------------
                --------------- base64 encoding of attachment
                --98766789--
                
        """
        yield ("From: " + self._reverse_path + "\n").encode()
        yield ("To: " + ", ".join(self._forward_paths) + "\n").encode()
        yield ("Subject: " + self._subject + "\n").encode()
        yield ("MIME-Version: 1.0\n").encode()
        yield ("Content-Type: multipart/mixed; boundary=98766789\n").encode()
        yield ("\n").encode()
        yield ("--98766789\n").encode()
        yield ("Content-Transfer-Encoding: quoted-printable\n").encode()
        yield ("Content-Type: text/plain\n").encode()
        yield ("\n").encode()
        for message_line in self._message_lines:
            yield (message_line).encode()
        yield ("--98766789\n").encode()
        yield ("Content-Transfer-Encoding: base64\n").encode()
        yield ("Content-Type: " + mimetypes.guess_type(self._attachment_filename)[0]
                + "\n").encode()
        yield ("\n").encode()
        with open(self._attachment_filename, 'rb') as attachment:
            base_64_encoded_attachment = base64.encodebytes(attachment.read())
        yield base_64_encoded_attachment
        yield ("--98766789--\n").encode()

    def _get_eomd_seq(self):
        return (Email.EOMD_SEQ).encode()

    def _get_quit_cmd(self):
        return ("QUIT\n").encode()
