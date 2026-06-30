from rpw.ui.forms import TextInput
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Element, Transaction
import re

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
t = Transaction(doc, 'Set Parameter by Name')

_inputvalue = TextInput('Enter Size', default="")
_inputvalue = re.findall(r'[A-Za-z]+|\d+', _inputvalue)
_length = 0
_textbtm = ""
_texttop = ""
_textloc = 0

if not _inputvalue:
    _barnum_temp = ""
    _bars_temp = ""
else:
    try:
        _barnum_temp, _bars_temp, _length = _inputvalue
    except:
        _barnum_temp, _bars_temp = _inputvalue


def get_length(string):
    temp_len = 0
    _chars = {"a": 129.0, "b": 129.0, "c": 107.5, "d": 129.0, "e": 129.0, "f": 86.0, "g": 129.0, "h": 129.0, "i": 43.0,
              "j": 64.5,
              "k": 107.5, "l": 43.0, "m": 172.0, "n": 129.0, "o": 129.0, "p": 129.0, "q": 129.0, "r": 86.0, "s": 107.5,
              "t": 64.5,
              "u": 129.0, "v": 107.5, "w": 172.0, "x": 107.5, "y": 107.5, "z": 107.5, "A": 172.0, "B": 150.5,
              "C": 150.5, "D": 150.5,
              "E": 150.5, "F": 129.0, "G": 172.0, "H": 150.5, "I": 64.5, "J": 107.5, "K": 150.5, "L": 140.0, "M": 172.0,
              "N": 150.5,
              "O": 172.0, "P": 150.5, "Q": 172.0, "R": 172.0, "S": 150.5, "T": 129.0, "U": 150.5, "V": 150.5,
              "W": 215.0, "X": 150.5,
              "Y": 150.5, "Z": 129.0, "-": 86.0, "1": 129.0, "2": 129.0, "3": 129.0, "4": 129.0, "5": 129.0, "6": 129.0,
              "7": 129.0,
              "8": 129.0, "9": 129.0, "0": 129.0, " ": 120, "(": 70, ")": 70, "/": 70, "\\": 70}
    for i in string:
        temp_len += _chars[i]
    return temp_len


def get_cts(barchar):
    _bars_cts = [["AaEeJjNnSsWw", 300], ["BbFfKkPpTtXx", 250], ["CcGgLlQqUuYy", 200], ["DdHhMmRrVvZz", 150]]
    for i in _bars_cts:
        j, k = i
        if barchar in j:
            return (k)


def get_parameter_value_by_name(element, parameterName):
    _temp = element.LookupParameter(parameterName).AsValueString()
    if _temp == None:
        _temp = element.LookupParameter(parameterName).AsString()
    return _temp


def set_parameter_by_name(element, parameterName, value):
    element.LookupParameter(parameterName).Set(value)


# convert units to mm coz revit retarded
def convertunits(number):
    return (number / 304.8)


# Select element from revit.
selection = [doc.GetElement(x) for x in uidoc.Selection.GetElementIds()]

# Start Transaction
t.Start()

for _detail in selection:
    # revit 2019
    try:
        _start = int(get_parameter_value_by_name(_detail, "Start Rebar Area Extents"))
        _end = int(get_parameter_value_by_name(_detail, "End Rebar Area Extents"))
        _textloc = int(get_parameter_value_by_name(_detail, "Text Location"))
        _btm = int(get_parameter_value_by_name(_detail, "Start Rebar Extension"))
        _top = int(get_parameter_value_by_name(_detail, "End Rebar Extension"))
        _text_top_on = get_parameter_value_by_name(_detail, "Text TOP On/Off")
        _text_gettop = get_parameter_value_by_name(_detail, "Text TOP")
        _text_btm_on = get_parameter_value_by_name(_detail, "Text BTM On/Off")
        _text_getbtm = get_parameter_value_by_name(_detail, "Text BTM")
    except:
        # revit 2021
        _start = int(get_parameter_value_by_name(_detail, "LEFT Extent"))
        _end = int(get_parameter_value_by_name(_detail, "RIGHT Extent"))
        _textloc = int(get_parameter_value_by_name(_detail, "Text Location"))
        _btm = int(get_parameter_value_by_name(_detail, "BTM Length"))
        _top = int(get_parameter_value_by_name(_detail, "TOP Length"))
        _text_top_on = get_parameter_value_by_name(_detail, "Text TOP Vis")
        _text_gettop = get_parameter_value_by_name(_detail, "Text TOP")
        _text_btm_on = get_parameter_value_by_name(_detail, "Text BTM Vis")
        _text_getbtm = get_parameter_value_by_name(_detail, "Text BTM")

    if _barnum_temp == "" and _bars_temp == "":
        _tempval = _text_gettop.split("-")
        _barnum = _tempval[0]
        _bars = _tempval[1]
    else:
        _barnum = _barnum_temp
        _bars = _bars_temp

    _newbarcts = (int(_barnum) - 1) * get_cts(_bars)
    _diff = (_newbarcts - (_start + _end)) / 2
    _length = int(_length)

    if (_start + _diff) < 50 or (_end + _diff) < 50:
        _startnew = _endnew = _newbarcts / 2
    else:
        _startnew = _start + _diff
        _endnew = _end + _diff

    _texttop = (_barnum + "-" + _bars).upper()
    if _length:
        _textbtm = str(_length) + " LG"
    elif _text_btm_on == 'Yes':
        _textbtm = _text_getbtm
    else:
        _textbtm = ""

    _text_len = 0
    if _text_top_on == 'Yes':
        _text_len = get_length(_texttop)
    if _text_btm_on == 'Yes' or (_length > 0):
        if _text_len < get_length(_textbtm):
            _text_len = get_length(_textbtm)

    if _textloc < 10000:
        if (_endnew + _startnew) < 620:
            _textloc = 10000 - _endnew - _text_len / 2 - 250
        elif _text_len > _endnew:
            _textloc = 10000 - _endnew - _text_len / 2 - 100
        else:
            _textloc = 10000 - _text_len / 2 - 100
    elif _textloc > 10000:
        if (_endnew + _startnew) < 620:
            _textloc = 10000 + _startnew + _text_len / 2 + 250
        elif _text_len > _startnew:
            _textloc = 10000 + _startnew + _text_len / 2
        else:
            _textloc = 10000 + _text_len / 2 + 100
    else:
        _textloc = 10000

    _length_diff = (_length - _top - _btm) / 2

    if _length:
        if ((_top + _length_diff) < 0) or ((_btm + _length_diff) < 0):
            _topnew = _btmnew = _length / 2
        else:
            _topnew = _top + _length_diff
            _btmnew = _btm + _length_diff

    try:
        set_parameter_by_name(_detail, "Start Rebar Area Extents", convertunits(_startnew))
        set_parameter_by_name(_detail, "End Rebar Area Extents", convertunits(_endnew))
    except:
        set_parameter_by_name(_detail, "LEFT Extent", convertunits(_startnew))
        set_parameter_by_name(_detail, "RIGHT Extent", convertunits(_endnew))

    set_parameter_by_name(_detail, "Text TOP", _texttop)
    set_parameter_by_name(_detail, "Text Location", convertunits(_textloc))

    if _length:
        try:
            set_parameter_by_name(_detail, "Start Rebar Extension", convertunits(_btmnew))
            set_parameter_by_name(_detail, "End Rebar Extension", convertunits(_topnew))
            set_parameter_by_name(_detail, "Text BTM On/Off", True)
        except:
            set_parameter_by_name(_detail, "BTM Length", convertunits(_btmnew))
            set_parameter_by_name(_detail, "TOP Length", convertunits(_topnew))
            set_parameter_by_name(_detail, "Text BTM Vis", True)
        set_parameter_by_name(_detail, "Text BTM", _textbtm)


# End Transaction
t.Commit()
