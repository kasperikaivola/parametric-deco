"""Optional Python desktop editor; CAD work always runs in disposable processes."""
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

from .config import STYLE_PARAMETERS, config_from_dict
from .desktop_state import PreviewState, fingerprint
from .parameter_edit import allowed_text, apply_parameter_edit


# Same dark surfaces as the offline assembly viewer in resources/index.html.
_DARK_STYLE = """
QToolBar { background:#12151b; border:0; spacing:6px; padding:6px; }
QToolBar QToolButton {
    background:transparent; color:#e7dfd4; padding:6px 8px; border-radius:4px;
}
QToolBar QToolButton:hover { background:#242a33; }
QPlainTextEdit, QTreeWidget, QComboBox, QLineEdit {
    background:#181d26; color:#e7dfd4; border:1px solid #30343c;
    selection-background-color:#3d4f66; selection-color:#f6f1e7;
}
QComboBox QAbstractItemView {
    background:#181d26; color:#e7dfd4; selection-background-color:#3d4f66;
    selection-color:#f6f1e7; border:1px solid #30343c;
}
QTreeWidget::item:selected { background:#3d4f66; color:#f6f1e7; }
QHeaderView::section {
    background:#1c222c; color:#a8acb5; border:0;
    border-bottom:1px solid #30343c; padding:4px 6px;
}
QTabWidget::pane { border:1px solid #30343c; background:#12151b; }
QTabBar::tab {
    background:#1c222c; color:#a8acb5; border:1px solid #30343c; padding:6px 12px;
}
QTabBar::tab:selected { background:#242a33; color:#e7dfd4; }
QPushButton {
    background:#242a33; color:#e7dfd4; border:1px solid #555;
    border-radius:4px; padding:8px 12px;
}
QPushButton:hover { background:#2e3642; }
QPushButton:disabled { color:#6d7380; background:#1a1f28; }
QSplitter::handle { background:#30343c; }
QScrollBar:vertical, QScrollBar:horizontal { background:#12151b; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background:#3a4150; min-height:24px;
}
QToolTip, QMenu { background:#242a33; color:#e7dfd4; border:1px solid #30343c; }
QMenu::item:selected { background:#3d4f66; }
QProgressBar {
    background:#1c222c; color:#e7dfd4; border:1px solid #30343c;
    border-radius:4px; text-align:center; min-height:22px; max-height:22px;
}
QProgressBar::chunk { background:#c4924a; border-radius:3px; }
"""

# First-run expectations from measured desktop builds. Later runs use this session's times.
_STYLE_ESTIMATE_S = {
    'laminar': 10.0,
    'layered-creature': 15.0,
    'radial-weave': 25.0,
    'rib-study': 5.0,
}


def progress_fraction(elapsed, estimate, floor=0.0, ceiling=0.9):
    """Fill for a timed estimate. The bar reaches `ceiling` at the estimate, then creeps."""
    estimate = max(float(estimate), 0.5)
    elapsed = max(float(elapsed), 0.0)
    if elapsed <= estimate:
        fraction = ceiling * elapsed / estimate
    else:
        span = max(1.0 - ceiling, 0.02)
        over = elapsed - estimate
        fraction = min(0.98, ceiling + span * (1.0 - math.exp(-over / estimate)))
    return min(0.98, max(float(floor), fraction))


def apply_dark_theme(app=None):
    """Paint the desktop chrome with the assembly viewer's dark palette."""
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QApplication

    app = app or QApplication.instance()
    if app is None:
        return
    app.setStyle('Fusion')
    bg = QColor('#12151b')
    panel = QColor('#181d26')
    raised = QColor('#242a33')
    text = QColor('#e7dfd4')
    muted = QColor('#a8acb5')
    highlight = QColor('#3d4f66')
    highlight_text = QColor('#f6f1e7')
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, bg),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, panel),
        (QPalette.ColorRole.AlternateBase, raised),
        (QPalette.ColorRole.ToolTipBase, raised),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, raised),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.BrightText, QColor('#ffffff')),
        (QPalette.ColorRole.Highlight, highlight),
        (QPalette.ColorRole.HighlightedText, highlight_text),
        (QPalette.ColorRole.Link, QColor('#edbd74')),
        (QPalette.ColorRole.PlaceholderText, muted),
        (QPalette.ColorRole.Light, QColor('#30343c')),
        (QPalette.ColorRole.Mid, QColor('#30343c')),
        (QPalette.ColorRole.Dark, QColor('#0c0e13')),
        (QPalette.ColorRole.Shadow, QColor('#0c0e13')),
    ):
        palette.setColor(role, color)
    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.HighlightedText,
    ):
        palette.setColor(disabled, role, muted)
    app.setPalette(palette)
    app.setStyleSheet(_DARK_STYLE)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    except ImportError as error:
        print('Desktop dependencies missing. Install with: python -m pip install '
              '\"parametric-deco[gui]\" (or pip install -e \".[gui]\" from source).',
              file=sys.stderr)
        print(f'Qt could not load: {error}. See docs/implementation/desktop.md for Linux platform libraries.',
              file=sys.stderr)
        return 2
    app = QApplication(sys.argv[:1])
    window = create_window()
    if argv and len(argv) == 1:
        window.load_path(Path(argv[0]))
    window.show()
    return app.exec()


def create_window():
    """Import Qt lazily so ordinary CLI installations stay light."""
    from PySide6.QtCore import QProcess, QTimer, Qt, QUrl
    from PySide6.QtGui import QAction, QColor
    from PySide6.QtWidgets import (
        QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
        QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
        QSplitter, QStyledItemDelegate, QTabWidget, QTreeWidget, QTreeWidgetItem,
        QVBoxLayout, QWidget,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView

    class ValueDelegate(QStyledItemDelegate):
        """Edit the value column in the row. Lists and objects expand in that cell."""

        def createEditor(self, parent, option, index):
            if index.column() != 1:
                return None
            full = index.data(Qt.ItemDataRole.UserRole)
            text = full if isinstance(full, str) else ''
            if text[:1] in '{[':
                editor = QPlainTextEdit(parent)
                editor.setMinimumHeight(max(option.rect.height(), 96))
                return editor
            editor = QLineEdit(parent)
            editor.setFrame(False)
            return editor

        def setEditorData(self, editor, index):
            full = index.data(Qt.ItemDataRole.UserRole)
            text = full if isinstance(full, str) else (index.data(Qt.ItemDataRole.DisplayRole) or '')
            if isinstance(editor, QPlainTextEdit):
                editor.setPlainText(text)
            else:
                editor.setText(text)

        def setModelData(self, editor, model, index):
            text = editor.toPlainText() if isinstance(editor, QPlainTextEdit) else editor.text()
            model.setData(index, text, Qt.ItemDataRole.EditRole)

        def updateEditorGeometry(self, editor, option, index):
            if isinstance(editor, QPlainTextEdit):
                rect = option.rect
                rect.setHeight(max(rect.height(), 120))
                editor.setGeometry(rect)
            else:
                super().updateEditorGeometry(editor, option, index)

    class Window(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('Parametric Deco · live CAD editor')
            self.resize(1440, 950)
            self.state = PreviewState()
            self.inventory = None
            self.inventory_label = 'New manufactured parts'
            self.root = Path(tempfile.mkdtemp(prefix='deco-desktop-'))
            self.jobs = {}
            self.preview_process = None
            self.export_process = None
            self.preview_directory = None
            self.preview_fingerprint = None
            self.camera = None
            self.closed = False
            self.updating = False
            self.dirty = False
            self.config_path = None
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.setInterval(650)
            self.timer.timeout.connect(self.start_preview)

            toolbar = self.addToolBar('Design')
            for label, slot in [('New', self.new_config), ('Open…', self.open_config),
                                ('Save config…', self.save_config),
                                ('Use saved inventory…', self.open_inventory),
                                ('New parts mode', self.clear_inventory)]:
                action = QAction(label, self)
                action.triggered.connect(slot)
                toolbar.addAction(action)
            self.style = QComboBox()
            self.style.addItems(STYLE_PARAMETERS)
            self.style.currentTextChanged.connect(self.change_style)
            toolbar.addWidget(QLabel('  Style: '))
            toolbar.addWidget(self.style)

            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(['Parameter', 'Value', 'Allowed'])
            self.tree.setColumnWidth(0, 168)
            self.tree.setColumnWidth(1, 120)
            self.tree.header().setStretchLastSection(True)
            self.tree.setItemDelegate(ValueDelegate(self.tree))
            self.tree.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked
                | QAbstractItemView.EditTrigger.SelectedClicked
                | QAbstractItemView.EditTrigger.EditKeyPressed
                | QAbstractItemView.EditTrigger.AnyKeyPressed)
            self.tree.itemChanged.connect(self.commit_parameter)
            self._filling_tree = False
            self.editor = QPlainTextEdit()
            self.editor.setPlaceholderText('Complete schema-v2 JSON, including lists and null values')
            self.editor.textChanged.connect(self.edited)
            self.tabs = QTabWidget()
            self.tabs.addTab(self.tree, 'Parameters')
            self.tabs.addTab(self.editor, 'Advanced JSON')
            self.tabs.currentChanged.connect(self.refresh_tree)
            tip = QLabel('Edit a value in the table. Numbers round or clamp to the allowed range '
                         'beside them. Text can be typed with or without quotes. Use null for '
                         'automatic overrides; cutting_bed may be null or an object. Edit a list '
                         'to add or remove entries. Changes regenerate CAD automatically.')
            tip.setWordWrap(True)
            tip.setStyleSheet('color:#a8acb5; background:transparent')
            left = QWidget()
            layout = QVBoxLayout(left)
            layout.addWidget(tip)
            layout.addWidget(self.tabs)
            self.mode = QLabel(self.inventory_label)
            self.mode.setWordWrap(True)
            layout.addWidget(self.mode)

            self.view = QWebEngineView()
            self.view.setHtml(
                '<body style="background:#12151b;color:#e7dfd4;font:20px sans-serif;'
                'padding:40px">Edit a design to generate validated physical CAD.</body>')
            self.view.page().setBackgroundColor(QColor('#12151b'))
            self.view.loadFinished.connect(self.view_loaded)
            self.status = QLabel()
            self.status.setWordWrap(True)
            self.status.setStyleSheet('font-weight:600;padding:10px;background:#292b32;color:#ffd58b')
            self.progress = QProgressBar()
            self.progress.setRange(0, 1000)
            self.progress.setTextVisible(True)
            self.progress.hide()
            self.progress_timer = QTimer(self)
            self.progress_timer.setInterval(200)
            self.progress_timer.timeout.connect(self.tick_progress)
            self.duration_by_style = {}
            self.progress_started = None
            self.progress_process = None
            self.progress_floor = 0.0
            self.progress_ceiling = 0.9
            self.progress_estimate = 12.0
            self.progress_label = 'Building CAD'
            self.job_buffers = {}
            self.details = QPlainTextEdit()
            self.details.setReadOnly(True)
            self.details.setMaximumBlockCount(1000)
            self.details.setMaximumHeight(130)
            self.export_button = QPushButton('Export current validated design…')
            self.export_button.clicked.connect(self.export_current)
            self.cancel_button = QPushButton('Cancel preview')
            self.cancel_button.clicked.connect(self.cancel_preview)
            buttons = QHBoxLayout()
            buttons.addWidget(self.cancel_button)
            buttons.addWidget(self.export_button)
            right = QWidget()
            right_layout = QVBoxLayout(right)
            right_layout.addWidget(self.status)
            right_layout.addWidget(self.progress)
            right_layout.addWidget(self.view, 1)
            right_layout.addLayout(buttons)
            right_layout.addWidget(self.details)
            splitter = QSplitter()
            splitter.addWidget(left)
            splitter.addWidget(right)
            splitter.setSizes([560, 880])
            self.setCentralWidget(splitter)
            self.set_config(config_from_dict({}).to_dict(), dirty=False)

        def set_config(self, data, dirty=True):
            self.editor.setPlainText(json.dumps(data, indent=2) + '\n')
            self.dirty = dirty
            self.refresh_tree()

        def edited(self):
            self.dirty = True
            self.timer.stop()
            self.state.edit(self.editor.toPlainText())
            self.stop_preview_process()
            if self.export_process is None:
                self.hide_progress()
            self.update_export()
            if self.state.config is None:
                self.show_status('INVALID CONFIG · previous preview is stale. ' + self.state.error)
                return
            self.updating = True
            self.style.setCurrentText(self.state.config['style'])
            self.updating = False
            self.show_status('STALE · waiting for edits to settle; CAD has not been validated yet.')
            self.timer.start()

        def refresh_tree(self, *_):
            self._filling_tree = True
            try:
                self.tree.clear()
                try:
                    data = json.loads(self.editor.toPlainText())
                except ValueError:
                    return
                if not isinstance(data, dict):
                    return

                def add(parent, key, value, path):
                    encoded = json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list)) and len(encoded) >= 80:
                        shown = encoded[:77] + '…'
                    else:
                        shown = encoded
                    phrase = allowed_text(data, path)
                    item = QTreeWidgetItem(parent, [str(key), shown, phrase])
                    item.setData(0, Qt.ItemDataRole.UserRole, path)
                    item.setData(1, Qt.ItemDataRole.UserRole, encoded)
                    item.setToolTip(1, encoded)
                    item.setToolTip(2, phrase)
                    item.setForeground(2, QColor('#a8acb5'))
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    if isinstance(value, dict):
                        for name, child in value.items():
                            add(item, name, child, (*path, name))
                    elif isinstance(value, list):
                        for index, child in enumerate(value):
                            add(item, index, child, (*path, index))

                for key, value in data.items():
                    add(self.tree, key, value, (key,))
                self.tree.expandToDepth(0)
            finally:
                self._filling_tree = False

        def commit_parameter(self, item, column):
            if self._filling_tree or column != 1:
                return
            path = tuple(item.data(0, Qt.ItemDataRole.UserRole) or ())
            if not path:
                return
            text = item.text(1)
            QTimer.singleShot(0, lambda path=path, text=text: self._apply_tree_edit(path, text))

        def _apply_tree_edit(self, path, text):
            try:
                data = json.loads(self.editor.toPlainText())
                updated = apply_parameter_edit(data, path, text)
            except json.JSONDecodeError as error:
                self.refresh_tree()
                self.show_status('INVALID CONFIG · ' + str(error))
                return
            except (ValueError, TypeError, KeyError, OverflowError) as error:
                self.refresh_tree()
                self.show_status('VALUE UNCHANGED · ' + str(error))
                return
            if updated == data:
                self.refresh_tree()
                return
            self.set_config(updated)

        def change_style(self, style):
            if self.updating:
                return
            try:
                data = json.loads(self.editor.toPlainText())
                if not isinstance(data, dict):
                    raise ValueError('Config must be an object')
            except ValueError as error:
                QMessageBox.warning(self, 'Fix JSON first', str(error))
                return
            data['style'] = style
            data['parameters'] = config_from_dict({'style': style}).to_dict()['parameters']
            self.set_config(data)

        def discard_changes(self):
            return not self.dirty or QMessageBox.question(
                self, 'Unsaved configuration', 'Discard unsaved configuration edits?',
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Discard

        def new_config(self):
            if self.discard_changes():
                self.config_path = None
                self.clear_inventory()
                self.set_config(config_from_dict({'style': self.style.currentText()}).to_dict(),
                                dirty=False)

        def open_config(self):
            if not self.discard_changes():
                return
            path, _ = QFileDialog.getOpenFileName(self, 'Open schema-v2 config', '', 'JSON (*.json)')
            if path:
                self.load_path(Path(path))

        def load_path(self, path):
            try:
                data = config_from_dict(json.loads(path.read_text())).to_dict()
            except (OSError, ValueError, TypeError) as error:
                QMessageBox.warning(self, 'Cannot load configuration', str(error))
                return
            self.config_path = path
            self.set_config(data, dirty=False)

        def save_config(self):
            if self.state.config is None:
                QMessageBox.warning(self, 'Invalid configuration', self.state.error)
                return
            path, _ = QFileDialog.getSaveFileName(self, 'Save schema-v2 config',
                                                str(self.config_path or 'design.json'), 'JSON (*.json)')
            if path:
                try:
                    Path(path).write_text(json.dumps(self.state.config, indent=2) + '\n')
                except OSError as error:
                    QMessageBox.warning(self, 'Cannot save configuration', str(error))
                    return
                self.config_path = Path(path)
                self.dirty = False

        def open_inventory(self):
            path, _ = QFileDialog.getOpenFileName(self, 'Use immutable manufactured inventory', '',
                                                'JSON (*.json)')
            if path:
                try:
                    from .model import Inventory
                    data = json.loads(Path(path).read_text())
                    Inventory.from_dict(data)
                except (OSError, ValueError, TypeError, KeyError) as error:
                    QMessageBox.warning(self, 'Cannot load inventory', str(error))
                    return
                self.inventory = data
                self.inventory_label = 'Reconfigure saved inventory: ' + path
                self.mode.setText(self.inventory_label)
                self.edited()

        def clear_inventory(self):
            self.inventory = None
            self.inventory_label = 'New manufactured parts'
            self.mode.setText(self.inventory_label)
            self.edited()

        def show_status(self, text):
            self.status.setText(text)

        def estimate_seconds(self, export=False):
            style = self.state.config['style'] if self.state.config else ''
            base = self.duration_by_style.get(style, _STYLE_ESTIMATE_S.get(style, 12.0))
            return base + (4.0 if export else 0.0)

        def begin_progress(self, label, estimate):
            self.progress_started = time.monotonic()
            self.progress_floor = 0.0
            self.progress_ceiling = 0.9
            self.progress_estimate = max(float(estimate), 0.5)
            self.progress_label = label
            self.progress.setValue(0)
            self.progress.show()
            self.progress_timer.start()
            self.tick_progress()

        def hide_progress(self):
            self.progress_timer.stop()
            self.progress.hide()
            self.progress_started = None
            self.progress_process = None

        def tick_progress(self):
            if self.progress_started is None:
                return
            elapsed = time.monotonic() - self.progress_started
            fraction = progress_fraction(
                elapsed, self.progress_estimate, self.progress_floor, self.progress_ceiling)
            self.progress.setValue(int(round(fraction * 1000)))
            remaining = self.progress_estimate - elapsed
            if remaining >= 0.5:
                detail = f'about {remaining:.0f}s left'
            elif elapsed <= self.progress_estimate + 0.5:
                detail = 'almost done'
            else:
                detail = 'past the estimate'
            self.progress.setFormat(f'{self.progress_label} · {elapsed:.0f}s · {detail}')

        def note_progress(self, line):
            if self.progress_started is None:
                return
            phase = None
            fraction = None
            for part in line.split():
                if part.startswith('phase='):
                    phase = part.split('=', 1)[1]
                elif part.startswith('fraction='):
                    try:
                        fraction = float(part.split('=', 1)[1])
                    except ValueError:
                        return
            if fraction is not None:
                self.progress_floor = max(self.progress_floor, min(fraction, 0.98))
            elapsed = time.monotonic() - self.progress_started
            if phase == 'mesh':
                self.progress_label = 'Meshing preview'
                self.progress_estimate = min(self.progress_estimate, elapsed + 2.0)
            elif phase == 'export':
                self.progress_label = 'Writing export'
                self.progress_estimate = min(self.progress_estimate, elapsed + 3.0)
            elif phase == 'construct':
                self.progress_label = 'Building CAD'
            self.tick_progress()

        def update_export(self):
            self.export_button.setEnabled(self.state.ready and self.export_process is None
                                          and self.preview_fingerprint == self.current_fingerprint())

        def current_fingerprint(self):
            if self.state.config is None:
                return None
            return fingerprint(self.state.config, self.inventory)

        def stop_preview_process(self):
            if self.preview_process is not None:
                self.preview_process.kill()
                self.preview_process = None

        def cancel_preview(self):
            self.state.edit(self.editor.toPlainText())
            self.timer.stop()
            self.stop_preview_process()
            self.state.validated = False
            self.update_export()
            self.hide_progress()
            self.show_status('CANCELLED · previous preview is stale. Edit any parameter to resume.')

        def start_preview(self):
            if self.closed or self.state.config is None:
                return
            self.stop_preview_process()
            revision = self.state.revision
            self.show_status('BUILDING CAD')
            self.begin_progress('Building CAD', self.estimate_seconds())
            self.launch('preview', revision, self.root / f'scene-{revision}')

        def launch(self, mode, revision, out, force=False):
            jobdir = self.root / f'job-{mode}-{revision}'
            jobdir.mkdir(exist_ok=True)
            request = {'config': self.state.config, 'inventory': self.inventory,
                       'mode': mode, 'out': str(out), 'force': force}
            job_fingerprint = fingerprint(request['config'], request['inventory'])
            request_path, result_path = jobdir / 'request.json', jobdir / 'result.json'
            request_path.write_text(json.dumps(request))
            process = QProcess(self)
            process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.jobs[process] = (mode, revision, out, jobdir, job_fingerprint)
            if mode == 'preview':
                self.preview_process = process
            else:
                self.export_process = process
            process.readyReadStandardOutput.connect(
                lambda: self.job_output(process))
            process.finished.connect(lambda code, status: self.finished(process, code))
            process.errorOccurred.connect(lambda error: self.process_error(process, error))
            process.start(sys.executable, ['-m', 'parametric_deco.desktop_worker',
                                          str(request_path), str(result_path)])
            self.progress_process = process
            self.update_export()

        def process_error(self, process, error):
            if error == QProcess.ProcessError.FailedToStart:
                self.finished(process, -1)

        def job_output(self, process, flush=False):
            chunk = bytes(process.readAllStandardOutput()).decode(errors='replace')
            pending = self.job_buffers.get(process, '') + chunk
            if flush:
                lines = pending.split('\n') if pending else []
                self.job_buffers.pop(process, None)
            else:
                lines = pending.split('\n')
                self.job_buffers[process] = lines.pop() if lines else ''
            shown = []
            for line in lines:
                line = line.strip()
                if line.startswith('PROGRESS '):
                    self.note_progress(line)
                elif line:
                    shown.append(line)
            if shown:
                mode, revision, *_ = self.jobs.get(process, ('job', '?'))
                self.details.appendPlainText(f'{mode} #{revision}: ' + '\n'.join(shown))

        def finished(self, process, code):
            job = self.jobs.pop(process, None)
            if job is None:
                return
            mode, revision, out, jobdir, job_fingerprint = job
            owns_bar = self.progress_process is process
            elapsed = None
            if owns_bar and self.progress_started is not None:
                elapsed = time.monotonic() - self.progress_started
            self.job_output(process, flush=True)
            try:
                result = json.loads((jobdir / 'result.json').read_text())
            except (OSError, ValueError):
                result = {'error': 'CAD worker stopped or could not start. See job log.'}
            success = code == 0 and result.get('fingerprint') == job_fingerprint
            if mode == 'preview':
                if self.preview_process is process:
                    self.preview_process = None
                accepted = self.state.complete(revision, success, result.get('error'))
                if accepted and success and not self.closed:
                    self.preview_fingerprint = job_fingerprint
                    self.install_preview(out, revision)
                    if elapsed is not None and self.state.config is not None:
                        style = self.state.config['style']
                        previous = self.duration_by_style.get(style)
                        self.duration_by_style[style] = (
                            elapsed if previous is None else 0.65 * previous + 0.35 * elapsed)
                    timing = f' · {elapsed:.0f}s' if elapsed is not None else ''
                    self.show_status('CURRENT · config ' + job_fingerprint[:12] + timing)
                    for issue in (result.get('validation') or {}).get('issues') or []:
                        self.details.appendPlainText(
                            f"{issue.get('severity', '')} {issue.get('code', '')}: "
                            f"{issue.get('message', '')}")
                else:
                    shutil.rmtree(out, ignore_errors=True)
                    if accepted:
                        self.show_status('CAD FAILED · previous preview is stale. '
                                         + result.get('error', 'Worker failed'))
            else:
                self.export_process = None
                if success:
                    self.details.appendPlainText(f'Exported config {job_fingerprint} to {out}')
                    if self.state.ready and job_fingerprint == self.current_fingerprint():
                        timing = f' · {elapsed:.0f}s' if elapsed is not None else ''
                        self.show_status('CURRENT · exported config ' + job_fingerprint[:12]
                                         + ' to ' + str(out) + timing)
                else:
                    self.details.appendPlainText('Export failed: ' + result.get('error', 'Worker failed'))
                    if self.state.ready:
                        self.show_status('CURRENT · CAD validated; export failed: '
                                         + result.get('error', 'Worker failed'))
                    QMessageBox.warning(self, 'Export failed', result.get('error', 'Worker failed'))
            shutil.rmtree(jobdir, ignore_errors=True)
            process.deleteLater()
            if owns_bar:
                self.hide_progress()
            self.update_export()

        def install_preview(self, out, revision):
            old = self.preview_directory
            self.preview_directory = out

            def load(camera):
                try:
                    camera = json.loads(camera) if isinstance(camera, str) else None
                except ValueError:
                    camera = None
                if self.closed or self.state.revision != revision:
                    if out != self.preview_directory:
                        shutil.rmtree(out, ignore_errors=True)
                    return
                if isinstance(camera, dict):
                    self.camera = camera
                self.view.setUrl(QUrl.fromLocalFile(str(out / 'preview/index.html')))
                if old and old != out:
                    # WebEngine may still be reading the old page until navigation completes.
                    QTimer.singleShot(2000, lambda: shutil.rmtree(old, ignore_errors=True))
            self.view.page().runJavaScript(
                'JSON.stringify(window.decoGetView ? window.decoGetView() : null)', load)

        def view_loaded(self, ok):
            if ok and self.camera:
                self.view.page().runJavaScript('window.decoSetView && window.decoSetView('
                                               + json.dumps(self.camera) + ')')

        def export_current(self):
            if (self.export_process is not None or not self.state.ready
                    or self.preview_fingerprint != self.current_fingerprint()):
                return
            directory = QFileDialog.getExistingDirectory(self, 'Select export parent directory')
            if not directory:
                return
            name, ok = QInputDialog.getText(self, 'Export directory', 'Subdirectory name:',
                                           text='my-design')
            if not ok or not name:
                return
            if Path(name).name != name or name in ('.', '..') or '/' in name or '\\' in name:
                QMessageBox.warning(self, 'Invalid name', 'Choose one subdirectory name.')
                return
            out = Path(directory) / name
            force = out.exists() and (not out.is_dir() or any(out.iterdir()))
            if force and QMessageBox.question(
                self, 'Replace generated export?',
                f'Overwrite generated files in {out}?\nExisting manifest ownership checks still apply.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            self.show_status('EXPORTING ' + self.current_fingerprint()[:12])
            self.begin_progress('Exporting', self.estimate_seconds(export=True))
            self.launch('export', self.state.revision, out, force)

        def closeEvent(self, event):
            if self.export_process is not None:
                QMessageBox.information(self, 'Export in progress',
                                        'Wait for export to finish before closing. '
                                        'Interrupting file replacement could leave a partial export.')
                event.ignore()
                return
            if not self.discard_changes():
                event.ignore()
                return
            self.closed = True
            self.timer.stop()
            for process in list(self.jobs):
                process.kill()
            for process in list(self.jobs):
                process.waitForFinished(3000)
            self.view.setUrl(QUrl('about:blank'))
            shutil.rmtree(self.root, ignore_errors=True)
            event.accept()

    apply_dark_theme()
    return Window()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
