import sys, os, io
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox
from auth import is_password_set, create_password, verify_password
from encryption import encrypt_file, decrypt_file
from file_utils import choose_files, choose_export_location, is_image, is_video, generate_video_thumbnail, set_file_creation_time_windows, resource_path
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QLabel, QDialog, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QPixmap, QImage, QFont
import tempfile
import subprocess
from encryption import decrypt_file, generate_thumbnail
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QLabel,
    QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QLineEdit,
    QMessageBox, QDialog, QScrollArea, QInputDialog, QGridLayout, QFrame, QMenu 
)
from PyQt5 import QtCore
from PIL import Image, ExifTags
import os
from PyQt5.QtCore import QThread, pyqtSignal, QObject, Qt, QRunnable, QThreadPool, pyqtSlot



GALLERY_FOLDER = "gallery"

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Gallery Login")
        self.layout = QVBoxLayout()

        # Image label
        self.image_label = QLabel()
        pixmap = QPixmap(resource_path("lock.png"))
        pixmap = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # resize if needed
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        self.label = QLabel("Password please:" if is_password_set() else "Set a password:")
        font = QFont()
        font.setPointSize(14)  # set font size here
        self.label.setFont(font)
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.button = QPushButton("Challuu!" if is_password_set() else "Set Password")
        font = QFont()
        font.setPointSize(14)  # set font size here
        self.label.setFont(font)
        self.button.clicked.connect(self.handle_password)

        self.button1 = QPushButton("Reset!")
        self.button1.clicked.connect(self.reset_password)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.button1)
        self.button1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout.addWidget(self.button1, alignment=Qt.AlignHCenter)
        self.layout.setContentsMargins(0,0,0,10)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout.addWidget(self.button, alignment=Qt.AlignHCenter)
        self.button.setFixedWidth(100)
        self.button.setFixedHeight(40)

        self.setLayout(self.layout)
        self.resize(600,400)

    def handle_password(self):
        pwd = self.input.text()
        if is_password_set():
            if verify_password(pwd):
                self.gallery = GalleryApp(pwd)
                self.gallery.show()
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Stay away!!!!")
        else:
            create_password(pwd)
            QMessageBox.information(self, "Success", "Password set!")
            self.gallery = GalleryApp(pwd)
            self.gallery.show()
            self.close()

    def reset_password(self):
            # Ask security question first
            correct_answer = "blue"  # set your secret answer here
            answer, ok = QInputDialog.getText(self, "Security Check", "What is your favorite color?")
            
            if not ok:  # User cancelled input
                return

            if answer.strip().lower() != correct_answer.lower():
                QMessageBox.warning(self, "Wrong Answer", "Security answer is incorrect. Reset cancelled.")
                return

            reply = QMessageBox.question(
                self,
                "Reset Password and Delete All Data",
                "This will delete your password and all saved files. Are you sure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                # Delete password file           
                try:
                    PASSWORD_HASH_FILE = os.path.join("config", "password.hash")
                    if os.path.exists(PASSWORD_HASH_FILE):
                        os.remove(PASSWORD_HASH_FILE)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete password file:\n{e}")
                    return

                # Delete all encrypted files
                try:
                    folder = "gallery"
                    for fname in os.listdir(folder):
                        if fname.endswith(".enc"):
                            os.remove(os.path.join(folder, fname))
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete gallery files:\n{e}")
                    return

                QMessageBox.information(self, "Reset Complete", "Password and all files deleted. The app will restart.")

                # Close current gallery window
                self.close()

                # Open login window again
                self.login = LoginWindow()
                self.login.show()


class ThumbnailWorkerSignals(QObject):
    loaded = pyqtSignal(str, object)  # fname, PIL image or None


class ThumbnailLabel(QLabel):
    clicked = pyqtSignal(str)       # emits filename on single click
    doubleClicked = pyqtSignal(str) # emits filename on double click

    def __init__(self, main_window, fname, delete_callback, is_video=False):
        super().__init__(main_window)
        self.main_window = main_window
        self.fname = fname
        self.delete_callback = delete_callback
        self.is_video = is_video
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        if self.is_video: self.add_play_icon()

    def add_play_icon(self):
        # Load play icon pixmap
        play_icon = QPixmap("play_icon.png")
        if play_icon.isNull():
            print("Failed to load play icon!")
        # Scale icon to fit nicely, e.g. 64x64 px
        play_icon = play_icon.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Create overlay label
        self.play_icon_label = QLabel(self)
        self.play_icon_label.setPixmap(play_icon)
        self.play_icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)  # So clicks pass through

        # Center the icon on the thumbnail
        self.play_icon_label.resize(play_icon.size())
        self.play_icon_label.move(
            (self.width() - self.play_icon_label.width()) // 2,
            (self.height() - self.play_icon_label.height()) // 2,
        )
        self.play_icon_label.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_video and hasattr(self, 'play_icon_label'):
            # Recenter play icon when resizing
            self.play_icon_label.move(
                (self.width() - self.play_icon_label.width()) // 2,
                (self.height() - self.play_icon_label.height()) // 2,
            )
            self.play_icon_label.show()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # emit clicked signal for single click select
            self.clicked.emit(self.fname)
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # emit doubleClicked signal for preview
            self.doubleClicked.emit(self.fname)
        else:
            super().mouseDoubleClickEvent(event)

    def show_context_menu(self, pos):
        globalPos = self.mapToGlobal(pos)
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        action = menu.exec_(globalPos)
        if action == delete_action:
            self.delete_callback(self.fname)



class ThumbnailLoader(QRunnable):
    #loaded = pyqtSignal(str, object)

    def __init__(self, fname, password, signals):
        super().__init__()
        self.fname = fname
        self.password = password
        self.signals = signals


    @pyqtSlot()
    def run(self):
        try:
            path = os.path.join(GALLERY_FOLDER, self.fname)
            data = decrypt_file(path, self.password)

            if is_image(data):
                pil_img = Image.open(io.BytesIO(data)).convert("RGB")
                pil_img.thumbnail((256, 256), Image.LANCZOS)
                self.signals.loaded.emit(self.fname, pil_img)
            elif is_video(self.fname):
                pil_img = generate_video_thumbnail(data)  # adapt your function accordingly
                self.signals.loaded.emit(self.fname, pil_img if pil_img else None)
            else:
                self.signals.loaded.emit(self.fname, None)
        except Exception as e:
            print(f"Error loading thumbnail for {self.fname}: {e}")
            self.signals.loaded.emit(self.fname, None)


class GalleryApp(QWidget):
    def __init__(self, password):
        super().__init__()
        self.password = password
        self.setWindowTitle("📸 Secure Gallery")
        self.layout = QVBoxLayout()
        
        self.file_count = QLabel("")

        self.import_btn = QPushButton("Import Media")
        self.import_btn.setStyleSheet("background-color: green; color: white; padding: 6px; border-radius: 4px;")
        self.export_btn = QPushButton("Export Selected")
        self.refresh_btn = QPushButton("Refresh Gallery")
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("background-color: red; color: white; padding: 6px; border-radius: 4px;")
        

        # self.list_widget = QListWidget()
        # self.list_widget.setViewMode(QListWidget.IconMode)         # Switch to grid icon mode
        # self.list_widget.setIconSize(QtCore.QSize(128, 128))       # Set icon size (adjust 128 as you want)
        # self.list_widget.setResizeMode(QListWidget.Adjust)         # Adjust layout when resizing
        # self.list_widget.setGridSize(QtCore.QSize(250, 250))       # Size of each grid cell (space for icon + text)
        # self.list_widget.setSpacing(0)                             # Space between items
        # self.list_widget.setUniformItemSizes(True)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_widget.setLayout(self.grid_layout)

        self.scroll_area.setWidget(self.grid_widget)
        self.layout.addWidget(self.scroll_area)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self.load_visible_thumbnails)
        self.thumbnails = []
        self.thumbnail_labels = {}
        self.thumbnail_threads = []
        self.selected_thumbnail = None
        self.thread_pool = QThreadPool()
        self.worker_signals = ThumbnailWorkerSignals()
        self.worker_signals.loaded.connect(self.set_thumbnail)




        #self.list_widget.itemDoubleClicked.connect(self.preview_item)
        self.gallery_list = QListWidget()

        self.import_btn.clicked.connect(self.import_media)
        self.export_btn.clicked.connect(self.export_media)
        self.refresh_btn.clicked.connect(self.load_gallery)
        #self.delete_btn.clicked.connect(self.delete_selected)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)

        #self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.file_count)

        self.import_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.export_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.load_gallery()
        self.resize(1200, 800)

    def import_media(self):
        files = choose_files()
        for file in files:
            # Get original timestamps
            stat = os.stat(file)
            atime, mtime = stat.st_atime, stat.st_mtime

            encrypt_file(file, self.password, GALLERY_FOLDER)

            # Get encrypted file path
            fname = os.path.basename(file) + ".enc"
            enc_path = os.path.join(GALLERY_FOLDER, fname)

            # Apply original timestamps to encrypted file
            os.utime(enc_path, (atime, mtime))
            self.load_gallery()

    def closeEvent(self, event):
        for thread in self.thumbnail_threads:
            thread.quit()
            thread.wait()  # Wait for the thread to finish
        event.accept()

    def load_gallery(self):
        #self.list_widget.clear()

        self.thumbnails.clear()
        self.thumbnail_labels.clear()
        # Clear old items from grid
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.thumbnail_threads = [] 

        if not os.path.exists(GALLERY_FOLDER):
            return
        
        count = 0
        row = col = 0
        for fname in os.listdir(GALLERY_FOLDER):
            if not fname.endswith(".enc"):
                continue
            count+=1
            is_vid = is_video(fname)  # Implement or use your existing video check
            label = ThumbnailLabel(self, fname, self.delete_file_by_name, is_video=is_vid)
            # Create a blank placeholder label for now
            #label = ThumbnailLabel(self, fname, self.delete_file_by_name)
            label.setFixedSize(256, 256)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: #ddd; border: 1px solid #aaa;")
            label.setText("Loading....")
            label.setToolTip(fname)
            #label.mousePressEvent = lambda e, name=fname: self.preview_item_grid(name)
            label.clicked.connect(self.on_thumbnail_clicked)
            label.doubleClicked.connect(self.on_thumbnail_double_clicked)
            self.grid_layout.addWidget(label, row, col)

            self.thumbnail_labels[fname] = label
            
            self.thumbnails.append({
                "fname": fname,
                "widget": label,
                "loaded": False
            })
            # loader.loaded.connect(self.set_thumbnail)
            # loader.start()
            # self.thumbnail_threads.append(loader)

            col += 1
            if col >= 5:  # 4 columns per row
                col = 0
                row += 1
           

                #self.grid_widget.addItem(item)
                self.file_count.setText(f"Total files: {count}")

    def set_thumbnail(self, fname, pil_image):
        label = self.thumbnail_labels.get(fname)
        if not label:
            return
        if pil_image is None:
            label.setText("No preview")
            return

        qimage = QImage(
            pil_image.tobytes(),
            pil_image.width,
            pil_image.height,
            pil_image.width * 3,
            QImage.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimage).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        label.setText("")  # Clear any previous text


    def load_visible_thumbnails(self):
        viewport_top = self.scroll_area.verticalScrollBar().value()
        viewport_height = self.scroll_area.viewport().height()

        for thumb in self.thumbnails:
            widget = thumb["widget"]
            widget_y = widget.pos().y()

            if thumb["loaded"]:
                continue

            if widget_y + widget.height() >= viewport_top and widget_y <= viewport_top + viewport_height:
                self.load_thumbnail_image(thumb)
    
    def load_thumbnail_image(self, thumb):
        fname = thumb["fname"]
        label = thumb["widget"]

        signals = ThumbnailWorkerSignals()
        signals.loaded.connect(self.set_thumbnail_callback(fname, thumb))

        worker = ThumbnailLoader(fname, self.password, signals)
        self.thread_pool.start(worker)

    def set_thumbnail_callback(self, fname, thumb_ref):
        def callback(_, pil_image):
            label = self.thumbnail_labels.get(fname)
            if not label:
                return
            if pil_image is None:
                label.setText("No preview")
                return
            qimage = QImage(
                pil_image.tobytes(),
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qimage).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setText("")
            thumb_ref["loaded"] = True
        return callback


    def on_thumbnail_clicked(self, fname):
        # When a thumbnail is single clicked, mark it as selected
        # Clear previous selection (optional, depends on your UI)
        if hasattr(self, 'selected_thumbnail') and self.selected_thumbnail:
            prev_label = self.thumbnail_labels.get(self.selected_thumbnail)
            if prev_label:
                prev_label.setStyleSheet("background-color: #ddd; border: 1px solid #aaa;")  # un-highlight previous

        self.selected_thumbnail = fname
        label = self.thumbnail_labels.get(fname)
        if label:
            label.setStyleSheet("background-color: #aaf; border: 2px solid #55f;")  # highlight selected

    def on_thumbnail_double_clicked(self, fname):
        self.preview_item_grid(fname)


    def export_media(self):
        if not hasattr(self, 'selected_thumbnail') or not self.selected_thumbnail:
            QMessageBox.warning(self, "No Selection", "Please select a file to export.")
            return

        fname = self.selected_thumbnail
        path = os.path.join(GALLERY_FOLDER, fname)
        data = decrypt_file(path, self.password)
        export_path = choose_export_location(fname.replace(".enc", ""))

        if export_path:
            with open(export_path, "wb") as f:
                f.write(data)

            # Apply original timestamps from encrypted file to exported file
            stat = os.stat(path)
            os.utime(export_path, (stat.st_atime, stat.st_mtime))
            # Set Windows creation time
            set_file_creation_time_windows(export_path, stat.st_ctime)
            QMessageBox.information(self, "Exported", "File exported successfully.")
   
    def preview_item(self, item):
        from file_utils import is_image, is_video
        from encryption import decrypt_file, generate_thumbnail

        fname = item.data(Qt.UserRole)
        self.preview_item_grid(fname)
        path = os.path.join(GALLERY_FOLDER, fname)
        data = decrypt_file(path, self.password)

        if is_image(data):
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(data))
                img = img.convert("RGB")
                img.load()

                width, height = img.size
                img_data = img.tobytes()
                qimage = QImage(img_data, width, height, width * 3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)

                # Create dialog
                dlg = QDialog(self)
                dlg.setWindowTitle(fname)
                dlg.resize(800, 600)
                dlg.setMinimumSize(400, 300)

                # Scroll area to hold the image
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)

                # Image label
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setPixmap(pixmap)
                scroll_area.setWidget(label)

                # Update image size on resize
                def resizeEvent(event):
                    scaled = pixmap.scaled(
                        scroll_area.viewport().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    label.setPixmap(scaled)

                dlg.resizeEvent = resizeEvent

                # Layout
                layout = QVBoxLayout()
                layout.addWidget(scroll_area)
                dlg.setLayout(layout)

                dlg.exec_()

            except Exception as e:
                import traceback
                print(traceback.format_exc())
                QMessageBox.warning(self, "Image Load Error", f"Failed to load image: {e}")        

        elif is_video(data):
        # Save to temp and open with system default player
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            subprocess.Popen([tmp_path], shell=True)
        else:
            QMessageBox.warning(self, "Unknown Format", "Can't preview this file.")

    def preview_item_grid(self, fname):
        from file_utils import is_image, is_video
        from encryption import decrypt_file

        path = os.path.join(GALLERY_FOLDER, fname)
        data = decrypt_file(path, self.password)

        if is_image(data):
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(data))
                img = img.convert("RGB")
                img.load()

                width, height = img.size
                img_data = img.tobytes()
                qimage = QImage(img_data, width, height, width * 3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)

                dlg = QDialog(self)
                dlg.setWindowTitle(fname)
                dlg.resize(800, 600)
                dlg.setMinimumSize(400, 300)
                dlg.setWindowFlags(Qt.Window)


                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)

                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setPixmap(pixmap)
                scroll_area.setWidget(label)
                

                def resizeEvent(event):
                    scaled = pixmap.scaled(
                        scroll_area.viewport().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    label.setPixmap(scaled)

                dlg.resizeEvent = resizeEvent

                layout = QVBoxLayout()
                layout.addWidget(scroll_area)
                dlg.setLayout(layout)

                dlg.exec_()

            except Exception as e:
                import traceback
                print(traceback.format_exc())
                QMessageBox.warning(self, "Image Load Error", f"Failed to load image: {e}")

        elif is_video(data):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            subprocess.Popen([tmp_path], shell=True)

        else:
            QMessageBox.warning(self, "Unknown Format", "Can't preview this file.")

    def delete_file_by_name(self, fname):
    
        path = os.path.join(GALLERY_FOLDER, fname)

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete '{fname}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                os.remove(path)
                QMessageBox.information(self, "Deleted", f"'{fname}' was deleted.")
                self.load_gallery()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file:\n{e}")
   


if __name__ == "__main__":
    os.makedirs(GALLERY_FOLDER, exist_ok=True)
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
