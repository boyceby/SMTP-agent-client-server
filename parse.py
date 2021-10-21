
"""
Parse

This module provides the parsing mechanisms that both agent_client and server employ
to parse SMTP messages, user input, and more. The module includes a number of
production-rule-associated parsing functions for the following grammars:

    SMTP Client Messages:
                 <helo-msg> ::= "HELO" <whitespace> <domain> <nullspace> <CRLF>
            <mail-from-cmd> ::= “MAIL” <whitespace> “FROM:” <nullspace> <reverse-path>
                                <nullspace> <CRLF>
              <rcpt-to-cmd> ::= “RCPT” <whitespace> “TO:” <nullspace> <forward-path>
                                <nullspace> <CRLF>
                 <data-cmd> ::= “DATA” <nullspace> <CRLF>
                 <quit-cmd> ::= “QUIT” <nullspace> <CRLF>
               <whitespace> ::= <SP> | <SP> <whitespace>
                       <SP> ::= the space or tab character
                <nullspace> ::= <null> | <whitespace>
                     <null> ::= no character
             <reverse-path> ::= <path>
             <forward-path> ::= <path>
                     <path> ::= "<" <mailbox> ">"
                  <mailbox> ::= <local-part> "@" <domain>
               <local-part> ::= <string>
                   <string> ::= <char> | <char> <string>
                     <char> ::= any one of the printable ASCII characters, but not any
                                of <special> or <SP>
                   <domain> ::= <element> | <element> "." <domain>
                  <element> ::= <letter> | <name>
                     <name> ::= <letter> <let-dig-str>
                   <letter> ::= any one of the 52 alphabetic characters A through Z
                                in upper case and a through z in lower case
              <let-dig-str> ::= <let-dig> | <let-dig> <let-dig-str>
                  <let-dig> ::= <letter> | <digit>
                    <digit> ::= any one of the ten digits 0 through 9
                     <CRLF> ::= the newline character
                  <special> ::= "<" | ">" | "(" | ")" | "[" | "]" | "\" | "."
                                | "," | ";" | ":" | "@" | '"'
    SMTP Server Response Messages:
             <response-code> ::= <resp-number> <whitespace> <arbitrary-text> <CRLF>
               <resp-number> ::= "250" | "354" | "500" | "501"
                <whitespace> ::= <SP> | <SP> <whitespace>
                        <SP> ::= the space or tab character
            <arbitrary-text> ::= any sequence of one or more printable characters
                      <CRLF> ::= the newline character
    Miscellaneous:
        <comma-sep-mailboxes> ::= <mailbox> | <mailbox> "," <nullspace> <comma-sep-mailboxes>
        
NOTE: Each parsing function requires a RemainingString object, which is meant to contain the 
unparsed portion of an original string.
"""

class RemainingString:
    """Wrapper class for the unparsed portion of a string."""

    def __init__(self, initial_string):
        self._remaining_string = initial_string

    def get(self):
        return self._remaining_string

    def set(self, remaining_string):
        self._remaining_string = remaining_string

    def is_empty(self):
        return not bool(self._remaining_string)

    def get_first_char(self):
        if self.is_empty():
            return ""
        return self._remaining_string[0]

    def has_further_chars(self):
        return True if self._remaining_string else False
 

def parse_helo_msg(rs):
    """
    <helo-msg> ::= "HELO" <whitespace> <arbitrary-text> <nullspace> <CRLF>
    """
    try:
        consume("HELO", rs)
    except ConsumptionError:
        raise MessageParsingError("helo-msg")
    # Here, one-character-look-ahead is used to discern what type of ParsingError should be raised if one occurs:
    #   In the case that no character, a space character, a tab character, or a newline character
    #   follows, a "HELO" message has been recognized and a ParameterArgumentParsingError should
    #   be raised on a subsequent parsing error. Otherwise, a "HELO" message has not been recognized,
    #   and a MessageParsingError will be raised.
    if (rs.is_empty() or rs.get_first_char() == " "
            or rs.get_first_char() == "\t" or rs.get_first_char() == "\n"):
        try:
            parse_whitespace(rs)
            parse_arbitrary_text(rs)
            parse_nullspace(rs)
            parse_CRLF(rs)
        except ParsingError as e:
            raise ParameterArgumentParsingError(str(e))
    else:
        raise MessageParsingError("helo-msg")


def parse_mail_from_cmd(rs):
    """
    <mail-from-cmd> ::= “MAIL” <whitespace> “FROM:” <nullspace> <reverse-path>
                         <nullspace> <CRLF>
    """
    try:
        consume("MAIL", rs)
        parse_whitespace(rs)
        consume("FROM:", rs)
    except ConsumptionError:
        raise MessageParsingError("mail-from-cmd")
    except ParsingError as e:
        raise MessageParsingError(str(e))
    try:
        parse_nullspace(rs)
        parse_reverse_path(rs)
        parse_nullspace(rs)
        parse_CRLF(rs)
    except ParsingError as e:
        raise ParameterArgumentParsingError(str(e))


def parse_rcpt_to_cmd(rs):
    """
    <rcpt-to-cmd> ::= “RCPT” <whitespace> “TO:” <nullspace> <forward-path>
                      <nullspace> <CRLF>
    """
    try:
        consume("RCPT", rs)
        parse_whitespace(rs)
        consume("TO:", rs)
    except ConsumptionError:
        raise MessageParsingError("rcpt-to-cmd")
    except ParsingError as e:
        raise MessageParsingError(str(e))
    try:
        parse_nullspace(rs)
        parse_forward_path(rs)
        parse_nullspace(rs)
        parse_CRLF(rs)
    except ParsingError as e:
        raise ParameterArgumentParsingError(str(e))


def parse_data_cmd(rs):
    """
    <data-cmd> ::= “DATA” <nullspace> <CRLF>
    """
    try:
        consume("DATA", rs)
    except ConsumptionError:
        raise MessageParsingError("data-cmd")
    # Here, one-character-look-ahead is used to discern what type of ParsingError should be raised if one occurs:
    #   In the case that no character, a space character, a tab character, or a newline character
    #   follows, a "DATA" command message has been recognized and a ParameterArgumentParsingError
    #   should be raised on a subsequent parsing error. Otherwise, a "DATA" command message has not
    #   been recognized, and a MessageParsingError will be raised.
    if (rs.is_empty() or rs.get_first_char() == " "
            or rs.get_first_char() == "\t" or rs.get_first_char() == "\n"):
        try:
            parse_nullspace(rs)
            parse_CRLF(rs)
        except ParsingError as e:
            raise ParameterArgumentParsingError(str(e))
    else:
        raise MessageParsingError("data-cmd")

        
def parse_quit_cmd(rs):
    """
    <quit-cmd> ::= “QUIT” <nullspace> <CRLF>
    """
    try:
        consume("QUIT", rs)
    except ConsumptionError:
        raise MessageParsingError("quit-cmd")
    # Here, one-character-look-ahead is used to discern what type of ParsingError should be raised if one occurs:
    #   In the case that no character, a space character, a tab character, or a newline character
    #   follows, a "QUIT" command message has been recognized and a ParameterArgumentParsingError
    #   should be raised on a subsequent parsing error. Otherwise, a "QUIT" command message has not
    #   been recognized, and a MessageParsingError will be raised.
    if (rs.is_empty() or rs.get_first_char() == " "
            or rs.get_first_char() == "\t" or rs.get_first_char() == "\n"):
        try:
            parse_nullspace(rs)
            parse_CRLF(rs)
        except ParsingError as e:
            raise ParameterArgumentParsingError(str(e))
    else:
        raise MessageParsingError("quit-cmd")


def parse_whitespace(rs):
    """
    <whitespace> ::= <SP> | <SP> <whitespace>
            <SP> ::= the space or tab character
    """
    try:
        consume("[ \t]+", rs)
    except ConsumptionError:
        raise ParsingError("whitespace")


def parse_nullspace(rs):
    """
     <nullspace> ::= <null> | <whitespace>
          <null> ::= no character
    <whitespace> ::= <SP> | <SP> <whitespace>
            <SP> ::= the space or tab character
    """
    try:
        consume("[ \t]*", rs)
    except ConsumptionError:
        raise ParsingError("nullspace")


def parse_reverse_path(rs):
    """
    <reverse-path> ::= <path>
    """
    parse_path(rs)


def parse_forward_path(rs):
    """
    <forward-path> ::= <path>
    """
    parse_path(rs)


def parse_CRLF(rs):
    """
    <CRLF> ::= the newline character
    """
    try:
        consume("\n", rs)
    except ConsumptionError:
        raise ParsingError("CRLF")


def parse_path(rs):
    """
    <path> ::= "<" <mailbox> ">"
    """
    try:
        consume("<", rs)
    except ConsumptionError:
        raise ParsingError("path")
    parse_mailbox(rs)
    try:
        consume(">", rs)
    except ConsumptionError:
        raise ParsingError("path")


def parse_mailbox(rs):
    """
    <mailbox> ::= <local-part> "@" <domain>
    """
    parse_local_part(rs)
    try:
        consume("@", rs)
    except ConsumptionError:
        raise ParsingError("mailbox")
    parse_domain(rs)


def parse_local_part(rs):
    """
    <local-part> ::= <string>
    """
    parse_string(rs)


def parse_domain(rs):
    """
         <domain> ::= <element> | <element> "." <domain>
        <element> ::= <letter> | <name>
           <name> ::= <letter> <let-dig-str>
         <letter> ::= any one of the 52 alphabetic characters A through Z
                      in upper case and a through z in lower case
    <let-dig-str> ::= <let-dig> | <let-dig> <let-dig-str>
        <let-dig> ::= <letter> | <digit>
          <digit> ::= any one of the ten digits 0 through 9
    """
    try:
        consume("([A-Za-z][A-Za-z0-9]*)(\\.([A-Za-z][A-Za-z0-9]*))*", rs)
    except ConsumptionError:
        raise ParsingError("domain")


def parse_string(rs):
    """
     <string> ::= <char> | <char> <string>
       <char> ::= any one of the printable ASCII characters, but not any
                 of <special> or <SP>
    <special> ::= "<" | ">" | "(" | ")" | "[" | "]" | "\" | "."
                  | "," | ";" | ":" | "@" | '"'
         <SP> ::= the space or tab character
    """
    try:
        consume("[^<>()[\\]\\\\.,;:@\" \t\n]+", rs)
    except ConsumptionError:
        raise ParsingError("string")

     
def parse_220_resp_code_msg(rs):
    """
    <220-resp-code-msg> ::= "220" <whitespace> <arbitrary-text> <CRLF>
    """
    try:
        consume("220", rs)
    except ConsumptionError:
        raise ParsingError("server-greeting")
    parse_whitespace(rs)
    parse_arbitrary_text(rs)
    parse_CRLF(rs)


def parse_221_resp_code_msg(rs):
    """
    <221-resp-code-msg> ::= "221" <whitespace> <arbitrary-text> <CRLF>
    """
    try:
        consume("221", rs)
    except ConsumptionError:
        raise ParsingError("250-resp-code-msg")
    parse_whitespace(rs)
    parse_arbitrary_text(rs)
    parse_CRLF(rs)

def parse_250_resp_code_msg(rs):
    """
    <250-resp-code-msg> ::= "250" <whitespace> <arbitrary-text> <CRLF>
    """
    try:
        consume("250", rs)
    except ConsumptionError:
        raise ParsingError("250-resp-code-msg")
    parse_whitespace(rs)
    parse_arbitrary_text(rs)
    parse_CRLF(rs)


def parse_354_resp_code_msg(rs):
    """
    <354-resp-code-msg> ::= "354" <whitespace> <arbitrary-text> <CRLF>
    """
    try:
        consume("354", rs)
    except ConsumptionError:
        raise ParsingError("250-resp-code-msg")
    parse_whitespace(rs)
    parse_arbitrary_text(rs)
    parse_CRLF(rs)
    

def parse_arbitrary_text(rs):
    """
    <arbitrary-text> ::= any sequence of one or more printable characters
    """
    try:
        consume("[ -~]+", rs)
    except ConsumptionError:
        raise ParsingError("arbitrary-text")        
        
        
def parse_comma_sep_mailboxes(rs):
    """
    <comma-sep-mailboxes> ::= <mailbox> | <mailbox> "," <nullspace> <comma-sep-mailboxes>
    """
    while True:
        parse_mailbox(rs)
        if rs.is_empty():
            break
        try:
            consume(",", rs)
        except ConsumptionError:
            raise ParsingError("comma-sep-mailboxes")
        parse_nullspace(rs)

        
def consume(regexp, rs):
    """Attempts to match the provided regexp pattern with the beginning of the remaining message string.
        If there is a match, the matching portion of the remaining message string is removed (consumed).
        Otherwise, a ConsumptionError is raised."""
    matched_string_obj = re.match(regexp, rs.get())
    if matched_string_obj is None:
        raise ConsumptionError()
    rs.set(rs.get()[len(matched_string_obj[0]):])
