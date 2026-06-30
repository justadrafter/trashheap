from rpw.ui.forms import FlexForm, Button, TextBox, Label, Separator

components = [
    Label("No. Bars:"),
    TextBox("bars_num", Text=""),

    Label("Bar Size Code:"),
    TextBox("bars_size", Text=""),

    Label("Spacing (mm):"),
    TextBox("bars_spacing", Text=""),

    Label("Length (mm):"),
    TextBox("bars_length", Text=""),
    Separator(),
    Button("OK")
]

form = FlexForm('Test', components)
form.show()