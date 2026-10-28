#!python2
"""Revit print settings for each one-view PDF job."""

import uuid

from System.Drawing.Printing import PrinterSettings

from pyrevit import DB


PAPER_TOLERANCE_INCHES = 0.01


def _matching_paper_size(print_manager, view, printer_name):
    outline = view.Outline
    width = (outline.Max.U - outline.Min.U) * 12.0
    height = (outline.Max.V - outline.Min.V) * 12.0
    if width <= 0 or height <= 0:
        raise ValueError("Revit could not determine the view's paper size.")

    revit_sizes = {}
    for paper_size in print_manager.PaperSizes:
        revit_sizes[paper_size.Name.lower()] = paper_size

    printer = PrinterSettings()
    printer.PrinterName = printer_name
    candidates = []
    for system_size in printer.PaperSizes:
        revit_size = revit_sizes.get(system_size.PaperName.lower())
        if revit_size is None:
            continue
        # PageOrientation is Landscape; Windows reports the stock size in
        # either order, so use its longer side as the printable page width.
        paper_width = max(system_size.Width, system_size.Height) / 100.0
        paper_height = min(system_size.Width, system_size.Height) / 100.0
        if (
                paper_width + PAPER_TOLERANCE_INCHES >= width
                and paper_height + PAPER_TOLERANCE_INCHES >= height
        ):
            candidates.append((
                paper_width * paper_height,
                max(paper_width - width, paper_height - height),
                revit_size.Name,
                revit_size
            ))

    if not candidates:
        raise ValueError(
            'No landscape paper size on "{}" fits this view at 100% '
            '({:.2f} x {:.2f} inches).'
            .format(printer_name, width, height)
        )

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0][3]


def configure_single_view(print_manager, view, printer_name):
    """Apply the requested options through a temporary print setting."""
    paper_size = _matching_paper_size(print_manager, view, printer_name)
    print_setup = print_manager.PrintSetup
    print_setup.CurrentPrintSetting = print_setup.InSession
    parameters = print_setup.CurrentPrintSetting.PrintParameters
    parameters.PaperSize = paper_size
    parameters.PageOrientation = DB.PageOrientationType.Landscape
    parameters.PaperPlacement = DB.PaperPlacementType.Center
    parameters.ZoomType = DB.ZoomType.Zoom
    parameters.Zoom = 100
    parameters.HideReforWorkPlanes = True
    parameters.HideUnreferencedViewTags = True
    parameters.HideScopeBoxes = True
    parameters.HideCropBoundaries = True
    parameters.HiddenLineViews = DB.HiddenLineViewsType.VectorProcessing
    parameters.RasterQuality = DB.RasterQualityType.High
    parameters.ColorDepth = DB.ColorDepthType.Color

    if not print_setup.SaveAs("SinglePDF_{}".format(uuid.uuid4().hex)):
        raise RuntimeError("Revit could not apply the single-view print setup.")
