# photoEncryption
A simple windows executable program to keep private photos encrypted and view them as album.

This app is capable of import any photos and videos and encrypt them immediately, encrypted files are stroed in a folder named Gallery which can be found in the same path of the .exe file itself.
![image](https://github.com/user-attachments/assets/d0181e65-0828-4e28-8e24-998fd51591c3)


- On first run, app will ask for a new password to initialize the setup. Password can be set any character, which is securely stored in a hash file.
- After then, it will ask for the password on every run unless you reset.
- Also, in any case of problem loading the actual gallery, you can reset the app. Resetting will delete all stored encrypted files and the password with immediate effect.
- For safety, a security question is set up. Answer is 'blue'
![image](https://github.com/user-attachments/assets/876e3ad5-1cb0-47dd-ab52-75c78cc8b8f2)
![image](https://github.com/user-attachments/assets/46c7e8a6-c0ac-4003-8266-f1d24f96d0fd)


Features: 
- Import button to import any photos/videos. Selecting higher number of files will take more time. Patience is required.
- Single click on any image will select the file, then Export button will be accessible to export the selected file as decrypted. Don't try multiple files as there is no code for it yet.
- Right click on any selected file will show a delete option that works somehow.
- Fancy red colored delete button can be seen that is only for view.
- Double click will open any file.
- Total number of files is shown at bottom left that only updates after each five files.
- Wrong password will warn you to stay away.

Must know:
- Thumbnail preview won't appear for video.
- Thumbnail of images won't appear unless you import at least 15-20 media files and scroll a bit. This is I will work on soon.
- If less files are imported, it will show Loading... text but you can view the file upon double clicking.
- Your data is save, files are saved only in your PC. You can view the source code and also you can run and use the app from source code by running main.py file.

Enjoy!
