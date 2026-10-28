#!python3
"""
Generate a coloured QR code using Segno and PyPNG.

Requirements:
    segno
    pypng

The QR code is saved to:
    ~/Downloads/qrcode_color_replaced.png
"""

import clr

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

import os

import png
import segno

from System.Drawing import Point, Size
from System.Windows.Forms import (
    Button,
    DialogResult,
    Form,
    Label,
    TextBox,
)


BOX_SIZE = 10
MODULE_RATIO = 0.8
QUIET_ZONE = 0

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

COLOR_A = (0, 82, 165)
COLOR_B = (165, 0, 41)
COLOR_C = (0, 127, 63)
COLOR_D = (255, 191, 0)
COLOR_E = (127, 0, 31)


class InputForm(Form):
    def __init__(self):
        Form.__init__(self)
        self.InitializeComponent()

    def InitializeComponent(self):
        self.Text = "Input Dialog"
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
        self.okButton.Text = "OK"
        self.okButton.Location = Point(190, 80)
        self.okButton.Click += self.okButton_Click
        self.Controls.Add(self.okButton)

        self.cancelButton = Button()
        self.cancelButton.Text = "Cancel"
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


def get_module_color(x, y, width, height):
    """Split module coordinates into nine regions as close to equal as possible."""
    x_1 = int(round(width / 3.0))
    x_2 = int(round(2.0 * width / 3.0))

    y_1 = int(round(height / 3.0))
    y_2 = int(round(2.0 * height / 3.0))

    if y < y_1:
        if x < x_1:
            return COLOR_A
        if x < x_2:
            return BLACK
        return COLOR_B

    if y < y_2:
        if x < x_1:
            return COLOR_C
        if x < x_2:
            return COLOR_D
        return COLOR_E

    if x < x_1:
        return COLOR_A
    if x < x_2:
        return BLACK
    return COLOR_B


def create_qr_matrix(qr_data):
    qr = segno.make_qr(
        qr_data,
        error="M",
        boost_error=False,
    )

    return [
        [bool(module) for module in row]
        for row in qr.matrix_iter(
            scale=1,
            border=0,
        )
    ]


def create_pixel_rows(matrix):
    module_count = len(matrix)

    qr_size = module_count * BOX_SIZE
    quiet_zone_size = QUIET_ZONE * BOX_SIZE
    image_size = qr_size + quiet_zone_size * 2

    white_row = bytearray(WHITE * image_size)

    rows = [
        bytearray(white_row)
        for _ in range(image_size)
    ]

    module_size = int(BOX_SIZE * MODULE_RATIO)
    module_offset = (BOX_SIZE - module_size) // 2

    for module_y, matrix_row in enumerate(matrix):
        for module_x, is_dark in enumerate(matrix_row):
            if not is_dark:
                continue

            start_x = (
                quiet_zone_size
                + module_x * BOX_SIZE
                + module_offset
            )
            start_y = (
                quiet_zone_size
                + module_y * BOX_SIZE
                + module_offset
            )

            color = get_module_color(
                module_x,
                module_y,
                module_count,
                module_count,
            )

            for offset_y in range(module_size):
                image_y = start_y + offset_y

                row = rows[image_y]

                for offset_x in range(module_size):
                    image_x = start_x + offset_x

                    pixel_index = image_x * 3

                    row[pixel_index] = color[0]
                    row[pixel_index + 1] = color[1]
                    row[pixel_index + 2] = color[2]

    return rows, image_size


def generate_qr_code(qr_data):
    matrix = create_qr_matrix(qr_data)
    return create_pixel_rows(matrix)


def save_qr_code(qr_image):
    rows, image_size = qr_image

    downloads_path = os.path.expanduser("~/Downloads")
    final_image_path = os.path.join(
        downloads_path,
        "qrcode_color_replaced.png",
    )

    writer = png.Writer(
        width=image_size,
        height=image_size,
        greyscale=False,
        alpha=False,
        bitdepth=8,
    )

    with open(final_image_path, "wb") as png_file:
        writer.write(png_file, rows)

    return final_image_path


qr_data = get_user_input()

if qr_data is not None:
    qr_image = generate_qr_code(qr_data)
    final_image_path = save_qr_code(qr_image)

    print("QR code saved to: {}".format(final_image_path))
else:
    print("User cancelled the input dialog.")
