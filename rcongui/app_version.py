# Python script to replace {version-tag} with text from a file specified on the command line

import sys

# Get the file paths from the command-line arguments
file_path = sys.argv[1]
version_file_path = sys.argv[2]

# Open the file in read mode
with open(file_path, 'r') as file:
    data = file.read()

# Open the version file and read the version
with open(version_file_path, 'r') as version_file:
    version = version_file.read().strip()

# Replace {version-tag} with the version
data = data.replace('{version-tag}', version)

# Write the result back to the original file
with open(file_path, 'w') as file:
    file.write(data)