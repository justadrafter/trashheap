#!python2
"""Printer-neutral entry point for PDF printing commands."""

PDF_BACKEND = "pdf24"


def create_pdf_printer():
    """Select the PDF backend for all commands in this extension."""
    if PDF_BACKEND == "pdf24":
        from pdf24printing import Pdf24Printer
        return Pdf24Printer()
    raise ValueError('Unknown PDF backend "{}".'.format(PDF_BACKEND))
