import os
import tempfile

from kazam.backend import config as config_mod


def _fresh_config(tmpdir):
    config_mod.KazamConfig.CONFIGDIR = tmpdir
    config_mod.KazamConfig.CONFIGFILE = os.path.join(tmpdir, "kazam.conf")
    return config_mod.KazamConfig()


def test_restore_token_defaults_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _fresh_config(tmp)
        assert cfg.get("main", "restore_token") == ""


def test_restore_token_roundtrips():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _fresh_config(tmp)
        cfg.set("main", "restore_token", "tok-persist-1")
        cfg.write()
        cfg2 = config_mod.KazamConfig()
        assert cfg2.get("main", "restore_token") == "tok-persist-1"
