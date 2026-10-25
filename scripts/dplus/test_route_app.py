#!/usr/bin/env python3
"""Offline route-app tests. Never calls a real pactl/systemctl daemon."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

FILE = Path(__file__).parent / "route-app.py"
spec = importlib.util.spec_from_file_location("route_app", FILE)
route_app = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = route_app
spec.loader.exec_module(route_app)
R = route_app


class Fake:
    def __init__(self, *, stream_id=4351, sink_id=69, playing=True, other=False,
                 app="Firefox", media="YouTube video", service="active"):
        self.stream_id = stream_id
        self.sink_id = sink_id
        self.playing = playing
        self.app = app
        self.media = media
        self.node = "firefox"
        self.service = service
        self.default = R.RAW
        self.outputs = {R.RAW: 69, R.DPLUS: 2912, "bluetooth_sink": 802}
        self.moves = []
        self.bounce = False
        self.change_default = False
        self.remove_stream = False
        self.extra = other

    def cmd(self, *argv):
        if argv == ("pactl", "list", "short", "sinks"):
            return "\n".join(f"{v}\t{k}\tPipeWire\ts16le 4ch 44100Hz RUNNING" for k,v in self.outputs.items())
        if argv == ("pactl", "get-default-sink"):
            return self.default
        if argv == ("systemctl", "--user", "is-active", R.UNIT):
            return self.service
        if argv == ("pactl", "list", "short", "sink-inputs"):
            if self.remove_stream:
                return "2913\t69\t-\tPipeWire\tfloat32le 4ch\n"
            base = f"{self.stream_id}\t{self.sink_id}\t147\tPipeWire\tfloat32le 2ch\n"
            if self.extra:
                base += "999\t69\t-\tPipeWire\tfloat32le 2ch\n"
            return base + "2913\t69\t-\tPipeWire\tfloat32le 4ch\n"
        if argv == ("pactl", "list", "sink-inputs"):
            if self.remove_stream:
                return "Sink Input #2913\n\tCorked: no\n\t\tmedia.name = \"MacBook8,1 D+ safe EQ preview output\""
            result = f'''Sink Input #{self.stream_id}
    Driver: PipeWire
    Sink: {self.sink_id}
    Corked: {"no" if self.playing else "yes"}
    Properties:
        application.name = "{self.app}"
        media.name = "{self.media}"
        node.name = "{self.node}"
'''
            if self.extra:
                result += '''Sink Input #999
    Corked: no
    Properties:
        application.name = "Firefox"
        media.name = "Another tab"
'''
            result += '''Sink Input #2913
    Corked: no
    Properties:
        media.name = "MacBook8,1 D+ safe EQ preview output"
        node.name = "dplus_preview_to_raw"
'''
            return result
        if argv[:2] == ("pactl", "move-sink-input"):
            self.moves.append(argv)
            if self.change_default:
                self.default = R.DPLUS
            elif not self.bounce:
                self.sink_id = self.outputs[argv[-1]]
            return ""
        raise AssertionError(argv)


class ParseTests(unittest.TestCase):
    def test_list_realistic(self):
        fake = Fake()
        entries = R.get_streams(fake.cmd)
        self.assertEqual(entries[0], R.Stream(4351,69,"Firefox","YouTube video","firefox",False))
        self.assertTrue(R.is_system_stream(entries[-1]))
        self.assertFalse(R.is_system_stream(entries[0]))

    def test_protect_unnamed_bridge(self):
        self.assertTrue(R.is_system_stream(R.Stream(7,69,"", "misc", "",False)))
        self.assertTrue(R.is_system_stream(R.Stream(7,69,"Browser", "MacBook8,1 D+ safe EQ preview output", "",False)))
        self.assertTrue(R.is_system_stream(R.Stream(7,69,"PipeWire", "", "",False)))
        self.assertTrue(R.is_system_stream(R.Stream(7,69,"Firefox", "normal", "dplus_preview_to_raw",False)))

    def test_corked_does_not_select(self):
        fake = Fake(playing=False)
        with self.assertRaisesRegex(R.RouteError, "No matching"):
            R.selected_stream(R.get_streams(fake.cmd), stream_id=None, app="Firefox", require_playing=True)

    def test_ambiguous_firefox_requires_id(self):
        fake = Fake(other=True)
        with self.assertRaisesRegex(R.RouteError,"Ambiguous.*4351.*999"):
            R.selected_stream(R.get_streams(fake.cmd), stream_id=None, app="Firefox", require_playing=True)


class RoutingTests(unittest.TestCase):
    def run_route(self, fake, dest, sid=None, app=None):
        with patch.object(R.os,"geteuid",return_value=1000):
            return R.route(dest, stream_id=sid, app=app, command=fake.cmd, sleep=lambda _: None)

    def test_move_normal_browser_to_dplus(self):
        fake=Fake()
        result=self.run_route(fake,"dplus",app="Firefox")
        self.assertEqual(result[1],2912)
        self.assertEqual(fake.sink_id,2912)
        self.assertEqual(fake.moves,[("pactl","move-sink-input","4351",R.DPLUS)])
        self.assertEqual(fake.default,R.RAW)

    def test_route_back_to_raw(self):
        fake=Fake(sink_id=2912)
        result=self.run_route(fake,"raw",app="Firefox")
        self.assertEqual(result[1],69)
        self.assertEqual(fake.moves[-1][-1],R.RAW)

    def test_idempotent(self):
        fake=Fake(sink_id=2912)
        self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_reject_bluetooth_source(self):
        fake=Fake(sink_id=802)
        with self.assertRaisesRegex(R.RouteError,"hijack"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_reject_bluetooth_for_raw(self):
        fake=Fake(sink_id=802)
        with self.assertRaisesRegex(R.RouteError,"unrelated"):
            self.run_route(fake,"raw",app="Firefox")

    def test_reject_default_not_raw(self):
        fake=Fake()
        fake.default=R.DPLUS
        with self.assertRaisesRegex(R.RouteError,"Global default"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_refuse_unstarted_managed_service(self):
        fake=Fake(service="inactive")
        with self.assertRaisesRegex(R.RouteError,"not active"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_reject_two_dplus_sinks(self):
        fake=Fake()
        fake.outputs["input."+R.DPLUS]=5555
        with self.assertRaisesRegex(R.RouteError,"Two D\+ outputs"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_reject_dplus_missing(self):
        fake=Fake()
        del fake.outputs[R.DPLUS]
        with self.assertRaisesRegex(R.RouteError,"not found"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertFalse(fake.moves)

    def test_reject_moving_engine(self):
        fake=Fake()
        with self.assertRaisesRegex(R.RouteError,"No matching"):
            self.run_route(fake,"dplus",sid=2913)
        self.assertFalse(fake.moves)

    def test_detect_immediate_route_revert(self):
        fake=Fake()
        fake.bounce=True
        with self.assertRaisesRegex(R.RouteError,"did not stick"):
            self.run_route(fake,"dplus",app="Firefox")
        self.assertEqual(fake.sink_id,69)

    def test_detect_external_default_change(self):
        fake=Fake()
        fake.change_default=True
        with self.assertRaisesRegex(R.RouteError,"Global default changed"):
            self.run_route(fake,"dplus",app="Firefox")

    def test_refuse_unnamed_or_paused(self):
        fake=Fake(playing=False)
        with self.assertRaisesRegex(R.RouteError,"paused"):
            self.run_route(fake,"dplus",sid=4351)

    def test_support_input_prefixed_sink(self):
        fake=Fake()
        sid=fake.outputs.pop(R.DPLUS)
        fake.outputs["input."+R.DPLUS]=sid
        result=self.run_route(fake,"dplus",app="Firefox")
        self.assertEqual(result[1],2912)


if __name__ == "__main__":
    unittest.main(verbosity=2)
