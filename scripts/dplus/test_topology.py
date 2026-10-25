#!/usr/bin/env python3
"""Offline structural regression: graph.outputs cannot be internal links."""
import importlib.util
from collections import Counter
from pathlib import Path
import re, sys, wave

p=Path(__file__).with_name("dplus-topology-preview.py")
spec=importlib.util.spec_from_file_location("preview",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if len(sys.argv)!=2:
    sys.exit("Usage: python3 test_topology.py ~/Downloads/dplus-v4-reference-profile.json")
conf,err=m.generate_config(Path(sys.argv[1]).expanduser())
assert 0<=err<0.12,err
nodes=conf.split('nodes = [',1)[1].split(']',1)[0]
links=conf.split('links = [',1)[1].split(']',1)[0]
outs=conf.split('       outputs = [',1)[1].split(']',1)[0]
internal=re.findall(r'\{ output = "([^"]+)" input = "([^"]+)" \}',links)
graph_outputs=re.findall(r'"([^"]+)"',outs)
sources=Counter(src for src,dst in internal)
targets=Counter(dst for src,dst in internal)
assert len(graph_outputs)==4 and len(set(graph_outputs))==4
assert not set(graph_outputs)&set(sources), "FATAL: graph output reused as internal source"
assert all(cnt==1 for cnt in targets.values()), "FATAL: multiple sources to filter input"
assert all(cnt==1 or port in {"copyL:Out","copyR:Out"} for port,cnt in sources.items())
for side in "LR":
    assert f'{{ type = builtin name = copy{side} label = copy }}' in conf
    assert f'{{ type = builtin name = copyOut{side} label = copy }}' in conf
    assert sources[f'clip{side}:Out']==1
    assert sources[f'copy{side}:Out']==2
    assert sources[f'copyOut{side}:Out']==0
    assert sources[f'zero{side}:Out']==0
    assert (f'copy{side}:Out',f'copyOut{side}:In') in internal
    assert (f'copy{side}:Out',f'zero{side}:In') in internal
assert graph_outputs==["copyOutL:Out","copyOutR:Out","zeroL:Out","zeroR:Out"]
assert 'target.object = "MacBook_Speaker_Raw"' in conf
assert 'audio.position = [ FL FR RL RR ]' in conf
assert '"g_out" = 0.35' in conf and '"Max" = 0.45' in conf
assert 'rate = 44100' in conf
assert m.FINAL_CLAMP==0.45 and m.LIM_OUT==0.35
assert m.graph_activation_error(None) is None
tone=Path(__file__).with_name("audible-check-20s.wav")
if tone.is_file():
    with wave.open(str(tone),"rb") as w:
        assert (w.getnchannels(),w.getframerate(),w.getsampwidth(),w.getnframes())==(2,48000,2,960000)
    print("PASS: optional 20s audio sample is correct and bounded")
else:
    print("SKIP: optional audible test tone not included in repository")
print("PASS: 4 unique graph outputs with no internal reuse")
print("PASS: only first-stage copy outputs branch internally")
print("PASS: original +1 dB DSP, limiter cap and Raw physical target preserved")
print("NOTE: offline topology checks, not a live PipeWire audio test")
