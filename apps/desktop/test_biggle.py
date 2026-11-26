import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
import tkinter as tk

import biggle


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "profile.json"

    def test_profile_recovery(self):
        for invalid in ("[1]", "{", '{"skin": "unknown", "mood": false}'):
            self.path.write_text(invalid)
            self.assertEqual(biggle.load(self.path), biggle.DEFAULT)

    def test_model_context_and_response(self):
        with patch("biggle.urlopen", return_value=BytesIO(b'{"message":{"content":"yes"}}')) as network:
            msg = [{"role": "user", "content": "hello"}]
            self.assertEqual(biggle.model_reply("demo", biggle.DEFAULT, msg), "yes")
            request = network.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(json.loads(request.data)["messages"][-1], msg[0])

    def test_room_flight_memory(self):
        root = tk.Tk()
        self.addCleanup(root.destroy)
        app = biggle.Biggle(root, self.path)
        root.update()
        app.fields["task"].insert(0, "Доклад")
        app.fields["step"].insert(0, "Открыть слайды")
        app.remember()
        app.persist(dict(skin="Звездочёт", mood="Игривый"))
        saved = biggle.load(self.path)
        self.assertIn("Открыть слайды", biggle.recall(saved))
        self.assertEqual(saved["skin"], "Звездочёт")
        app.fly()
        root.update()
        self.assertTrue(app.pet.winfo_viewable())
        app.float.event_generate("<ButtonPress-1>", x=60,y=80)
        app.float.event_generate("<ButtonRelease-1>", x=60,y=80)
        root.update()
        self.assertTrue(app.away)
        self.assertEqual(app.reaction, "happy")
        app.touch()
        app.touch()
        self.assertEqual(app.reaction, "dodge")
        self.assertIsNotNone(app.trip)
        start, duration, x, y, end_x, end_y = app.trip
        app.animate(start + duration + .01)
        root.update()
        self.assertEqual((app.pet.winfo_x(), app.pet.winfo_y()), (end_x, end_y))
        app.float.event_generate("<Button-3>", x=60, y=80)
        root.update()
        self.assertTrue(root.winfo_viewable())
        app.fly()
        app.animate(app.last_activity + 301)
        self.assertIsNone(app.trip)
        app.animate(app.last_activity + 601)
        self.assertFalse(app.away)
        app.toggle_focus()
        app.animate(app.focus_end + 1)
        self.assertEqual(app.focus_end, 0)
        app.forget()
        self.assertEqual(biggle.load(self.path)["task"], "")
