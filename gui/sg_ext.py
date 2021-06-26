import PySimpleGUIWx as wx
import PySimpleGUI as sg


sg.ChangeLookAndFeel(
    index="SystemDefault",
)


def PopupOkCancelTitled(*args, title=None, button_color=None, background_color=None, text_color=None, auto_close=False,
                        auto_close_duration=None, non_blocking=False, icon=wx.DEFAULT_WINDOW_ICON, line_width=None, font=None,
                        no_titlebar=False, grab_anywhere=False, keep_on_top=False, location=(None, None)):
    """
    Extend the normal PopupYesNo functionality to include a specific title.
    """
    return wx.Popup(*args, title=title, button_type=wx.POPUP_BUTTONS_OK_CANCEL, background_color=background_color, text_color=text_color,
                    non_blocking=non_blocking, icon=icon, line_width=line_width, button_color=button_color,
                    auto_close=auto_close, auto_close_duration=auto_close_duration, font=font, no_titlebar=no_titlebar,
                    grab_anywhere=grab_anywhere, keep_on_top=keep_on_top, location=location)


def PopupWindowStartSession(title, submit_text, windows, configurations, icon=wx.DEFAULT_WINDOW_ICON,
                            default_window=None, default_configuration=None):
    return wx.Window(
        title=title,
        icon=icon,
        layout=[
            [wx.Text("Window:       "), wx.InputCombo(windows, default_value=default_window or windows[0] if windows else None)],
            [wx.Text("Configuration:"), wx.InputCombo(configurations, default_value=default_configuration or configurations[0] if configurations else None)],
            [wx.Submit(submit_text), wx.Cancel()],
        ],
    ).read(close=True)


def PopupWindowEvents(title, events, icon=wx.DEFAULT_WINDOW_ICON):
    if not events:
        events = [
            ["                    " for row in range(3)] for col in range(1)
        ]
    return sg.Window(
        title=title,
        icon=icon,
        layout=[
            [sg.Table(
                justification="left",
                max_col_width=300,
                col_widths=[
                    50,
                    90,
                    200,
                ],
                headings=[
                    "Instance",
                    "Timestamp",
                    "Event",
                ],
                values=events,
                key="table",
            )],
            [sg.Cancel(), sg.Button("Delete Highlighted", button_color="red")],
        ],
    ).read(close=True)


INPUT_SCHEMA = {
    "TEXT": {
        "widget": sg.Multiline,
        "default_kwarg": "default_text",
        "required_kwargs": {
            "size": (45, 4),
        },
    },
    "BOOL": {
        "widget": sg.Checkbox,
        "default_kwarg": "default",
        "required_kwargs": {
            "text": "",
        },
    },
    "VARCHAR": {
        "widget": sg.Input,
        "default_kwarg": "default_text",
        "required_kwargs": {},
    },
    "VARCHAR_CHOICES": {
        "widget": sg.InputCombo,
        "default_kwarg": "default_value",
        "required_kwargs": {
            "values": "choices",
        },
    },
    "INT": {
        "widget": sg.Input,
        "default_kwarg": "default_text",
        "required_kwargs": {},
    },
}


def handle_required_kwargs(mdl, kwargs, parsed=None):
    """Handle the "required" kwargs functionality taken from the input schema available.

    If a required kwarg is using a value that's available within the field being parsed,
    we'll use the value of that instead of the value entered initially.
    """
    if not parsed:
        parsed = {}

    for key, val in kwargs.items():
        parsed_val = getattr(mdl, str(val), val)
        parsed[key] = parsed_val

    return parsed


def generate_input_fields(fields, model_obj):
    rows = []

    for i, field in enumerate(fields, start=1):
        row, mdl = (
            [],
            getattr(model_obj._schema.model, field),
        )
        val, verbose, help_text, field_type = (
            getattr(model_obj, field),
            mdl.verbose_name,
            mdl.help_text,
            mdl.field_type,
        )
        # Update explicit field_type so we can use an input combo
        # box on any inputs that use the "choices" option.
        if field_type == "VARCHAR" and mdl.choices:
            field_type = "VARCHAR_CHOICES"

        # Retrieve our schema and get the input field
        # kwargs ready for widget generation.
        schema = INPUT_SCHEMA[field_type]
        default_kwargs = {
            schema["default_kwarg"]: val,
        }
        required_kwargs = handle_required_kwargs(
            mdl=mdl,
            kwargs=schema["required_kwargs"],
        )

        rows.append([sg.Text(verbose), schema["widget"](key=field, **default_kwargs, **required_kwargs)])
        rows.append([sg.Text(help_text, font=("Any", 8))])

        if i != len(fields):
            rows.append([sg.HorizontalSeparator(color="white")])
    return rows


def generate_settings_input_layout(settings_obj):
    """Generate a valid layout used to generate and display editable settings.
    """
    fields = settings_obj._schema.model.editable_fields
    inputs = generate_input_fields(
        fields=fields,
        model_obj=settings_obj,
    )
    return [
        inputs,
        [sg.Save(), sg.Cancel()],
    ]


def PopupWindowSettings(title, settings_obj, icon=sg.DEFAULT_WINDOW_ICON):
    return sg.Window(
        title=title,
        icon=icon,
        layout=generate_settings_input_layout(settings_obj=settings_obj),
    ).read(close=True)


def generate_configuration_input_layout(configuration_obj):
    """Generate a valid layout used to generate and display an editable configuration.
    """
    tabs = []
    grouped_fields = configuration_obj._schema.model.grouped_fields
    # Our grouped fields will contain a list of labels with a dictionary
    # of the expected settings in each group.
    for group, fields in grouped_fields.items():
        tab = generate_input_fields(
            fields=fields,
            model_obj=configuration_obj,
        )
        tabs.append([sg.Tab(group, tab, key=None)])
    return [
        [sg.TabGroup(tabs)],
        [
            sg.Column(layout=[[sg.Save(), sg.Cancel()]]),
            sg.Column(layout=[[sg.Button(button_text="Delete", button_color="red"), sg.Button("Replicate", button_color="green")]])
        ],
    ]


def PopupWindowConfiguration(title, configuration_obj, icon=sg.DEFAULT_WINDOW_ICON):
    event, values = sg.Window(
        title=title,
        icon=icon,
        layout=generate_configuration_input_layout(configuration_obj=configuration_obj),
    ).read(close=True)
    # Ensure only configuration fields are returned as part of
    # the values dictionary.
    values = {key: val for key, val in values.items() if key in [
        key for key in configuration_obj._meta.fields.keys()
        if key != "id"
    ]}
    return event, values
