import PySimpleGUIWx as sg


def PopupOkCancelTitled(*args, title=None, button_color=None, background_color=None, text_color=None, auto_close=False,
                        auto_close_duration=None, non_blocking=False, icon=sg.DEFAULT_WINDOW_ICON, line_width=None, font=None,
                        no_titlebar=False, grab_anywhere=False, keep_on_top=False, location=(None, None)):
    """
    Extend the normal PopupYesNo functionality to include a specific title.
    """
    return sg.Popup(*args, title=title, button_type=sg.POPUP_BUTTONS_OK_CANCEL, background_color=background_color, text_color=text_color,
                    non_blocking=non_blocking, icon=icon, line_width=line_width, button_color=button_color,
                    auto_close=auto_close, auto_close_duration=auto_close_duration, font=font, no_titlebar=no_titlebar,
                    grab_anywhere=grab_anywhere, keep_on_top=keep_on_top, location=location)


def PopupWindowConfiguration(title, submit_text, windows, configurations, icon=sg.DEFAULT_WINDOW_ICON,
                             default_window=None, default_configuration=None):
    return sg.Window(
        title=title,
        icon=icon,
        layout=[
            [sg.Text("Window:       "), sg.InputCombo(windows, default_value=default_window or windows[0])],
            [sg.Text("Configuration:"), sg.InputCombo(configurations, default_value=default_configuration or configurations[0])],
            [sg.Submit(submit_text), sg.Cancel()],
        ],
    ).read(close=True)

