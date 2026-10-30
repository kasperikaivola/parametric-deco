"""Optional Python desktop editor; CAD work always runs in disposable processes."""
import json
from pathlib import Path
import shutil
import sys
import tempfile

from .config import STYLE_PARAMETERS, config_from_dict
from .desktop_state import PreviewState, fingerprint, replace_value


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
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMainWindow,
        QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget,
        QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView

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
            self.tree.setHeaderLabels(['Parameter', 'JSON value (double-click to edit)'])
            self.tree.setColumnWidth(0, 230)
            self.tree.itemDoubleClicked.connect(self.edit_item)
            self.editor = QPlainTextEdit()
            self.editor.setPlaceholderText('Complete schema-v2 JSON, including lists and null values')
            self.editor.textChanged.connect(self.edited)
            self.tabs = QTabWidget()
            self.tabs.addTab(self.tree, 'Parameters')
            self.tabs.addTab(self.editor, 'Advanced JSON')
            self.tabs.currentChanged.connect(self.refresh_tree)
            tip = QLabel('Double-click any value, list or object to edit JSON. Strings need quotes. '
                         'Use null for automatic overrides; cutting_bed may be null or an object. '
                         'Full parameter ranges: docs/design.md. Changes regenerate CAD automatically.')
            tip.setWordWrap(True)
            left = QWidget()
            layout = QVBoxLayout(left)
            layout.addWidget(tip)
            layout.addWidget(self.tabs)
            self.mode = QLabel(self.inventory_label)
            self.mode.setWordWrap(True)
            layout.addWidget(self.mode)

            self.view = QWebEngineView()
            self.view.setHtml('<body style="background:#12151b;color:#eee;font:20px sans-serif;'
                              'padding:40px">Edit a design to generate validated physical CAD.</body>')
            self.view.loadFinished.connect(self.view_loaded)
            self.status = QLabel()
            self.status.setWordWrap(True)
            self.status.setStyleSheet('font-weight:600;padding:10px;background:#292b32;color:#ffd58b')
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
            right_layout.addWidget(self.view, 1)
            right_layout.addLayout(buttons)
            right_layout.addWidget(self.details)
            splitter = QSplitter()
            splitter.addWidget(left)
            splitter.addWidget(right)
            splitter.setSizes([470, 970])
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
            self.tree.clear()
            try:
                data = json.loads(self.editor.toPlainText())
                if not isinstance(data, dict):
                    return
            except ValueError:
                return

            def add(parent, key, value, path):
                encoded = json.dumps(value, ensure_ascii=False)
                item = QTreeWidgetItem(parent, [str(key), encoded if len(encoded) < 140
                                                else encoded[:137] + '…'])
                item.setData(0, Qt.ItemDataRole.UserRole, path)
                item.setToolTip(1, encoded)
                if isinstance(value, dict):
                    for name, child in value.items():
                        add(item, name, child, (*path, name))
                elif isinstance(value, list):
                    for index, child in enumerate(value):
                        add(item, index, child, (*path, index))
            for key, value in data.items():
                add(self.tree, key, value, (key,))
            self.tree.expandToDepth(0)

        def edit_item(self, item, column):
            path = tuple(item.data(0, Qt.ItemDataRole.UserRole))
            data = json.loads(self.editor.toPlainText())
            value = data
            for key in path:
                value = value[key]
            text, ok = QInputDialog.getMultiLineText(
                self, 'Edit ' + '.'.join(map(str, path)),
                'JSON value: numbers, "strings", null, lists or objects.\n'
                'Edit a parent list to add/remove placements or change its length.',
                json.dumps(value, indent=2))
            if ok:
                try:
                    replace_value(data, path, text)
                except ValueError as error:
                    QMessageBox.warning(self, 'Invalid JSON value', str(error))
                    return
                self.set_config(data)

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
            self.show_status('CANCELLED · previous preview is stale. Edit any parameter to resume.')

        def start_preview(self):
            if self.closed or self.state.config is None:
                return
            self.stop_preview_process()
            revision = self.state.revision
            self.show_status('BUILDING CAD · previous preview is stale. This can take seconds or '
                             'minutes; validating real geometry before display.')
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
            self.update_export()

        def process_error(self, process, error):
            if error == QProcess.ProcessError.FailedToStart:
                self.finished(process, -1)

        def job_output(self, process):
            text = bytes(process.readAllStandardOutput()).decode(errors='replace').strip()
            if text:
                mode, revision, *_ = self.jobs.get(process, ('job', '?'))
                self.details.appendPlainText(f'{mode} #{revision}: {text}')

        def finished(self, process, code):
            job = self.jobs.pop(process, None)
            if job is None:
                return
            mode, revision, out, jobdir, job_fingerprint = job
            self.job_output(process)
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
                    self.show_status('CURRENT · digitally validated CAD · config '
                                     + job_fingerprint[:12] + '. Physical/host checks NOT RUN.')
                    self.details.appendPlainText(json.dumps(result.get('validation', {}), indent=2))
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
                        self.show_status('CURRENT · exported config ' + job_fingerprint[:12]
                                         + ' to ' + str(out) + '. Physical/host checks NOT RUN.')
                else:
                    self.details.appendPlainText('Export failed: ' + result.get('error', 'Worker failed'))
                    if self.state.ready:
                        self.show_status('CURRENT · CAD validated; export failed: '
                                         + result.get('error', 'Worker failed'))
                    QMessageBox.warning(self, 'Export failed', result.get('error', 'Worker failed'))
            shutil.rmtree(jobdir, ignore_errors=True)
            process.deleteLater()
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
            self.show_status('EXPORTING snapshot ' + self.current_fingerprint()[:12]
                             + ' · rebuilding and validating before transactional export.')
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

    return Window()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
