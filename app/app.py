import sys

import numpy as np
import pandas as pd
from PIL import Image, ImageQt

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *


class Window(QMainWindow):
    def __init__(self, model):
        super().__init__()

        # Общий вид приложения
        self.setWindowTitle("Smart Desk")
        self.setGeometry(0, 0, 780, 630)
        self.background = QImage(self.size(), QImage.Format.Format_RGB32)
        self.background.fill(QColor(250, 255, 253, 255))

        self.image = QImage(QSize(self.size().height() - 70, self.size().height() - 70), QImage.Format.Format_RGB32)
        self.image.fill(QColor(255, 255, 255))

        # Предсказание
        self.model = model

        self.probs = np.zeros(10)
        self.digit_prob_col = []
        for i in range(10):
            digit_prob = QLineEdit(f'{i}: {self.probs[i] * 100:.2f}%', self)
            digit_prob.setReadOnly(True)
            digit_prob.move((self.size().width() + self.size().height() - 50) // 2 - 50,
                            (self.size().height() - 220) * i / 9 + 115)
            digit_prob.setStyleSheet("background-color: rgba(0, 0, 0, 0); "
                                     "color: rgb(0, 0, 0);"
                                     "border: none;"
                                     "font-size: 20px")
            self.digit_prob_col.append(digit_prob)

        # Анимация подсчета вероятностей
        self.start_anim = False
        self.anim_phase = 0

        timer = QTimer(self)
        timer.timeout.connect(self.percentage_animation)
        timer.start(10)

        # Задание параметров рисования
        self.drawing = False
        self.brushSize = 32
        self.brushColor = QColor(0, 0, 0)
        self.lastPoint = QPoint()

        # Навигационная панель
        mainMenu = self.menuBar()
        mainMenu.setStyleSheet("background-color: rgb(255, 255, 255); "
                               "color: rgb(0, 0, 0);"
                               "border-bottom: 1px solid rgb(0, 0, 0);")

        fileMenu = mainMenu.addMenu("File")

        saveAction = QAction("Save", self)
        saveAction.setShortcut("Ctrl+S")
        fileMenu.addAction(saveAction)
        saveAction.triggered.connect(self.save)

        clearAction = QAction("Clear", self)
        clearAction.setShortcut("Ctrl+X")
        fileMenu.addAction(clearAction)
        clearAction.triggered.connect(self.clear)

        exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        exitAct.setShortcut('Esc')
        fileMenu.addAction(exitAct)
        exitAct.triggered.connect(QCoreApplication.quit)

        toolMenu = mainMenu.addMenu("Tools")

        drawAction = QAction("Drawer", self)
        drawAction.setShortcut("Ctrl+D")
        toolMenu.addAction(drawAction)
        drawAction.triggered.connect(self.drawer)

        eraseAction = QAction("Eraser", self)
        eraseAction.setShortcut("Ctrl+E")
        toolMenu.addAction(eraseAction)
        eraseAction.triggered.connect(self.eraser)

        brsMenu = mainMenu.addMenu('BrushSize')

        BrushSize24 = QAction('24px', self)
        brsMenu.addAction(BrushSize24)
        BrushSize24.triggered.connect(self.changeSize24)

        BrushSize32 = QAction('32px(Recommended)', self)
        brsMenu.addAction(BrushSize32)
        BrushSize32.triggered.connect(self.changeSize32)

        BrushSize40 = QAction('40px', self)
        brsMenu.addAction(BrushSize40)
        BrushSize40.triggered.connect(self.changeSize40)

    def paintEvent(self, event):
        canvasPainter = QPainter(self)

        canvasPainter.drawImage(self.rect(), self.background, self.background.rect())
        canvasPainter.drawImage(20, 55, self.image)

        canvasPainter.setPen(QPen(QColor(0, 0, 0), 1))
        canvasPainter.drawRect(20, 55, self.size().height() - 70, self.size().height() - 70)

    def mousePressEvent(self, event):
        """Проверяем, внутри ли нашей доски курсор"""
        if (event.button() == Qt.MouseButton.LeftButton and
                20 + self.brushSize // 2 <= event.pos().x() <= self.size().height() - 50 - self.brushSize // 2 and
                55 + self.brushSize // 2 <= event.pos().y() <= self.size().height() - 15 - self.brushSize // 2):
            self.drawing = True
            self.lastPoint = QPoint(event.pos().x() - 20, event.pos().y() - 55)

    def mouseMoveEvent(self, event):
        """Непосредственно рисуем"""
        if event.buttons() and Qt.MouseButton.LeftButton and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(QPen(self.brushColor, self.brushSize,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

            x_pos = max(self.brushSize // 2,
                        min(event.pos().x() - 20, self.size().height() - 70 - self.brushSize // 2))
            y_pos = max(self.brushSize // 2,
                        min(event.pos().y() - 55, self.size().height() - 70 - self.brushSize // 2))
            total_pos = QPoint(x_pos, y_pos)

            painter.drawLine(self.lastPoint, total_pos)

            self.lastPoint = total_pos
            self.update()

    def mouseReleaseEvent(self, event):
        """Как только юзер отпускает кнопку мыши, модель останавливает режим рисования и конвертирует изображение в
        табличный вид, на основе которого модель делает свое предсказание"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            real_im = ImageQt.fromqimage(self.image)
            real_im = real_im.resize((28, 28))
            real_px = real_im.load()

            vert_line, horiz_line = [27, 0], [27, 0]
            for x in range(real_im.size[0]):
                for y in range(real_im.size[1]):
                    horiz_line = [min(x, horiz_line[0]), max(x, horiz_line[1])] if real_px[x, y][0] != 255 \
                        else horiz_line
                    vert_line = [min(y, vert_line[0]), max(y, vert_line[1])] if real_px[x, y][0] != 255 \
                        else vert_line

            if vert_line != [27, 0] or horiz_line != [27, 0]:
                new_im = Image.new("RGBA", (28, 28), "#fff")
                paste_im = real_im.crop((horiz_line[0], vert_line[0], horiz_line[1], vert_line[1]))
                start_coord = (28 - (horiz_line[1] - horiz_line[0])) // 2, (28 - (vert_line[1] - vert_line[0])) // 2
                new_im.paste(paste_im, start_coord)
            else:
                for i in range(10):
                    self.digit_prob_col[i].setStyleSheet("background-color: rgba(0, 0, 0, 0); "
                                                         "color: rgb(0, 0, 0);"
                                                         "border: none;"
                                                         "font-size: 20px")
                return

            new_px = new_im.load()
            item = {}
            for x in range(new_im.size[0]):
                for y in range(new_im.size[1]):
                    if f'{x}_{y}' in item.keys():
                        item[f'{x}_{y}'].append(1 - new_px[x, y][0] / 255)
                    else:
                        item[f'{x}_{y}'] = [1 - new_px[x, y][0] / 255]

            im_data = pd.DataFrame(item)

            self.probs = self.model.predict_proba(im_data)[0] / 10
            digit = np.argmax(self.probs)
            for i in range(10):
                if i != digit:
                    self.digit_prob_col[i].setStyleSheet("background-color: rgba(0, 0, 0, 0); "
                                                         "color: rgb(0, 0, 0);"
                                                         "border: none;"
                                                         "font-size: 20px")
                else:
                    self.digit_prob_col[i].setStyleSheet("background-color: rgba(0, 0, 0, 0);"
                                                         "color: rgb(47, 145, 75);"
                                                         'border: none;'
                                                         "border-bottom: 1px solid rgb(47, 145, 75);"
                                                         "font-size: 20px;")
            self.start_anim = True

    def percentage_animation(self):
        if self.start_anim:
            self.anim_phase += 1
            for i in range(10):
                self.digit_prob_col[i].setText(f'{i}: {self.probs[i] * self.anim_phase * 100:.2f}%')

            if self.anim_phase == 10:
                self.start_anim = False
                self.anim_phase = 0
                self.probs = self.probs * 10

    def clear(self):
        self.image.fill(QColor(255, 255, 255))
        self.update()

        for i in range(10):
            self.digit_prob_col[i].setText(f'{i}: 0.00%')
            self.digit_prob_col[i].setStyleSheet("background-color: rgba(0, 0, 0, 0); "
                                                 "color: rgb(0, 0, 0);"
                                                 "border: none;"
                                                 "font-size: 20px")

    def save(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                                  "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")

        if filePath == "":
            return
        self.image.save(filePath)

    # Методы ниже - методы для работы с кистью
    def drawer(self):
        self.brushColor = QColor(0, 0, 0)

    def eraser(self):
        self.brushColor = QColor(255, 255, 255)

    def changeSize24(self):
        self.brushSize = 24

    def changeSize32(self):
        self.brushSize = 32

    def changeSize40(self):
        self.brushSize = 40


def launch_app(model):
    App = QApplication(sys.argv)
    window = Window(model)
    window.setFixedSize(780, 630)
    window.show()
    sys.exit(App.exec())
