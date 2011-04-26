import glob, os

if __name__ == "__main__":
    files = glob.glob("./*.dat")
    files.extend(glob.glob("./*.gnu"))    
    files.extend(glob.glob("./*.eps"))
    
    for file in files:
        os.unlink(file)