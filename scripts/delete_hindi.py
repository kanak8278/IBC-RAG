# ends with _hin.pdf
# go through all the files data/ibbi_raw and delete all the files ending with _hin.pdf

import os
import glob

for file in glob.glob("data/ibbi_raw/**/*_hin.pdf", recursive=True):
    os.remove(file)
