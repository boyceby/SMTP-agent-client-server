"""
Message
"""

class Message:
    """Class defining an object representative of a single application-layer SMTP message."""

    # Possible message types
    _UNRECOGNIZED = 0
    _HELO = 1
    _MAIL_FROM = 2
    _RCPT_TO = 3
    _DATA = 4
    _QUIT = 5

    def __init__(self, ms):

        # Attempt init as HELO message
        try:
            parse_helo_msg(RemainingString(ms))
        except MessageParsingError:
            pass
        except ParameterArgumentParsingError:
            self._msg_type = Message._HELO
            self._param_arg_error = True
            return
        else:
            self._msg_type = Message._HELO
            self._param_arg_error = False
            return

        # Attempt init as MAIL_FROM command
        try:
            parse_mail_from_cmd(RemainingString(ms))
        except MessageParsingError:
            pass
        except ParameterArgumentParsingError:
            self._msg_type = Message._MAIL_FROM
            self._param_arg_error = True
            return
        else:
            self._msg_type = Message._MAIL_FROM
            self._param_arg_error = False
            return

        # Attempt init as RCPT_TO command
        try:
            parse_rcpt_to_cmd(RemainingString(ms))
        except MessageParsingError:
            pass
        except ParameterArgumentParsingError:
            self._msg_type = Message._RCPT_TO
            self._param_arg_error = True
            return
        else:
            self._msg_type = Message._RCPT_TO
            self._param_arg_error = False
            return

        # Attempt init as DATA command
        try:
            parse_data_cmd(RemainingString(ms))
        except MessageParsingError:
            pass
        except ParameterArgumentParsingError:
            self._msg_type = Message._DATA
            self._param_arg_error = True
            return
        else:
            self._msg_type = Message._DATA
            self._param_arg_error = False
            return

        # Attempt init as QUIT command
        try:
            parse_quit_cmd(RemainingString(ms))
        except MessageParsingError:
            pass
        except ParameterArgumentParsingError:
            self._msg_type = Message._QUIT
            self._param_arg_error = True
            return
        else:
            self._msg_type = Message._QUIT
            self._param_arg_error = False
            return

        # If not a MAIL_FROM, RCPT_TO, DATA, or QUIT command, init as UNRECOGNIZED
        self._msg_type = Message._UNRECOGNIZED
        self._param_arg_error = False # If an unrecognized command, defaults to no ParameterArgumentParsingError

    def is_recognized(self):
        return self._msg_type != Message._UNRECOGNIZED

    def is_helo_msg(self):
        return self._msg_type == Message._HELO

    def is_mail_from_cmd(self):
        return self._msg_type == Message._MAIL_FROM

    def is_rcpt_to_cmd(self):
        return self._msg_type == Message._RCPT_TO

    def is_data_cmd(self):
        return self._msg_type == Message._DATA

    def is_quit_cmd(self):
        return self._msg_type == Message._QUIT

    def has_valid_params_args(self):
        return not self._param_arg_error
