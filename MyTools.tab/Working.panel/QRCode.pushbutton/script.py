#!python3
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

import os
import qrcode
from qrcode.image.styles.moduledrawers import GappedSquareModuleDrawer
from qrcode.image.styledpil import StyledPilImage
from PIL import Image, ImageDraw
from System.Windows.Forms import Application, Form, TextBox, Button, Label, DialogResult
from System.Drawing import Size, Point


class InputForm(Form):
    def __init__(self):
        self.InitializeComponent()

    def InitializeComponent(self):
        self.Text = 'Input Dialog'
        self.Size = Size(300, 150)

        self.label = Label()
        self.label.Text = "Enter QR code data:"
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


def generate_qr_code(qr_data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white', image_factory=StyledPilImage, module_drawer=GappedSquareModuleDrawer()).convert('RGB')

    W, H = qr_img.size
    x_1 = int(round(13/41*W))
    x_2 = W - x_1
    y_1 = int(round(15/41*H))
    y_2 = H - y_1

    color_A = (0, 82, 165)
    color_B = (165, 0, 41)
    color_C = (0, 127, 63)
    color_D = (255, 191, 0)
    color_E = (127, 0, 31)
    black = (0, 0, 0)

    overlay = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(overlay)

    rectangles = [
        ((0, 0), (x_1, y_1), color_A),
        ((x_1, 0), (x_2, y_1), black),
        ((x_2, 0), (W, y_1), color_B),
        ((0, y_1), (x_1, y_2), color_C),
        ((x_1, y_1), (x_2, y_2), color_D),
        ((x_2, y_1), (W, y_2), color_E),
        ((0, y_2), (x_1, H), color_A),
        ((x_1, y_2), (x_2, H), black),
        ((x_2, y_2), (W, H), color_B),
    ]
    for rect in rectangles:
        draw.rectangle([rect[0], rect[1]], fill=rect[2])

    qr_pixels = qr_img.load()
    overlay_pixels = overlay.load()
    for y in range(H):
        for x in range(W):
            if qr_pixels[x, y] == black:
                qr_pixels[x, y] = overlay_pixels[x, y]

    return qr_img


def save_qr_code(qr_img):
    downloads_path = os.path.expanduser("~/Downloads")
    final_image_path = os.path.join(downloads_path, "qrcode_color_replaced.png")
    qr_img.save(final_image_path)
    return final_image_path


qr_data = get_user_input()
if qr_data is not None:
    qr_img = generate_qr_code(qr_data)
    final_image_path = save_qr_code(qr_img)
    print(f"QR code saved to: {final_image_path}")
else:
    print("User cancelled the input dialog.")