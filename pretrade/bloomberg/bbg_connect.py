import blpapi

def connect_user():
    session_options = blpapi.SessionOptions()
    session_options.setServerHost('localhost')
    session_options.setServerPort(8194)

    session = blpapi.Session(session_options)
    identity = 0

    if not session.start():
        raise Exception('Failed to start a bbg session !')
    else:
        return session, identity
