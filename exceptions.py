"""
Exceptions
"""
 
class ConsumptionError(Exception):
    """Exception raised when 'consume' fails to match a given regexp pattern with the beginning of
        the remaining string, (and therefore also fails to consume it)."""
    pass

class ParsingError(Exception):
    """Exception raised when an invalid character sequence is encountered whilst parsing the remaining
        string under a given production rule. Passes along as a message the name of the
        non-terminal associated with the production rule parsing function at which the
        ParsingError ocurred."""
    pass

class MessageParsingError(ParsingError):
    """Exception raised when a ParsingError results in a message for which a message string is being
        parsed (i.e. messages of type "HELO", "MAIL FROM", "RCPT TO", "DATA", or "QUIT") failing to
        be recognized."""
    pass

class ParameterArgumentParsingError(ParsingError):
    """Exception raised when a message for which a message string is being parsed is recognized, but
        a ParsingError results in its parameters or arguments failing to be recognized."""
    pass

  class EarlyTerminationError(Exception):
    """Exception raised when EOF is encountered before all required email data has been provided
        by the command-line user."""
    pass
  
class SocketError(Exception):
    """Exception raised when an any exception is encountered while creating, initiating a connection with,
    reading from, or writing to a socket."""
    pass
  
class SMTPBreakOfProtocolError(Exception):
    """Exception raised when a message breaking SMTP protocol has been sent from the client or received
    from the server."""
    pass
  
