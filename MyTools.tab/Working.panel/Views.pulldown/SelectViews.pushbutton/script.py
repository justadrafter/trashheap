"""Select multiple views from a list"""
#pylint: disable=import-error,invalid-name
from pyrevit import revit
from pyrevit import forms

__title__ = "Select Views"
__author__ = "Adam Shaw"

selection = revit.get_selection()
sel_views = forms.select_views(title='Select Views')

if sel_views:
    selection.set_to(sel_views)
