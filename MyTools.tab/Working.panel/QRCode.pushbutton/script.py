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
import subprocess

import png
import segno
from pyrevit import script
from qr_input_ui import show_qr_input

from System.Drawing import Point, Size
from System.Windows.Forms import (
    Button,
    DialogResult,
    Form,
    FormBorderStyle,
    FormStartPosition,
    Label,
    LinkLabel,
    MessageBox,
    MessageBoxButtons,
    MessageBoxIcon,
)


BOX_SIZE = 10
MODULE_RATIO = 0.8
QUIET_ZONE = 2  # 20 pixels on each side at BOX_SIZE = 10.

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

COLOR_A = (0, 82, 165)
COLOR_B = (165, 0, 41)
COLOR_C = (0, 127, 63)
COLOR_D = (255, 191, 0)
COLOR_E = (127, 0, 31)


def get_user_input():
    return show_qr_input()


class SavedQRCodeForm(Form):
    def __init__(self, image_path):
        Form.__init__(self)
        self.output_folder = os.path.dirname(image_path)
        self.Text = "QR code saved"
        self.ClientSize = Size(540, 125)
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.StartPosition = FormStartPosition.CenterScreen
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.ShowInTaskbar = False

        self.path_label = Label()
        self.path_label.Text = image_path
        self.path_label.Location = Point(10, 10)
        self.path_label.Size = Size(520, 45)
        self.Controls.Add(self.path_label)

        self.folder_link = LinkLabel()
        self.folder_link.Text = "Open in Windows Explorer"
        self.folder_link.Location = Point(10, 65)
        self.folder_link.Size = Size(300, 25)
        self.folder_link.LinkClicked += self.open_output_folder
        self.Controls.Add(self.folder_link)

        self.close_button = Button()
        self.close_button.Text = "Close"
        self.close_button.Location = Point(440, 90)
        self.close_button.DialogResult = DialogResult.OK
        self.Controls.Add(self.close_button)
        self.AcceptButton = self.close_button
        self.CancelButton = self.close_button

    def open_output_folder(self, sender, args):
        try:
            subprocess.Popen(["explorer.exe", self.output_folder])
        except Exception:
            script.get_logger().exception(
                "Could not open QR output folder in Windows Explorer: {}".format(
                    self.output_folder
                )
            )
            MessageBox.Show(
                "The QR code was saved, but Windows Explorer could not open:\n{}"
                .format(self.output_folder),
                "Open output folder",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error,
            )


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

    downloads_path = os.path.normpath(os.path.expanduser("~/Downloads"))
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


def main():
    qr_data = get_user_input()

    qr_image = generate_qr_code(qr_data)
    final_image_path = save_qr_code(qr_image)
    saved_form = SavedQRCodeForm(final_image_path)
    try:
        saved_form.ShowDialog()
    finally:
        saved_form.Dispose()
    return final_image_path


if __name__ == "__main__":
    main()
