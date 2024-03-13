#!python3
from pyrevit import forms

import qrcode

# # Get the parameter by name
# qrcodeurl = proj_info.LookupParameter('Project QR Code')

# if qrcodeurl.AsString()[0:4] == "http":
#     qr = qrcode.QRCode()
#     qr.add_data(qrcodeurl.AsString())
#     f = io.StringIO()
#     qr.print_ascii(out=f)
#     f.seek(0)
#     qrcodechars = ""
#     with f as fi:
#         for line in fi:
#             qrcodechars += line[4::]
#     t.Start()
#     qrcodeurl.Set(qrcodechars)
#     t.Commit()
# else:
#     print("Not a valid address")

import sys

message = sys.argv[1]

name = message.split("My name is ")[1]
response = "Hello " + name + ", My name is Python 3.8"
print(response)