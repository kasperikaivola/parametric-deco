"""Optional real Qt/WebEngine + CAD process integration (DECO_GUI_TESTS=1)."""
import json
import os
import time

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('DECO_GUI_TESTS') != '1',
                                reason='optional desktop integration; set DECO_GUI_TESTS=1')


def wait_until(app, predicate, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('GUI integration timed out')


def javascript(app, window, expression):
    result = []
    window.view.page().runJavaScript('JSON.stringify((' + expression + '))', result.append)
    wait_until(app, lambda: bool(result), 15)
    return json.loads(result[0]) if result[0] else None


def test_real_gui_cad_edit_orbit_stale_failure_export_and_shutdown(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from parametric_deco.config import config_from_dict
    from parametric_deco.desktop import create_window

    app = QApplication.instance() or QApplication([])
    window = create_window()
    window.set_config(config_from_dict({'style': 'rib-study'}).to_dict(), dirty=False)
    window.show()
    try:
        wait_until(app, lambda: window.state.ready)
        wait_until(app, lambda: javascript(app, window, 'typeof window.decoGetView') == 'function')
        assert javascript(app, window, "document.getElementById('status').textContent").endswith(
            'identified plywood instances · orbit preview')
        assert window.export_button.isEnabled()
        javascript(app, window, 'window.decoSetView({yaw:0.8,pitch:0.6,zoom:1.2})')
        first_fingerprint = window.preview_fingerprint
        config = config_from_dict({'style':'rib-study', 'parameters':{
            'placements':[{'module_id':'other','angle_deg':0}]}}).to_dict()
        window.set_config(config, dirty=False)
        assert not window.export_button.isEnabled()
        assert 'STALE' in window.status.text()
        wait_until(app, lambda: window.state.ready)
        wait_until(app, lambda: javascript(app, window, 'window.decoGetView && window.decoGetView().yaw')
                   == .8)
        assert window.preview_fingerprint != first_fingerprint
        good_directory = window.preview_directory
        # Geometry-level failure (schema-valid but outside physical envelope).
        config['parameters']['placements'][0]['x_mm'] = 2000
        window.set_config(config, dirty=False)
        wait_until(app, lambda: 'CAD FAILED' in window.status.text())
        assert not window.export_button.isEnabled()
        assert window.preview_directory == good_directory and good_directory.exists()
        window.editor.setPlainText('{')
        assert 'INVALID CONFIG' in window.status.text()
        assert not window.export_button.isEnabled()
        window.set_config(config_from_dict({'style':'rib-study'}).to_dict(), dirty=False)
        window.start_preview()
        old_revision = window.state.revision
        window.cancel_preview()
        assert window.state.revision > old_revision and not window.state.ready
        wait_until(app, lambda: not window.jobs)
        assert 'CANCELLED' in window.status.text()
        window.set_config(config_from_dict({'style':'rib-study'}).to_dict(), dirty=False)
        wait_until(app, lambda: window.state.ready)
        # Exercise actual export process with a frozen request, then edit during export.
        exported_fingerprint = window.current_fingerprint()
        out = tmp_path / 'export'
        window.launch('export', window.state.revision, out)
        window.editor.setPlainText('{')
        wait_until(app, lambda: window.export_process is None, 180)
        manifest = json.loads((out / 'manifest.json').read_text())
        assert manifest and (out / 'inventory.json').exists()
        assert exported_fingerprint in window.details.toPlainText()
        assert not window.export_button.isEnabled()
        window.set_config(config_from_dict({'style':'rib-study'}).to_dict(), dirty=False)
        wait_until(app, lambda: window.state.ready)
        wait_until(app, lambda: javascript(app, window, 'typeof window.decoGetView') == 'function')
        screenshot = os.environ.get('DECO_GUI_SCREENSHOT')
        if screenshot:
            # Allow compositor to paint the model, then capture the actual desktop widget.
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            assert window.grab().save(screenshot)
        # A real failed export must clear its progress state and leave current CAD usable.
        notices = []
        monkeypatch.setattr(QMessageBox, 'warning', lambda *args: notices.append(args))
        window.launch('export', window.state.revision, out)
        wait_until(app, lambda: window.export_process is None, 180)
        assert notices and 'export failed' in window.status.text()
        assert window.export_button.isEnabled()
        # Leave a worker running when closing to verify child cancellation and cleanup.
        window.state.edit(window.editor.toPlainText())
        window.start_preview()
        root = window.root
        window.dirty = False
        window.close()
        app.processEvents()
        assert window.closed and not root.exists() and not window.jobs
    finally:
        window.dirty = False
        if not window.closed and window.export_process is None:
            window.close()
