"""Subscribe/unsubscribe from async notifications.

This module provides functions that let you subscribe and unsubscribe from notifications. iTerm2
posts notifications when some event of interest (for example, a keystroke) occurs. By subscribing to
a notifications your async callback will be run when the event occurs.
"""
import iterm2.api_pb2
import iterm2.connection
import iterm2.rpc

RPC_ROLE_GENERIC = iterm2.api_pb2.RPCRegistrationRequest.Role.Value("GENERIC")
RPC_ROLE_SESSION_TITLE = iterm2.api_pb2.RPCRegistrationRequest.Role.Value("SESSION_TITLE")

def _get_handlers():
    """Returns the registered notification handlers.

    :returns: (session, notification_type) -> [coroutine, ...]
    """
    if not hasattr(_get_handlers, 'handlers'):
        _get_handlers.handlers = {}
    return _get_handlers.handlers

## APIs -----------------------------------------------------------------------

class SubscriptionException(Exception):
    """Raised when a subscription attempt fails."""
    pass

async def async_unsubscribe(connection, token):
    """
    Unsubscribes from a notification.

    :param connection: A connected :class:`Connection`.
    :param token: The result of a previous subscribe call.
    """
    key, coro = token
    coros = _get_handlers()[key]
    coros.remove(coro)
    if coros:
        _get_handlers()[key] = coros
    else:
        del _get_handlers()[key]
        session, notification_type = key
        await _async_subscribe(connection, False, notification_type, None, session=session)

async def async_subscribe_to_new_session_notification(connection, callback):
    """
    Registers a callback to be run when a new session is created.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an
      :class:`Connection` and iterm2.api_pb2.NewSessionNotification.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(connection, True, iterm2.api_pb2.NOTIFY_ON_NEW_SESSION, callback)

async def async_subscribe_to_keystroke_notification(connection, callback, session=None):
    """
    Registers a callback to be run when a key is pressed.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.KeystrokeNotification.
    :param session: The session to monitor, or None.

    Returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_KEYSTROKE,
        callback,
        session=session)

async def async_subscribe_to_screen_update_notification(connection, callback, session=None):
    """
    Registers a callback to be run when the screen contents change.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.ScreenUpdateNotification..
    :param session: The session to monitor, or None.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_SCREEN_UPDATE,
        callback,
        session=session)

async def async_subscribe_to_prompt_notification(connection, callback, session=None):
    """
    Registers a callback to be run when a shell prompt is received.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.PromptNotification.
    :param session: The session to monitor, or None.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_PROMPT,
        callback,
        session=session)

async def async_subscribe_to_location_change_notification(connection, callback, session=None):
    """
    Registers a callback to be run when the host or current directory changes.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.LocationChangeNotification.
    :param session: The session to monitor, or None.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_LOCATION_CHANGE,
        callback,
        session=session)

async def async_subscribe_to_custom_escape_sequence_notification(connection,
                                                                 callback,
                                                                 session=None):
    """
    Registers a callback to be run when a custom escape sequence is received.

    The escape sequence is OSC 1337 ; Custom=id=<identity>:<payload> ST

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.CustomEscapeSequenceNotification.
    :param session: The session to monitor, or None.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_CUSTOM_ESCAPE_SEQUENCE,
        callback,
        session=session)

async def async_subscribe_to_terminate_session_notification(connection, callback):
    """
    Registers a callback to be run when a session terminates.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.TerminateSessionNotification.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_TERMINATE_SESSION,
        callback,
        session=None)

async def async_subscribe_to_layout_change_notification(connection, callback):
    """
    Registers a callback to be run when the relationship between sessions, tabs,
    and windows changes.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.LayoutChangedNotification.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_LAYOUT_CHANGE,
        callback,
        session=None)

async def async_subscribe_to_focus_change_notification(connection, callback):
    """
    Registers a callback to be run when focus changes.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and
      iterm2.api_pb2.FocusChangedNotification.

    :returns: A token that can be passed to unsubscribe.
    """
    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_FOCUS_CHANGE,
        callback,
        session=None)

async def async_subscribe_to_server_originated_rpc_notification(connection, callback, name, arguments=[], timeout_seconds=5, defaults={}, role=RPC_ROLE_GENERIC, display_name=None):
    """
    Registers a callback to be run when the server wants to invoke an RPC.

    You probably want to use :meth:`iterm2.App.async_register_rpc_handler`
    instead of this. It's a much higher level API.

    :param connection: A connected :class:`Connection`.
    :param callback: A coroutine taking two arguments: an :class:`Connection` and iterm2.api_pb2.ServerOriginatedRPCNotification.
    :param timeout_seconds: How long iTerm2 should wait for this function to return or `None` to use the default timeout.
    :param defaults: Gives default values. Names correspond to argument names in `arguments`. Values are in-scope variables at the callsite.
    :param role: Defines the special purpose of this RPC. If none, use `RPC_ROLE_GENERIC`.
    :param display_name: Used by the `RPC_ROLE_SESSION_TITLE` role to give the name of the function to show in preferences.

    :returns: A token that can be passed to unsubscribe.
    """
    rpc_registration_request = iterm2.api_pb2.RPCRegistrationRequest()
    rpc_registration_request.name = name
    if timeout_seconds is not None:
        rpc_registration_request.timeout = timeout_seconds
    args = []
    for arg_name in arguments:
        arg = iterm2.api_pb2.RPCRegistrationRequest.RPCArgumentSignature()
        arg.name = arg_name
        args.append(arg)
    rpc_registration_request.arguments.extend(args)
    rpc_registration_request.role = role

    if len(defaults) > 0:
        d = []
        for name in defaults:
            assert name in arguments, "Name for default '{}' not in arguments {}".format(name, arguments)
            path = defaults[name]
            argd = iterm2.api_pb2.RPCRegistrationRequest.RPCArgument()
            argd.name = name
            argd.path = path
            d.append(argd)

        rpc_registration_request.defaults.extend(d)

    if display_name is not None:
        rpc_registration_request.display_name = display_name

    return await _async_subscribe(
        connection,
        True,
        iterm2.api_pb2.NOTIFY_ON_SERVER_ORIGINATED_RPC,
        callback,
        rpc_registration_request=rpc_registration_request)

## Private --------------------------------------------------------------------

def _string_rpc_registration_request(rpc):
    """Converts ServerOriginatedRPC or RPCSignature to a string."""
    if rpc is None:
        return None
    args = map(lambda x: x.name, rpc.arguments)
    return rpc.name + "(" + ",".join(args) + ")"

async def _async_subscribe(connection, subscribe, notification_type, callback, session=None, rpc_registration_request=None):
    _register_helper_if_needed()
    transformed_session = session if session is not None else "all"
    response = await iterm2.rpc.async_notification_request(
        connection,
        subscribe,
        notification_type,
        transformed_session,
        rpc_registration_request)
    status = response.notification_response.status
    status_ok = (status == iterm2.api_pb2.NotificationResponse.Status.Value("OK"))

    if subscribe:
        already = (status == iterm2.api_pb2.NotificationResponse.Status.Value("ALREADY_SUBSCRIBED"))
        if status_ok or already:
            _register_notification_handler(session, _string_rpc_registration_request(rpc_registration_request), notification_type, callback)
            return ((session, notification_type), callback)
    else:
        # Unsubscribe
        if status_ok:
            return

    raise SubscriptionException(iterm2.api_pb2.NotificationResponse.Status.Name(status))

def _register_helper_if_needed():
    if not hasattr(_register_helper_if_needed, 'haveRegisteredHelper'):
        _register_helper_if_needed.haveRegisteredHelper = True
        iterm2.connection.Connection.register_helper(_async_dispatch_helper)

async def _async_dispatch_helper(connection, message):
    handlers, sub_notification = _get_notification_handlers(message)
    for handler in handlers:
        assert handler is not None
        await handler(connection, sub_notification)
    return bool(handlers)

def _get_handler_key_from_notification(notification):
    key = None

    if notification.HasField('keystroke_notification'):
        key = (notification.keystroke_notification.session, iterm2.api_pb2.NOTIFY_ON_KEYSTROKE)
        notification = notification.keystroke_notification
    elif notification.HasField('screen_update_notification'):
        key = (notification.screen_update_notification.session,
               iterm2.api_pb2.NOTIFY_ON_SCREEN_UPDATE)
        notification = notification.screen_update_notification
    elif notification.HasField('prompt_notification'):
        key = (notification.prompt_notification.session, iterm2.api_pb2.NOTIFY_ON_PROMPT)
        notification = notification.prompt_notification
    elif notification.HasField('location_change_notification'):
        key = (notification.location_change_notification.session,
               iterm2.api_pb2.NOTIFY_ON_LOCATION_CHANGE)
        notification = notification.location_change_notification
    elif notification.HasField('custom_escape_sequence_notification'):
        key = (notification.custom_escape_sequence_notification.session,
               iterm2.api_pb2.NOTIFY_ON_CUSTOM_ESCAPE_SEQUENCE)
        notification = notification.custom_escape_sequence_notification
    elif notification.HasField('new_session_notification'):
        key = (None, iterm2.api_pb2.NOTIFY_ON_NEW_SESSION)
        notification = notification.new_session_notification
    elif notification.HasField('terminate_session_notification'):
        key = (None, iterm2.api_pb2.NOTIFY_ON_TERMINATE_SESSION)
        notification = notification.terminate_session_notification
    elif notification.HasField('layout_changed_notification'):
        key = (None, iterm2.api_pb2.NOTIFY_ON_LAYOUT_CHANGE)
        notification = notification.layout_changed_notification
    elif notification.HasField('focus_changed_notification'):
        key = (None, iterm2.api_pb2.NOTIFY_ON_FOCUS_CHANGE)
        notification = notification.focus_changed_notification
    elif notification.HasField('server_originated_rpc_notification'):
        key = (None, iterm2.api_pb2.NOTIFY_ON_SERVER_ORIGINATED_RPC, _string_rpc_registration_request(notification.server_originated_rpc_notification.rpc))
    return key, notification

def _get_notification_handlers(message):
    key, sub_notification = _get_handler_key_from_notification(message.notification)
    if key is None:
        return ([], None)

    fallback = (None, key[1])

    if key in _get_handlers():
        return (_get_handlers()[key], sub_notification)
    elif fallback in _get_handlers():
        return (_get_handlers()[fallback], sub_notification)
    return ([], None)

def _register_notification_handler(session, rpc_registration_request, notification_type, coro):
    assert coro is not None

    if rpc_registration_request is None:
        key = (session, notification_type)
    else:
        key = (session, notification_type, rpc_registration_request)

    if key in _get_handlers():
        _get_handlers()[key].append(coro)
    else:
        _get_handlers()[key] = [coro]
