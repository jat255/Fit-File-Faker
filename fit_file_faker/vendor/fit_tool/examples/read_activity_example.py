from fit_file_faker.vendor.fit_tool.fit_file import FitFile


def main():
    """ The following code reads all the bytes from a FIT formatted file and then decodes these bytes to
        create a FIT file object. We then convert the FIT data to a human-readable CSV file.
    """
    path = '../tests/data/sdk/Activity.fit'
    fit_file = FitFile.from_file(path)

    out_path = '../tests/data/sdk/Activity.csv'
    fit_file.to_csv(out_path)


if __name__ == "__main__":
    main()
