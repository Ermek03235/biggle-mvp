import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
import tkinter as tk

import beagle


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "profile.json"

    def test_profile_recovery(self):
        for invalid in ("[1]", "{", '{"skin": "unknown", "mood": false}'):
            self.path.write_text(invalid)
            self.assertEqual(beagle.load(self.path), beagle.DEFAULT)

    def test_model_context_and_response(self):
        with patch("beagle.urlopen", return_value=BytesIO(b'{"message":{"content":"yes"}}')) as network:
            msg = [{"role": "user", "content": "hello"}]
            self.assertEqual(beagle.model_reply("demo", beagle.DEFAULT, msg), "yes")
            request = network.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(json.loads(request.data)["messages"][-1], msg[0])

    def test_room_flight_memory(self):
        root = tk.Tk()
        self.addCleanup(root.destroy)
        app = beagle.Beagle(root, self.path)
        root.update()
        app.fields["task"].insert(0, "Доклад")
        app.fields["step"].insert(0, "Открыть слайды")
        app.remember()
        app.persist(dict(skin="Звездочёт", mood="Игривый"))
        saved = beagle.load(self.path)
        self.assertIn("Открыть слайды", beagle.recall(saved))
        self.assertEqual(saved["skin"], "Звездочёт")
        app.fly()
        root.update()
        self.assertTrue(app.pet.winfo_viewable())
        app.float.event_generate("<ButtonPress-1>", x=60,y=80)
        app.float.event_generate("<ButtonRelease-1>", x=60,y=80)
        root.update()
        self.assertTrue(root.winfo_viewable())
        app.forget()
        self.assertEqual(beagle.load(self.path)["task"], "")
