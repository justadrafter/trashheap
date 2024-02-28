#!python3
import sys
sys.path.append(r'c:\program files\python38\lib\site-packages')
import io
import qrcode

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction

doc = __revit__.ActiveUIDocument.Document
t = Transaction(doc, 'Set QR Code')

# Find the Project Information element
proj_info_collector = FilteredElementCollector(doc)
proj_info = proj_info_collector.OfCategory(BuiltInCategory.OST_ProjectInformation).FirstElement()

# Get the parameter by name
qrcodeurl = proj_info.LookupParameter('Project QR Code')

if qrcodeurl.AsString()[0:4] == "http":
    qr = qrcode.QRCode()
    qr.add_data(qrcodeurl.AsString())
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    qrcodechars = ""
    with f as fi:
        for line in fi:
            qrcodechars += line[4::]
    t.Start()
    qrcodeurl.Set(qrcodechars)
    t.Commit()
else:
    print("Not a valid address")