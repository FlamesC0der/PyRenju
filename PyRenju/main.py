import sys
import sqlite3
import ast
import random
import json

from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QDialog, QLabel, QVBoxLayout
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal

from components.ToggleButton import ToggleButton

from PyRenju.ui.ui import Ui_MainWindow, Ui_AboutPage, Ui_Settings

SIZE = 15


class AboutPage(QWidget, Ui_AboutPage):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class SettingsPage(QWidget, Ui_Settings):
    update_settings = pyqtSignal(str, bool)

    def __init__(self, settings_data):
        super().__init__()
        self.setupUi(self)
        self.settings_data = settings_data
        self.init_ui()

    def init_ui(self):
        Toggle_Bot = ToggleButton(50, 40, self.settings_data['bot'])
        Toggle_Bot.clicked.connect(self.bot)
        self.setting.addWidget(Toggle_Bot)

        Toggle_BotV2 = ToggleButton(50, 40, self.settings_data['botV2'])
        Toggle_BotV2.clicked.connect(self.botV2)
        self.setting2.addWidget(Toggle_BotV2)

    def bot(self, on_off):
        self.update_settings.emit('bot', on_off)

    def botV2(self, on_off):
        self.update_settings.emit('botV2', on_off)


class PyRenju(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(750, 600)

        # Settings
        with open('settings.json') as f:
            self.settings = json.load(f)

        self.boardmtrx = [['' for _ in range(SIZE)] for _ in range(SIZE)]
        self.turn = False
        self.move = 1

        self.conn = sqlite3.connect("history.db")
        self.cur = self.conn.cursor()

        self.init_ui()
        self.load_db()

    def init_ui(self):
        # Menu
        menu = self.menuBar()
        # Enable the menu bar as a custom widget on macOS
        if sys.platform == 'darwin':
            menu.setNativeMenuBar(False)

        about_action = QAction(QIcon('icons/menubar/info.png'), "&About", self)
        about_action.triggered.connect(self.openAboutPage)

        settings_action = QAction(QIcon('icons/menubar/settings.png'), "&Settings", self)
        settings_action.triggered.connect(self.openSettingsPage)

        play_again_action = QAction(QIcon('icons/menubar/replay.png'), "&Play Again", self)
        play_again_action.triggered.connect(self.replay_menu)

        game_menu = menu.addMenu("&Game")
        game_menu.addAction(about_action)
        game_menu.addSeparator()
        game_menu.addAction(settings_action)
        game_menu.addSeparator()
        game_menu.addAction(play_again_action)

        self.Turn.setPixmap(QIcon('icons/stones/black.svg').pixmap(30, 30))
        if self.settings['bot']:
            self.Bot.setPixmap(QIcon('icons/on.png').pixmap(30, 30))
        else:
            self.Bot.setPixmap(QIcon('icons/off.png').pixmap(30, 30))
        self.render_board()

    # Pages

    def openAboutPage(self):
        self.about_page = AboutPage()
        self.about_page.show()

    def openSettingsPage(self):
        self.settings_page = SettingsPage(self.settings)

        self.settings_page.update_settings.connect(self.update_settings)
        self.settings_page.show()

    def update_settings(self, type, data):
        self.settings[type] = data
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
        if self.settings['bot']:
            self.Bot.setPixmap(QIcon('icons/on.png').pixmap(30, 30))
        else:
            self.Bot.setPixmap(QIcon('icons/off.png').pixmap(30, 30))

    # Board

    def render_board(self):
        # Clear board
        for i in reversed(range(self.Board.count())):
            self.Board.itemAt(i).widget().setParent(None)

        for i in range(SIZE):
            for j in range(SIZE):
                button = QPushButton('')
                button.setFixedSize(40, 40)

                button.i = i
                button.j = j

                button.clicked.connect(self.handle_place)

                if self.boardmtrx[i][j] == 'w':
                    button.setIcon(QIcon('icons/stones/white.svg'))
                    button.setStyleSheet("background-color: #545454;")
                elif self.boardmtrx[i][j] == 'b':
                    button.setIcon(QIcon('icons/stones/black.svg'))
                    button.setStyleSheet("background-color: #545454;")
                button.setStyleSheet("border: 1px solid #5e5e5e;")

                self.Board.addWidget(button, i, j)

    def handle_place(self):
        button = self.sender()
        i, j = button.i, button.j
        if not self.boardmtrx[i][j]:
            if self.turn:
                self.boardmtrx[i][j] = 'w'
                self.Turn.setPixmap(QIcon('icons/stones/black.svg').pixmap(30, 30))
            else:
                self.boardmtrx[i][j] = 'b'
                self.Turn.setPixmap(QIcon('icons/stones/white.svg').pixmap(30, 30))
            self.turn = not self.turn
            self.move += 1
            self.save_db()
            self.render_board()
            winner = self.check_winner(self.boardmtrx)
            if winner:
                self.replay_menu(winner=winner)
                return
        if self.settings['bot'] and self.turn:
            if self.settings['botV2']:
                self.bot_place2()
            else:
                self.bot_place1()
            self.turn = not self.turn
            self.render_board()
            winner = self.check_winner(self.boardmtrx)
            if winner:
                self.replay_menu(winner=winner)

    def save_db(self):
        self.cur.execute("CREATE TABLE IF NOT EXISTS Matrix (matrix TEXT, move INTEGER)")

        self.cur.execute(f"INSERT INTO Matrix VALUES (?, ?)", (str(self.boardmtrx), self.move))
        self.conn.commit()

        self.load_db()

    def load_db(self):
        self.cur.execute("CREATE TABLE IF NOT EXISTS Matrix (matrix TEXT, move INTEGER)")
        self.conn.commit()
        self.move = len(list(self.cur.execute("SELECT * FROM Matrix").fetchall()))
        data = list(self.cur.execute("SELECT * FROM Matrix").fetchall())

        if data:
            self.boardmtrx = ast.literal_eval(data[-1][0])
        else:
            self.reset()

        for i in reversed(range(self.history.count())):
            self.history.itemAt(i).widget().setParent(None)

        for i in range(len(data)):
            history_button = QPushButton(f'Move #{i + 1}')

            history_button.setStyleSheet("background-color: 413f4d;")
            history_button.value = ast.literal_eval(data[i][0])
            history_button.move = data[i][1]
            history_button.clicked.connect(self.set_move)

            self.history.addWidget(history_button)

        self.render_board()

    def set_move(self):
        history_button = self.sender()
        self.boardmtrx = history_button.value
        self.move = history_button.move
        self.cur.execute(f'DELETE FROM matrix WHERE move > {self.move}')
        self.conn.commit()
        self.render_board()

    def check_winner(self, board):
        def find_winner(matrix):
            height = len(matrix)
            width = len(matrix[0])

            # Проверка по вертикали
            for i in range(height - 4):
                for j in range(width):
                    symbol = matrix[i][j]

                    if symbol == matrix[i + 1][j] == matrix[i + 2][j] == matrix[i + 3][j] == matrix[i + 4][j]:
                        if symbol in ('w', 'b'):
                            return symbol

            # Проверка по горизонтали
            for i in range(height):
                for j in range(width - 4):
                    symbol = matrix[i][j]

                    if symbol == matrix[i][j + 1] == matrix[i][j + 2] == matrix[i][j + 3] == matrix[i][j + 4]:
                        if symbol in ('w', 'b'):
                            return symbol

            # Проверка по диагонали '/'
            for i in range(height - 4):
                for j in range(width - 4):
                    symbol = matrix[i][j]

                    if symbol == matrix[i + 1][j + 1] == matrix[i + 2][j + 2] == matrix[i + 3][j + 3] == \
                            matrix[i + 4][
                                j + 4]:
                        if symbol in ('w', 'b'):
                            return symbol

            # Проверка по диагонали '\'
            for i in range(height - 4):
                for j in range(4, width):
                    symbol = matrix[i][j]

                    if symbol == matrix[i + 1][j - 1] == matrix[i + 2][j - 2] == matrix[i + 3][j - 3] == \
                            matrix[i + 4][
                                j - 4]:
                        if symbol in ('w', 'b'):
                            return symbol

            # Если нет победителя
            return None

        winner = find_winner(board)
        return winner

    def replay_menu(self, winner):
        self.replaymenu = QDialog(self)
        self.replaymenu.setGeometry(500, 400, 450, 100)
        self.replaymenu.setWindowTitle("連珠 Menu")

        layout = QVBoxLayout()

        label = QLabel(f"{winner} win!")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px;")

        layout.addWidget(label)

        play_again_button = QPushButton("Play again")
        play_again_button.setIcon(QIcon('icons/play.png'))
        play_again_button.setIconSize(QtCore.QSize(30, 30))
        play_again_button.clicked.connect(self.replay)
        play_again_button.setStyleSheet("background-color: #413f4d; font-size: 20px;")
        layout.addWidget(play_again_button)
        self.replaymenu.setLayout(layout)
        self.replaymenu.exec()

    def replay(self):
        self.reset()
        self.render_board()
        self.replaymenu.hide()

    def reset(self):
        self.boardmtrx = [['' for _ in range(SIZE)] for _ in range(SIZE)]
        self.turn = False
        self.cur.execute("DELETE FROM matrix")
        self.conn.commit()
        self.Turn.setPixmap(QIcon('icons/stones/black.svg').pixmap(30, 30))

        for i in reversed(range(self.history.count())):
            self.history.itemAt(i).widget().setParent(None)

    # Bot V1

    def bot_place1(self):
        empty_cells = self.get_empty_cells()

        for x, y in empty_cells:
            # Check bot
            self.boardmtrx[x][y] = "w"
            if self.check_winner(self.boardmtrx):
                self.boardmtrx[x][y] = "w"
                return
            self.boardmtrx[x][y] = ""

            # Check player
            self.boardmtrx[x][y] = "b"
            if self.check_winner(self.boardmtrx):
                self.boardmtrx[x][y] = "w"
                return
            self.boardmtrx[x][y] = ""

        # random place

        if empty_cells:
            x, y = random.choice(empty_cells)
            self.boardmtrx[x][y] = "w"

    def get_empty_cells(self):
        empty_cells = []
        for x in range(SIZE):
            for y in range(SIZE):
                if self.boardmtrx[x][y] == '':
                    empty_cells.append((x, y))
        return empty_cells

    # Bot V2

    def bot_place2(self):
        best_move1, best_move2 = self.minimax(1, True)
        print(f'Bot move: Score - {best_move1}; coords - {best_move2}')
        self.boardmtrx[best_move2[0]][best_move2[1]] = 'w'

    def minimax(self, depth, is_maximizing):
        if depth == 0 or self.check_winner(self.boardmtrx):
            return self.evaluate(), None

        if is_maximizing:
            best_score = -float('inf')
            best_move = None
            for row in range(len(self.boardmtrx)):
                for col in range(len(self.boardmtrx[row])):
                    if self.boardmtrx[row][col] == '':
                        self.boardmtrx[row][col] = 'w'
                        score, _ = self.minimax(depth - 1, False)
                        self.boardmtrx[row][col] = ''
                        if score > best_score:
                            best_score = score
                            best_move = (row, col)
            return best_score, best_move
        else:
            best_score = float('inf')
            best_move = None
            for row in range(len(self.boardmtrx)):
                for col in range(len(self.boardmtrx[row])):
                    if self.boardmtrx[row][col] == '':
                        self.boardmtrx[row][col] = 'b'
                        score, _ = self.minimax(depth - 1, True)
                        self.boardmtrx[row][col] = ''
                        if score < best_score:
                            best_score = score
                            best_move = (row, col)
            return best_score, best_move

    def evaluate(self):
        score = 0

        # Проверка по вертикали и горизонтали
        for i in range(len(self.boardmtrx)):
            for j in range(len(self.boardmtrx[i]) - 3):
                mx = 5
                if j <= 10:
                    mx = 6
                for le in range(1, mx):
                    row_sequence = self.boardmtrx[i][j:j + le]
                    col_sequence = [self.boardmtrx[j][i] for j in range(j, j + le)]

                    if row_sequence == ['w' * le] or col_sequence == ['w' * le]:
                        score += 100 * le
                    elif row_sequence == ['b' * le] or col_sequence == ['b' * le]:
                        score -= 100 * le

        # Проверка по диагоналям
        for i in range(len(self.boardmtrx) - 3):
            for j in range(len(self.boardmtrx[i]) - 3):
                for le in range(1, 5):
                    diagonal_sequence_1 = [self.boardmtrx[i + k][j + k] for k in range(le)]
                    diagonal_sequence_2 = [self.boardmtrx[i + k][j + 3 - k] for k in range(le)]

                    if diagonal_sequence_1 == ['w' * le] or diagonal_sequence_2 == ['w' * le]:
                        score += 100 * le
                    elif diagonal_sequence_1 == ['b' * le] or diagonal_sequence_2 == ['b' * le]:
                        score -= 100 * le

        return score


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = PyRenju()
    ex.show()
    sys.exit(app.exec())
