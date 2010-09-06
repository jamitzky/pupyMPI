#!/usr/bin/env python

import sys, glob, re, shutil

if __name__ == "__main__":
    try:
        from_folder = sys.argv[1]
    except IndexError:
        print "Run with a single argument: the folder to migrate"
        sys.exit(1)
    print "Migrating data for folder", from_folder

    # Find the folders in the proper format
    folders = glob.glob(from_folder + "single_*")
    folders.extend (glob.glob(from_folder + "collective_*"))
    folders.extend (glob.glob(from_folder + "single*"))
    folders.extend (glob.glob(from_folder + "collective*"))

    folder_re = re.compile(".*(collective|single)_?(\d+)")
    date_re = re.compile(".*(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.csv")

    for folder in folders:
        print "\tFinding folder", folder
        match = folder_re.match(folder)
        run_type, procs = match.groups()

        # Find all the csv files
        csv_files = glob.glob(folder + "/*.csv")

        for csv_file in csv_files:
            print "\t\tFinding file", csv_file
            # locate the date from the file
            date_match = date_re.match(csv_file)
            if date_match:
                date = date_match.groups()[0]

                # Generate a new filename
                to_file = "%spupymark.%s.%sprocs.4MB.%s.csv" % (from_folder, run_type[:4], procs, date)

                # Copy the file to the new location
                shutil.copyfile(csv_file, to_file)



