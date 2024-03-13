#!python3
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

from System.Windows.Forms import Application, Form, TextBox, Button, Label, DialogResult
from System.Drawing import Size, Point

class InputForm(Form):
    def __init__(self):
        self.InitializeComponent()
    
    def InitializeComponent(self):
        self.Text = 'Input Dialog'
        self.Size = Size(300, 150)

        self.label = Label()
        self.label.Text = "Enter some text:"
        self.label.Location = Point(10, 20)
        self.label.Size = Size(280, 20)
        self.Controls.Add(self.label)

        self.textBox = TextBox()
        self.textBox.Location = Point(10, 50)
        self.textBox.Size = Size(280, 20)
        self.Controls.Add(self.textBox)

        self.okButton = Button()
        self.okButton.Text = 'OK'
        self.okButton.Location = Point(190, 80)
        self.okButton.Click += self.okButton_Click
        self.Controls.Add(self.okButton)

        self.cancelButton = Button()
        self.cancelButton.Text = 'Cancel'
        self.cancelButton.Location = Point(110, 80)
        self.cancelButton.Click += self.cancelButton_Click
        self.Controls.Add(self.cancelButton)

    def okButton_Click(self, sender, e):
        self.DialogResult = DialogResult.OK

    def cancelButton_Click(self, sender, e):
        self.DialogResult = DialogResult.Cancel

def get_user_input():
    form = InputForm()
    if form.ShowDialog() == DialogResult.OK:
        return form.textBox.Text
    return None

# Example usage
user_input = get_user_input()
if user_input is not None:
    print("User input: " + user_input)
else:
    print("User cancelled the input dialog.")