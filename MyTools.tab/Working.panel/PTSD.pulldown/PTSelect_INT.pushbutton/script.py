__title__ = "Filter INTERs"
__author__ = "Adam Shaw"

from revitfunctions.basics import filter_and_select_elements


def main():
    filter_and_select_elements(
        [("HIGH", "No"), ("LOW", "No"), ("END", "No"), ("Type", "PT Height_HERA")]
    )


if __name__ == "__main__":
    main()
