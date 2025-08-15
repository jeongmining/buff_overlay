import sys
from PySide6 import QtCore, QtGui, QtWidgets

HANDLE_SIZE = 10
GRIP_SIZE = 14
MIN_W, MIN_H = 180, 120
RESIZE_MARGIN = 14

OUTLINE_COLOR = QtGui.QColor(0, 170, 255, 180)
OUTLINE_HL_COLOR = QtGui.QColor(255, 255, 255, 220)
OUTLINE_WIDTH = 2
OUTLINE_RADIUS = 8


class ResizableRectWidget(QtWidgets.QWidget):
    moved = QtCore.Signal()
    resized = QtCore.Signal()

    def __init__(self, parent=None, rect=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._pen = QtGui.QPen(QtGui.QColor(0, 153, 255), 2)
        self._brush = QtGui.QBrush(QtGui.QColor(0, 153, 255, 40))

        self._dragging = False
        self._resizing = False
        self._active_handle = None
        self._start_pos = QtCore.QPoint()
        self._start_geom = QtCore.QRect()

        if rect is None:
            rect = QtCore.QRect(200, 200, 480, 320)
        self.setGeometry(rect)
        self._handles = self._calc_handles()

    def _calc_handles(self):
        r = self.rect()
        s = HANDLE_SIZE
        return {
            "tl": QtCore.QRect(r.left()-s//2, r.top()-s//2, s, s),
            "tm": QtCore.QRect(r.center().x()-s//2, r.top()-s//2, s, s),
            "tr": QtCore.QRect(r.right()-s//2, r.top()-s//2, s, s),
            "ml": QtCore.QRect(r.left()-s//2, r.center().y()-s//2, s, s),
            "mr": QtCore.QRect(r.right()-s//2, r.center().y()-s//2, s, s),
            "bl": QtCore.QRect(r.left()-s//2, r.bottom()-s//2, s, s),
            "bm": QtCore.QRect(r.center().x()-s//2, r.bottom()-s//2, s, s),
            "br": QtCore.QRect(r.right()-s//2, r.bottom()-s//2, s, s),
        }

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self._pen)
        p.setBrush(self._brush)
        p.drawRect(self.rect())
        p.setBrush(QtGui.QBrush(QtGui.QColor(0, 153, 255)))
        p.setPen(QtCore.Qt.NoPen)
        for r in self._handles.values():
            p.drawRect(r)

    def _hit_test(self, pos):
        for name, r in self._handles.items():
            if r.contains(pos):
                return name
        if self.rect().adjusted(HANDLE_SIZE, HANDLE_SIZE, -HANDLE_SIZE, -HANDLE_SIZE).contains(pos):
            return "move"
        return None

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._active_handle = self._hit_test(e.position().toPoint())
            self._start_pos = e.globalPosition().toPoint()
            self._start_geom = self.geometry()
            if self._active_handle == "move":
                self._dragging = True
            elif self._active_handle is not None:
                self._resizing = True
            self.grabKeyboard()
            e.accept()
        else:
            e.ignore()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        pos = e.position().toPoint()
        hit = self._hit_test(pos)
        cursor_map = {
            "tl": QtCore.Qt.SizeFDiagCursor, "br": QtCore.Qt.SizeFDiagCursor,
            "tr": QtCore.Qt.SizeBDiagCursor, "bl": QtCore.Qt.SizeBDiagCursor,
            "ml": QtCore.Qt.SizeHorCursor, "mr": QtCore.Qt.SizeHorCursor,
            "tm": QtCore.Qt.SizeVerCursor, "bm": QtCore.Qt.SizeVerCursor,
            "move": QtCore.Qt.SizeAllCursor, None: QtCore.Qt.ArrowCursor
        }
        self.setCursor(cursor_map.get(hit, QtCore.Qt.ArrowCursor))

        if self._dragging or self._resizing:
            delta = e.globalPosition().toPoint() - self._start_pos
            g = QtCore.QRect(self._start_geom)
            if self._dragging:
                g.moveTo(self._start_geom.topLeft() + delta)
                self.setGeometry(g)
                self.moved.emit()
            else:
                minw, minh = 20, 20
                if self._active_handle in ("tl", "ml", "bl"):
                    new_left = g.left() + delta.x()
                    if g.right() - new_left < minw:
                        new_left = g.right() - minw
                    g.setLeft(new_left)
                if self._active_handle in ("tr", "mr", "br"):
                    new_right = g.right() + delta.x()
                    if new_right - g.left() < minw:
                        new_right = g.left() + minw
                    g.setRight(new_right)
                if self._active_handle in ("tl", "tm", "tr"):
                    new_top = g.top() + delta.y()
                    if g.bottom() - new_top < minh:
                        new_top = g.bottom() - minh
                    g.setTop(new_top)
                if self._active_handle in ("bl", "bm", "br"):
                    new_bottom = g.bottom() + delta.y()
                    if new_bottom - g.top() < minh:
                        new_bottom = g.top() + minh
                    g.setBottom(new_bottom)
                self.setGeometry(g)
                self.resized.emit()

            self._handles = self._calc_handles()
            self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._dragging = False
            self._resizing = False
            self._active_handle = None
            self.releaseKeyboard()
            e.accept()
        else:
            e.ignore()

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key_R:
            win = self.window()
            if isinstance(win, SelectionOverlay):
                win.finish()
                e.accept()
                return
        super().keyPressEvent(e)


class SelectionOverlay(QtWidgets.QWidget):
    finished = QtCore.Signal(QtCore.QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowStaysOnTopHint
                            | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        geo = QtGui.QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)

        self._shade_color = QtGui.QColor(0, 0, 0, 80)

        center_rect = QtCore.QRect(geo.center().x()-240, geo.center().y()-160, 480, 320)
        self.rect_widget = ResizableRectWidget(self, center_rect)
        self.rect_widget.show()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), self._shade_color)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        p.fillRect(self.rect_widget.geometry(), QtCore.Qt.transparent)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

    def current_global_rect(self) -> QtCore.QRect:
        return self.rect_widget.geometry()

    def finish(self):
        self.finished.emit(self.current_global_rect())
        self.close()


class PreviewWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self._grab_rect = None
        self._last_pix = None
        self._has_frame = False

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._update_frame)

    def set_region(self, rect: QtCore.QRect):
        self._grab_rect = rect
        if rect is not None:
            self._timer.start()
        else:
            self._timer.stop()
            self._has_frame = False
            self._last_pix = None
            self.update()

    def _update_frame(self):
        if not self._grab_rect or self._grab_rect.isEmpty():
            return
        screen = QtGui.QGuiApplication.primaryScreen()
        pix = screen.grabWindow(0,
                                self._grab_rect.x(), self._grab_rect.y(),
                                self._grab_rect.width(), self._grab_rect.height())
        if pix.isNull():
            return
        self._last_pix = pix
        self._has_frame = True
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        rect_t = self.rect()
        if self._has_frame and self._last_pix is not None and not self._last_pix.isNull():
            pw, ph = self._last_pix.width(), self._last_pix.height()
            tw, th = max(1, rect_t.width()), max(1, rect_t.height())
            ar_t = tw / th
            ar_s = pw / ph
            if ar_s > ar_t:
                new_sw = int(ph * ar_t)
                sx = (pw - new_sw) // 2
                src = QtCore.QRect(sx, 0, new_sw, ph)
            else:
                new_sh = int(pw / ar_t)
                sy = (ph - new_sh) // 2
                src = QtCore.QRect(0, sy, pw, new_sh)
            p.drawPixmap(rect_t, self._last_pix, src)
        else:
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 2, QtCore.Qt.DotLine)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRoundedRect(rect_t.adjusted(2, 2, -2, -2), 10, 10)
            hint = "R: 영역 선택 • Wheel: 투명도 • 드래그: 이동 • 엣지/코너: 리사이즈"
            metrics = QtGui.QFontMetrics(self.font())
            tw = metrics.horizontalAdvance(hint) + 20
            th = metrics.height() + 12
            bx = max(10, (rect_t.width() - tw) // 2)
            by = max(10, (rect_t.height() - th) // 2)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(0, 0, 0, 140))
            p.drawRoundedRect(QtCore.QRect(bx, by, tw, th), 8, 8)
            p.setPen(QtGui.QColor(255, 255, 255))
            p.drawText(QtCore.QRect(bx, by, tw, th), QtCore.Qt.AlignCenter, hint)


class EdgeGrip(QtWidgets.QWidget):
    def __init__(self, parent, edges):
        super().__init__(parent)
        self.edges = set(edges)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        self._start_geom = None
        self._start_pos = None
        self.setCursor(self._cursor_for_edges())

    def _cursor_for_edges(self):
        e = self.edges
        if e == {'L','T'} or e == {'R','B'}:
            return QtCore.Qt.SizeFDiagCursor
        if e == {'R','T'} or e == {'L','B'}:
            return QtCore.Qt.SizeBDiagCursor
        if e in ({'L'},{'R'}):
            return QtCore.Qt.SizeHorCursor
        if e in ({'T'},{'B'}):
            return QtCore.Qt.SizeVerCursor
        return QtCore.Qt.ArrowCursor

    def enterEvent(self, e):
        self.setStyleSheet("background: rgba(255,255,255,20);")
        parent = self.parent()
        if hasattr(parent, "_set_outline_highlight"):
            parent._set_outline_highlight(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet("background: transparent;")
        parent = self.parent()
        if hasattr(parent, "_set_outline_highlight"):
            parent._set_outline_highlight(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._start_geom = self.parent().geometry()
            self._start_pos = e.globalPosition().toPoint()
            parent = self.parent()
            if hasattr(parent, "_set_outline_highlight"):
                parent._set_outline_highlight(True)
            e.accept()
        else:
            e.ignore()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._start_geom is None:
            e.ignore()
            return
        g = QtCore.QRect(self._start_geom)
        delta = e.globalPosition().toPoint() - self._start_pos
        if 'L' in self.edges:
            new_left = g.left() + delta.x()
            if g.right() - new_left < MIN_W:
                new_left = g.right() - MIN_W
            g.setLeft(new_left)
        if 'R' in self.edges:
            new_right = g.right() + delta.x()
            if new_right - g.left() < MIN_W:
                new_right = g.left() + MIN_W
            g.setRight(new_right)
        if 'T' in self.edges:
            new_top = g.top() + delta.y()
            if g.bottom() - new_top < MIN_H:
                new_top = g.bottom() - MIN_H
            g.setTop(new_top)
        if 'B' in self.edges:
            new_bottom = g.bottom() + delta.y()
            if new_bottom - g.top() < MIN_H:
                new_bottom = g.top() + MIN_H
            g.setBottom(new_bottom)
        parent = self.parent()
        if hasattr(parent, "_enforce_aspect"):
            g = parent._enforce_aspect(g, self.edges, self._start_geom)
        parent.setGeometry(g)
        e.accept()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        self._start_geom = None
        self._start_pos = None
        parent = self.parent()
        if hasattr(parent, "_set_outline_highlight"):
            parent._set_outline_highlight(False)
        e.accept()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowStaysOnTopHint
                            | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setWindowTitle("Transparent Screen Preview (R: select, Esc: exit, Wheel: opacity)")
        self.resize(900, 600)

        self.preview = PreviewWidget()
        cw = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(cw)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.preview)
        self.setCentralWidget(cw)

        self._sc_r = QtGui.QShortcut(QtGui.QKeySequence("R"), self, activated=self._handle_r)
        self._sc_r.setContext(QtCore.Qt.ApplicationShortcut)
        QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.close)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, activated=lambda: self._set_opacity(1.0))
        QtGui.QShortcut(QtGui.QKeySequence("F12"), self, activated=self.center_on_primary)

        self._overlay = None
        self._selecting = False

        self._dragging_window = False
        self._drag_pos_global = QtCore.QPoint()

        self._opacity = 0.9
        self.setWindowOpacity(self._opacity)
        self._osd = QtWidgets.QLabel(self)
        self._osd.setStyleSheet(
            "color: white; background: rgba(0,0,0,140);"
            "padding: 6px 10px; border-radius: 8px; font-size: 14px;"
        )
        self._osd.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._osd.hide()

        self.preview.installEventFilter(self)

        self._outline_on = True
        self._outline_highlight = False

        self._aspect = None

        self._grips = {
            'L': EdgeGrip(self, {'L'}), 'R': EdgeGrip(self, {'R'}),
            'T': EdgeGrip(self, {'T'}), 'B': EdgeGrip(self, {'B'}),
            'TL': EdgeGrip(self, {'T','L'}), 'TR': EdgeGrip(self, {'T','R'}),
            'BL': EdgeGrip(self, {'B','L'}), 'BR': EdgeGrip(self, {'B','R'}),
        }
        self._layout_grips()
        for g in self._grips.values():
            g.raise_()
            g.show()

        QtCore.QTimer.singleShot(0, self.center_on_primary)
        QtCore.QTimer.singleShot(300, lambda: self._show_osd("R로 영역 선택 • 휠로 투명도 조절", 1500))

    def _set_outline_highlight(self, on: bool):
        self._outline_highlight = bool(on)
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._outline_on:
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        color = OUTLINE_HL_COLOR if self._outline_highlight else OUTLINE_COLOR
        pen = QtGui.QPen(color, OUTLINE_WIDTH)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.drawRoundedRect(r, OUTLINE_RADIUS, OUTLINE_RADIUS)

    def _handle_r(self):
        if self._overlay is not None:
            self._overlay.finish()
        else:
            self.toggle_region_select()

    def toggle_region_select(self):
        if not self._selecting:
            self._overlay = SelectionOverlay()
            self._overlay.finished.connect(self._on_region_selected)
            self._overlay.show()
            self._selecting = True
        else:
            if self._overlay is not None:
                self._overlay.finish()
            self._selecting = False

    def _on_region_selected(self, rect: QtCore.QRect):
        self.preview.set_region(rect)
        self._overlay = None
        self._selecting = False
        if rect.height() > 0:
            self._aspect = rect.width() / rect.height()
            self._resize_to_aspect(anchor='TL')

    def _resize_to_aspect(self, anchor='TL'):
        if not self._aspect:
            return
        g = QtCore.QRect(self.geometry())
        new_h = max(MIN_H, int(round(g.width() / self._aspect)))
        new_w = max(MIN_W, int(round(new_h * self._aspect)))
        if anchor in ('TL','L','T'):
            g.setWidth(new_w)
            g.setHeight(new_h)
        else:
            g.setRight(g.left() + new_w)
            g.setBottom(g.top() + new_h)
        self.setGeometry(g)

    def _enforce_aspect(self, g: QtCore.QRect, edges: set, start_geom: QtCore.QRect) -> QtCore.QRect:
        if not self._aspect:
            if g.width() < MIN_W:
                g.setWidth(MIN_W)
            if g.height() < MIN_H:
                g.setHeight(MIN_H)
            return g

        A = self._aspect
        dw = g.width() - start_geom.width()
        dh = g.height() - start_geom.height()

        if ('L' in edges or 'R' in edges) and ('T' not in edges and 'B' not in edges):
            new_h = max(MIN_H, int(round(g.width() / A)))
            if 'T' in edges and 'B' not in edges:
                g.setTop(g.bottom() - new_h)
            else:
                g.setBottom(g.top() + new_h)
        elif ('T' in edges or 'B' in edges) and ('L' not in edges and 'R' not in edges):
            new_w = max(MIN_W, int(round(g.height() * A)))
            if 'L' in edges and 'R' not in edges:
                g.setLeft(g.right() - new_w)
            else:
                g.setRight(g.left() + new_w)
        else:
            if abs(dw) >= abs(dh):
                new_h = max(MIN_H, int(round(g.width() / A)))
                if 'T' in edges and 'B' not in edges:
                    g.setTop(g.bottom() - new_h)
                else:
                    g.setBottom(g.top() + new_h)
            else:
                new_w = max(MIN_W, int(round(g.height() * A)))
                if 'L' in edges and 'R' not in edges:
                    g.setLeft(g.right() - new_w)
                else:
                    g.setRight(g.left() + new_w)

        if g.width() < MIN_W:
            g.setRight(g.left() + MIN_W)
        if g.height() < MIN_H:
            g.setBottom(g.top() + MIN_H)
        return g

    def center_on_primary(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        if not screen:
            return
        ag = screen.availableGeometry()
        w, h = self.width(), self.height()
        x = ag.x() + (ag.width() - w) // 2
        y = ag.y() + (ag.height() - h) // 2
        self.move(x, y)

    def _show_osd(self, text: str, msec=800):
        self._osd.setText(text)
        self._osd.adjustSize()
        cx = (self.width() - self._osd.width()) // 2
        cy = (self.height() - self._osd.height()) // 2
        self._osd.move(max(0, cx), max(0, cy))
        self._osd.show()
        QtCore.QTimer.singleShot(msec, self._osd.hide)

    def _set_opacity(self, value: float):
        self._opacity = max(0.2, min(1.0, value))
        self.setWindowOpacity(self._opacity)
        self._show_osd(f"Opacity: {int(self._opacity * 100)}%")

    def wheelEvent(self, e: QtGui.QWheelEvent):
        delta = e.angleDelta().y()
        step = 0.05
        if delta > 0:
            self._set_opacity(self._opacity + step)
        elif delta < 0:
            self._set_opacity(self._opacity - step)

    def eventFilter(self, obj, ev):
        if obj is self.preview:
            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
                self._dragging_window = True
                self._drag_pos_global = ev.globalPosition().toPoint()
                ev.accept()
                return True
            if ev.type() == QtCore.QEvent.MouseMove and self._dragging_window:
                delta = ev.globalPosition().toPoint() - self._drag_pos_global
                self.move(self.pos() + delta)
                self._drag_pos_global = ev.globalPosition().toPoint()
                ev.accept()
                return True
            if ev.type() == QtCore.QEvent.MouseButtonRelease and ev.button() == QtCore.Qt.LeftButton:
                self._dragging_window = False
                ev.accept()
                return True
            if ev.type() == QtCore.QEvent.Wheel:
                self.wheelEvent(ev)
                return True
        return super().eventFilter(obj, ev)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        step = 20 if not (e.modifiers() & QtCore.Qt.ShiftModifier) else 80
        g = QtCore.QRect(self.geometry())
        handled = False
        if e.key() == QtCore.Qt.Key_Left:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                g.setRight(g.right() - step)
                handled = True
            else:
                g.moveLeft(g.left() - step)
                handled = True
        elif e.key() == QtCore.Qt.Key_Right:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                g.setRight(g.right() + step)
                handled = True
            else:
                g.moveLeft(g.left() + step)
                handled = True
        elif e.key() == QtCore.Qt.Key_Up:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                g.setBottom(g.bottom() - step)
                handled = True
            else:
                g.moveTop(g.top() - step)
                handled = True
        elif e.key() == QtCore.Qt.Key_Down:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                g.setBottom(g.bottom() + step)
                handled = True
            else:
                g.moveTop(g.top() + step)
                handled = True

        if handled:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                g = self._enforce_aspect(g, {'B','R'}, self.geometry())
            if g.width() < MIN_W:
                g.setRight(g.left() + MIN_W)
            if g.height() < MIN_H:
                g.setBottom(g.top() + MIN_H)
            self.setGeometry(g)
            e.accept()
        else:
            super().keyPressEvent(e)

    def _layout_grips(self):
        w, h = self.width(), self.height()
        s = GRIP_SIZE
        self._grips['TL'].setGeometry(0, 0, s, s)
        self._grips['TR'].setGeometry(w - s, 0, s, s)
        self._grips['BL'].setGeometry(0, h - s, s, s)
        self._grips['BR'].setGeometry(w - s, h - s, s, s)
        self._grips['L'].setGeometry(0, s, s, h - 2*s)
        self._grips['R'].setGeometry(w - s, s, s, h - 2*s)
        self._grips['T'].setGeometry(s, 0, w - 2*s, s)
        self._grips['B'].setGeometry(s, h - s, w - 2*s, s)
        for g in self._grips.values():
            g.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_grips"):
            self._layout_grips()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
