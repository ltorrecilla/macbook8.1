# D+ Clarity v4 — status, evidence, and delivery roadmap

**Updated 2026-10-25 · MacBook8,1 (Early 2015) / CachyOS · [Tracking issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39)**

**Goal:** make D+ the automatic, reliable **internal-speaker** output while retaining `MacBook_Speaker_Raw` and the existing patched CS4208 driver as a recoverable base. Deliver actual sound and working A/V synchronization before promoting D+ to the default. **No production-ready D+ implementation or new kernel driver has been released.**

**Current safe state (owner-confirmed):** the old `macbook81-dplus.service` is **disabled/inactive** and `pactl get-default-sink` reports **`MacBook_Speaker_Raw`**. The newest isolated graph experiment did not change this. Do not re-enable the old prototype or make D+ the system default.

## Verified results and boundaries

| Item | Status on the owner's MacBook | Important limitation |
|---|---|---|
| Patched HDA/CS4208 | Kernel `7.3.0-2-cachyos` runs; all three DKMS modules passed **on-disk** checks for it and `6.18.55-2-cachyos-lts`; ALSA exposed `CS4208 Speaker` device 2 | On-disk checks do not prove current module binding, boot image contents or playback on another install |
| Raw routing | Preferred `MacBook_Speaker_Raw` at S16LE, four channels, 44.1 kHz; playback previously owner-confirmed | Last follow-up commands confirmed the default, not a fresh listening comparison |
| Original D+ quality | Owner preferred D+ Clarity v4 to earlier profiles and found it close to Big Sur | No proof of Apple DSP equivalence or speaker-protection certification |
| D+ prototype lifecycle | Multi-second A/V delay after pause/resume; after s2idle wake its output-flow watchdog fired and Raw was temporarily absent; selecting D as default tripped its deliberate guard and a restart loop reached `start-limit-hit` | Wake timing is correlated with the first failure, not a proved kernel root cause |
| D+ reference | Approved local Python engine inspected; 11 biquads and full FFmpeg chain extracted; five synthetic full-chain renders replicated on CachyOS | Engine/profile remain user-held, not released here pending provenance/licensing review |
| EQ math | Independent 44.1-kHz double-precision biquads matched FFmpeg (four cases; maximum observed error about `8.77e-14`) | **Not** a test of PipeWire output or the limiter |
| Clock/rate | Production PipeWire graph uses 48 kHz (allowed rates only `[ 48000 ]`), Raw hardware uses 44.1 kHz | Reusing 44.1-kHz filter coefficients at 48 kHz changes the EQ |
| 48-kHz EQ audit | Naive unchanged coefficients drift up to ~3.71 dB in sampled 20 Hz–5 kHz band; basic bilinear conversion is closer there but differs by ~2.13 dB at 18 kHz | Experimental high-frequency correction (~0.077 dB *calculated magnitude* error) is **not** a verified native processor or release candidate |
| Isolated PipeWire | Private server connection, metadata, filter-chain loading, and two test nodes all confirmed; 21 static smoke tests passed | In a private server without session management, both nodes stayed suspended and **zero Port objects** were published even with the opt-in activation probe; **no PCM was processed** |

**Decision (2026-10-23): stop iterating on the stripped-down private PipeWire smoke-test harness.** Its purpose—proving native filter-chain module availability—is complete. Its missing ports do not establish a defective `bq_raw` filter, bad hardware driver or production PipeWire incompatibility. Next development must deliver *actual audio*, not another node-enumeration report.

## 2026-10-24 handoff — first listenable prototype

The next step has changed from private PipeWire node-registration diagnostics to an **opt-in real-time listening trial**. A standalone `dplus-live-preview.py` proof-of-concept was prepared in the conversation and packaged for private owner testing; it is **not committed to this repository** until its actual first audio output and safe stop/recovery have been validated on the MacBook. [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) tracks its acceptance.

The experimental client runs `pipewire -c preview.conf` against the existing user PipeWire/WirePlumber session, exposing a temporary selectable output for **one manually routed application**. It generates 48-kHz-matched D+ EQ from the owner's locally held profile, an extra 3-kHz presence stage, and an **LSP Limiter Stereo LV2** candidate, then explicitly targets the four-channel `MacBook_Speaker_Raw` device with `L,R,0,0`. In development, the 11-filter magnitude response plus corrective filters matched the original with a maximum sampled error of about 0.0589 dB; six offline Python unit tests passed. **None of these tests proves live PipeWire audio, limiter dynamics, phase or physical safety.**

The preview deliberately omits the original +8.31-dB pregain, runs the limiter at unity input gain and reduced output gain (0.35), and includes a post-limiter hard clamp. It will sound **quieter than approved D+ v4**; it is not presented as an equivalent calibrated preset. The LV2 plugin may need the distro `lsp-plugins-lv2` package, but no package is installed automatically.

**Acceptance gate:** on the owner's laptop, confirm temporary output appears, one application can play through it, Raw stays default, startup/stop are reversible, and no unexpected distortion or delay occurs. Only then commit/refine it as an experimental supported repo workflow. Do not enable the old D+ service to test this.

### 2026-10-24 — KDE device selection versus application routing

Owner installed the LSP LV2 dependency and the downloadable first real-time preview successfully displayed `Ready: MacBook_Speaker_D_Preview`. On selecting the new output in KDE, the preview printed `STOP: System default changed; stopping trial`; its temporary output disappeared. This matches the preview's **deliberate guard**: it closes itself if the global default is no longer `MacBook_Speaker_Raw`. This is **not** proof of a DSP error or sleep failure. The reported logs do not distinguish exactly which KDE control was used, but selecting the output under **Output Devices** typically changes the global default.

**One-app audition:** keep the preview running, start audio playback in an app, then choose D+ only for that app under KDE's **Applications / Playback Streams** audio controls. **Do not** select D+ in KDE's global **Output Devices** list during this experimental trial. Keep Raw as the system default and stop with Ctrl+C. If the app routes correctly, the next acceptance question is whether audio is actually heard without undue latency/distortion. [Track outcome in Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39).

The finished D+ product must eventually be able to act as the global speaker default. This temporary prototype guard is a research safety measure and cannot simply be removed until we have verified that the final graph cannot loop back into itself.

### 2026-10-24 — First audible real-time preview confirmed

The owner confirmed **“works”** after following the per-application KDE routing instructions for the experimental `MacBook_Speaker_D_Preview` client. This is the first confirmed **live native PipeWire preview playback** on the MacBook through a selected application. The preview appeared earlier but stopped when chosen as KDE's **global** default; that shutdown is intentional. The later successful playback was achieved with the per-application selection method.

**Do not overstate this milestone:** the experimental preview is intentionally lower-gain and is **not** equivalent to the approved D+ v4 limiter or loudness. The owner has not yet reported objective A/V delay, matched sound quality, measured latency, long-playback stability, headphone behavior, or suspend/resume recovery. The experimental script is still a user-held bundle, not a validated installed package. Raw remains the intended default; the latest successful listening report did not separately reprint the default sink state.

**Next task (no new script):** while the preview is running, route a video player's audio **only for that application**, perform pause/resume and seeking repeatedly (initial small sample, then the planned 20-cycle test), check for any growing A/V delay or dropouts, and stop with Ctrl+C. Observe whether stopping removes the preview and normal Raw audio remains. Only after that should we refine the limiter, level, and automatic resume/default handling.

### 2026-10-24 — Playback feedback and controlled vocal-clarity trial

Owner reports the opt-in lower-gain D+ preview has been **working well so far, without noticed functional issues**; voices remain **very slightly muffled**. This is encouraging but not proof of long-duration sync, measured latency or exact D+ v4 dynamics.

The existing preview already includes an extra **+1.0 dB at 3 kHz** presence stage. A privately supplied experimental A/B variant (not yet in the repository) holds the 11 source biquads, 48-kHz correction filters, reduced-gain LSP limiter, final clamp, stereo-to-Raw `L,R,0,0` mapping, and default-selection guard unchanged. It permits just **+1.0 versus +1.5 dB** on the 3-kHz band. Six offline safety/graph consistency tests passed, but the brighter variant has **not** been listened to or validated on this MacBook.

The test should use the same speech excerpt and roughly matched loudness at modest volume, starting/stopping each variant separately (per-app KDE selector only, not global default). If the extra half-decibel does not clearly improve natural speech or causes sharp consonants, retain the already functioning +1.0 dB setting. A slightly muffled impression could also result from the intentionally lower gain rather than filter shape; do not increase global volume, driver gain, or the original +8.31 dB pregain as a shortcut.

### 2026-10-24 — Presence A/B verdict

The owner tested the +1.5 dB presence variant and preferred the **earlier +1.0 dB** D+ native low-gain preview (“before was better”). **Do not promote the +1.5 dB voice variant.** Preserve the exact earlier processing/limiter settings as the preferred listening baseline, while recognizing that perceived slight vocal muffling was not objectively traced to a specific EQ component. The owner has not approved additional EQ changes.

Return to the earlier per-app preview by stopping the A/B version with Ctrl+C and running `python3 ~/Downloads/dplus-preview/dplus-live-preview.py --profile ~/Downloads/dplus-v4-reference-profile.json --start`. Keep `MacBook_Speaker_Raw` globally selected. Resume/default reliability and formal latency/safety testing remain open; do not enable the old failed D+ bridge.

### 2026-10-24 — Resume-aware per-app experiment (pending real hardware validation)

A separate downloadable user-held experimental version of the **approved +1.0 dB lower-gain preview** has been prepared for one bounded sleep/wake test; it is **not installed** and not yet part of the tracked release scripts. Its DSP configuration generator is unchanged from the previously working one-app preview; nine offline recovery tests pass. On wake it attempts to recreate its **own temporary PipeWire client** after Raw returns, with a 30-second maximum wait and at most three attempts; the app may need to be reselected through KDE. It does **not** modify the global default, repair the codec/driver, alter WirePlumber, or auto-start at login.

**Release gate unchanged:** owner must confirm audio before and after wake, no feedback, and safe Ctrl+C cleanup. The observed prior disappearance after suspend was with the previous/old configuration and cannot be treated as proof of failure or success for the newly prepared preview. Original known-working preview remains available for rollback; the old D+ FFmpeg bridge stays disabled.

### 2026-10-24 — Actual resume failure and narrowly targeted fix

Owner reproduced a failure with the first experimental resume-aware preview: it detected sleep/wake but then exited because `pactl list short sinks` returned status 1 during recovery. Source inspection revealed the original code retried temporary `pactl` failures while waiting for Raw, but made additional **unprotected** `pactl` calls while launching and observing the replacement D+ sink. A transient failure after the first successful Raw check could still terminate the preview. The exact failing call cannot be pinpointed without a traceback; this is a source-supported explanation, not a proven final hardware diagnosis.

A separate privately downloadable **v2** script addresses this gap without changing DSP or system audio configuration. It waits for Raw to be the default, retries transient command errors while waiting up to 12 seconds for its own replacement sink, and retains 30-second Raw readiness and three-recovery ceilings. Fifteen unit tests passed offline; the new full DSP configuration text is byte-for-byte identical to the previously audible +1.0 dB preview. **It has not yet been validated through a real wake cycle.** The old v1 script remains an available fallback and is not overwritten.

Application routing is still a separate problem: KDE may move an application back to Raw when the transient preview sink disappears. Successful restart of the D+ client would not yet restore that application's per-stream selection. Do not change the global default or re-enable the obsolete FFmpeg service as a workaround.

### 2026-10-24 — v2 wake report and restricted v3 default-restoration option

With v2 the owner saw D+ start and detect sleep/wake, then exit: `STOP: System default changed away from Raw; stopping preview`. In the v2 source this string is emitted in the **replacement sink readiness loop** (`wait_for_preview_seen`), after waiting for Raw initially. The actual unexpected default was **not logged**. WirePlumber can restore user-selected default outputs on device reappearance, so startup order is a plausible explanation, not a confirmed culprit.

An opt-in, **user-held v3 ZIP** has been prepared in the conversation (not in this repository as a release). It preserves the exact preferred +1.0 dB low-gain D+ DSP graph, adds the precise unexpected default to error messages and supports `--restore-raw-on-wake`. With that flag, during detected wake recovery **only**, it may issue `pactl set-default-sink MacBook_Speaker_Raw` **once** if Raw is present and the newly selected default is **exactly its own temporary D+ preview**. It must never override headphones/Bluetooth/USB/HDMI or an intentional other selection. Without the flag the script changes no default. Because WirePlumber remembers manual default selections, this opt-in may update the persisted preference to Raw. 21 offline tests passed; **hardware validation remains outstanding**.

The safe default remains the old native preview using per-application KDE routing, not enabling D+ as global default. On any further failure, use the exact reported sink name to decide whether this is transient preview selection or an entirely different output-routing problem. No new driver or EQ changes are justified by these logs.

### 2026-10-24 — v3 first real sleep/wake restart: script reports success

Owner ran the opt-in v3 resume script and it remained running after reporting `Detected sleep/wake transition` and `D+ preview recreated after recovery. Re-select your application output in KDE if needed.` This is the first owner-observed **completion of the restart path after sleep**, unlike earlier v1/v2 fatal shutdowns. The test has **not yet confirmed that the user can hear D+ after wake** or that the app stream is routed back to the preview rather than Raw. Keep the existing +1 dB DSP and Raw default unchanged; the next acceptance check is to select D+ again for the individual application's playback stream and confirm the audio source by listening.

### 2026-10-24 — v3 temporary output confirmed after physical wake

After the v3 script reported successful recreation, the owner ran `pactl get-default-sink` and `pactl list short sinks`: global default remained `MacBook_Speaker_Raw` (RUNNING at S16LE/4ch/44.1 kHz), and `MacBook_Speaker_D_Preview` was **present** again (SUSPENDED at float32/2ch/48 kHz). This independently confirms successful output reappearance on the actual laptop after wake without manually restarting the Python process. SUSPENDED can be normal for an idle output. **Still to verify:** manually route a playing app to D+ again and hear the D+ processing after wake; automatic stream routing and recurring resume reliability remain open. Details in [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39).

### 2026-10-24 — Correction: restored sink is silent after wake

The owner followed up: although v3 remained running and PipeWire listed `MacBook_Speaker_D_Preview` again, **there is no audible D+ sound when attempting playback after wake**, and the preview sink stays SUSPENDED. **Previous wording implying successful end-to-end recovery was premature.** Only wake detection and sink recreation have been demonstrated; the audio graph is not confirmed functional after resume.

Inspection of v3's generated `playback.props` shows `target.object=MacBook_Speaker_Raw`, `node.passive=true`, `node.dont-fallback=true`, `node.dont-move=true`, and `node.dont-reconnect=true`. The replacement client currently considers startup successful when the **preview sink name appears**, not when its Raw playback stream is actually linked. WirePlumber's documented `node.dont-reconnect` behavior makes lost target relinking after device recreation plausible, but the exact failed edge is not yet known.

**Next narrowly scoped diagnosis with audio playing:** compare the app's sink ID in `pactl list short sink-inputs` with `pactl list short sinks`, and inspect `pw-link -lI` for links involving `MacBook_Speaker_D_Preview`, `dplus_preview_to_raw`, and `MacBook_Speaker_Raw`. If the app→D+ edge is absent, address stream routing; if the D+→Raw link is absent, address filter-chain output reconnection. Do not keep changing the v3 script on guesses. Keep Raw as default and stop the experimental child with Ctrl+C when finished.

### 2026-10-24 — Resume graph narrowed: Firefox bypasses D+ despite restored bridge

The owner supplied the PipeWire link graph after waking with the v3 preview. Sink 69 `MacBook_Speaker_Raw` is RUNNING, sink 2912 `MacBook_Speaker_D_Preview` is SUSPENDED. Every `pactl list short sink-inputs` entry targets **69**, not 2912; `pw-link -lI` independently shows Firefox ports linked **directly to Raw**, alongside working `dplus_preview_to_raw:output_*` links to Raw. Thus the immediate issue visible in the snapshot is **application input is not reaching the restored D+ sink**; the output-to-Raw link has actually reappeared. A SUSPENDED D+ sink without clients does not by itself show a broken DSP.

**Next test is direct, per-app routing only:** identify one active Firefox sink-input by `pactl list sink-inputs` and move only that entry via `pactl move-sink-input <id> MacBook_Speaker_D_Preview`. Confirm its sink ID changes to 2912 and listen; if KDE/WirePlumber moves it back, capture that. Never move the `dplus_preview_to_raw` return stream into its own preview sink (feedback danger). Global default remains Raw; reversibility: `pactl move-sink-input <id> MacBook_Speaker_Raw`. No speculative filter or HDA changes needed at this stage.

### 2026-10-24 — Confirmed post-wake routing bypass

The owner's read-only graph confirms that **all five sink-inputs target Raw sink 69**, not the recreated D+ sink 2912. `pw-link -lI` confirms the `dplus_preview_to_raw` output ports are in fact linked to Raw and that Firefox ports are likewise linked **directly to Raw**. Therefore an absent D+→Raw connection is **not** the observed cause of the silence in this snapshot; D+ is SUSPENDED because it has no demonstrated application input. The next controlled test is to identify one Firefox playing stream and explicitly `pactl move-sink-input <id> MacBook_Speaker_D_Preview`, verify the sink ID becomes 2912, and listen. Do not move D+'s own output bridge to D+, or change the global Raw default. See [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) for the full evidence.

### 2026-10-24 — Firefox move rejected or reverted after wake

The owner identified playing Firefox sink-input 4351, attempted `pactl move-sink-input 4351 MacBook_Speaker_D_Preview`, then found it **still mapped to Raw sink 69**, with D+ 2912 still **SUSPENDED** and reported no audio. A manual move is therefore insufficient; whether WirePlumber undid it or the node couldn't accept the stream is not yet established. The D+ output-to-Raw link was already visible in the previous graph. **Next controlled test:** restore Firefox to Raw, stop v3 via Ctrl+C, check basic Raw playback, then start the exact same v3 script again while fully awake and route one app to it. This distinguishes the after-wake reinstantiation state from a general session routing failure without another code change.

### 2026-10-24 — Plasma tray virtual-device visibility

Owner observes D+ in **System Settings → Sound** but not in tray Audio Volume's per-application destination menu or device list. KDE Plasma's tray widget can **hide virtual outputs by default**, independently of the backend `pactl` list; KDE provides **Show virtual devices** via the tray audio popup menu (sometimes the hamburger) or right-click speaker → Configure Audio Volume. See [KDE's discussion](https://discuss.kde.org/t/simultaneous-audio-output/6274) and [matching Plasma 6 bug report](https://mail-archive.com/kde-bugs-dist%40kde.org/msg906610.html). First enable this UI setting and reselect D+ for the playing Firefox stream. Do **not** use the global-default selector or change audio filters. This may resolve the missing option but has **not yet proved the failed manual move and post-resume silence are fixed**; check audible playback and stream target before marking recovery functional.

### 2026-10-24 — Native graph activation bug: PipeWire copy fan-out required

**Do not interpret the post-wake problem as solely a KDE routing issue.** Owner's latest v3 terminal log includes `spa.filter-graph: output port clipL[0]:Out already used by link, use copy`, followed by `pw.stream: error (-16) can't start graph: Device or resource busy`. Reading the original v3 `generate_config` demonstrates that both `clipL:Out` and `clipR:Out` are consumed twice: once as a graph output (FL/FR) and once by internal links feeding the zeroed rear channels. PipeWire's [filter-chain specification](https://docs.pipewire.org/page_module_filter_chain.html) explicitly requires a builtin `copy` for branching. [Its own LFE example](https://github.com/PipeWire/pipewire/blob/master/src/daemon/filter-chain/sink-make-LFE.conf) confirms how to tee copy outputs. Earlier offline graph checks missed actual activation.

**User-held targeted repair, hardware untested:** an experimental bundle `dplus-pipewire-graphfix-experimental.zip` modifies only the generated topology: `clipL→copyL→(FL output, zeroL)` and `clipR→copyR→(FR output, zeroR)`. All DSP coefficients, preferred +1.0 dB presence, conservative limiter/clamp, four-channel L,R,0,0 physical format, fixed `MacBook_Speaker_Raw` playback target, and prior resume supervisor remain unchanged. Regression checks prove the originally invalid double-consumer ports and their corrected copy-node fan-outs; no live MacBook PipeWire run has been performed with the repaired graph.

**New next step (do not involve KDE selector):** stop old v3, launch corrected native preview with Raw as global default, then direct a bundled quiet 2-second sample to `MacBook_Speaker_D_Preview` via `pw-play --target=MacBook_Speaker_D_Preview ~/Downloads/dplus-graphfix/quiet-check.wav`. This directly checks active DSP processing, without KDE unexpectedly selecting D+ globally. Capture an exact client log if `pw-play` errors or is silent. No default/suspend tests until direct sample playback works.

**Long-term design change:** once the audio graph proves functional, stop adding layers to the disposable preview. Implement a persistent PipeWire filter-chain output under user-session management and a WirePlumber speaker-specific default policy that never feeds its own output back into itself, respects external headphones/Bluetooth, recovers from wake, and provides explicit rollback. Wrap installation and on/off/diagnostics in a GUI rather than requiring nontechnical Mac users to run terminals. This is an architectural plan, not yet implemented, and any future default switch must be tested and reversible.

### 2026-10-24 — Graph-fixed preview: silence in direct PipeWire audition

After the proposed `copyL`/`copyR` graph topology correction, owner reports `pw-play --target=MacBook_Speaker_D_Preview ~/Downloads/dplus-graphfix/quiet-check.wav` **does not produce an audible tone**, although Audacity plays the WAV. D+ is still visible in System Settings but not in the Plasma tray. Raw is selected globally; the owner perceives normal playback as D+-like, but previous PipeWire link reports show another `MacBook_Speaker_DSP_Out` also feeding Raw, so sound character and default selection cannot establish that the new preview actually processed samples. **Graph fix has NOT passed hardware-audio acceptance; don't claim success**.

The bundled 550 Hz tone's peak is only **0.04498** (about −27 dBFS); the preview limiter's conservative `g_out=0.35` reduces it by about another 9 dB at this frequency, suggesting a ~−36 dBFS peak before speaker volume. **Inaudibility alone remains ambiguous**: target-link failure, active graph error, or a tone that's simply too quiet. Upstream `pw-play --target=<node.name>` is syntactically correct; the script's `Ready` is still only a sink-name registration check, not verification of PCM activation.

**Do not create another script revision on this evidence.** First compare the identical WAV using `pw-play --target=MacBook_Speaker_Raw ~/Downloads/dplus-graphfix/quiet-check.wav` at ordinary listening volume. If Raw also inaudible, the sample/test method is weak; if Raw audible and D+ inaudible, inspect filter-chain client stdout/stderr and the real playback link while the stream is active. Keep Raw default, no wake/default tests, and stop the opt-in preview with Ctrl+C. Add a genuine running PCM/link acceptance test before promoting any future `Ready` result. [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) tracks this.

### 2026-10-25 — Both D+ graph links exist, DSP still silent

The owner's 20-second loudness-controlled direct playback test supplied the missing `pw-link -lI` evidence: **`pw-play` FL/FR connected to `MacBook_Speaker_D_Preview` FL/FR, and all four `dplus_preview_to_raw` playback channels connected to `MacBook_Speaker_Raw`.** The current `pactl` stream mapped to D+ sink ID 7375 and Raw stayed default. The WAV remained inaudible through D+ but had previously played through Raw. **This disproves the earlier suggestion that D+ silence was because of a missing input or output PipeWire link, or because `node.autoconnect=false` prevented this particular stream's attachment.**

**Do not patch KDE selection, `node.autoconnect`, the driver, or resume supervisor based on this case.** A *linked and streaming* graph can still fail to activate its filters or produce silence. The existing script hides the private child logs in its owned temporary directory under `/tmp/dplus-live-resume-preview-*/client-1.log` until the owner ends the session. **Next concrete step: read that already-written log while graphfixed preview is running**, paying attention to filter-graph setup, LSP LV2 load/control/port errors, and any `pw.stream` state failures. The live client log can be printed without changing anything using `find /tmp -maxdepth 2 -path '/tmp/dplus-live-resume-preview-*/client-*.log' -type f -print -exec tail -n 100 {} \;`. Do not ship another revised ZIP based on unsupported guesses. An actual **nonzero PCM and level** check, not `Ready` or mere sink/link presence, is required before promoting any implementation. [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) tracks acceptance.

### 2026-10-25 — Decisive root cause: copy output still double-used

Owner supplied the private-client logfile from the graphfixed native preview, confirming the **actual runtime graph error**: `output port copyL[0]:Out already used by link, use copy` and `can't start graph: Device or resource busy`. This proves the earlier `clipL` → `copyL` patch **did not fix the topology**; it still used `copyL:Out` simultaneously as the graph's FL output and as an internal link feeding `zeroL`. Live `pw-play` and physical Raw connections therefore showed both graph edges while the filter processing itself failed. Earlier checks were structurally inadequate because they allowed this port collision.

Following [upstream PipeWire LFE topology](https://github.com/PipeWire/pipewire/blob/master/src/daemon/filter-chain/sink-make-LFE.conf) and the [filter-chain specification](https://docs.pipewire.org/page_module_filter_chain.html), a privately downloaded test ZIP `dplus-graph-topology-corrected-experimental.zip` changes the graph to two copies per side: the internal tee `copyL:Out` feeds **only internal consumers** `zeroL:In` and `copyOutL:In`; graph FL exits solely from `copyOutL:Out`, RL from `zeroL:Out` (and R similarly). It adds a static regression requirement **no filter.graph.outputs port may also be a link source**, and makes the Python user-facing status explicitly say sink registered ≠ audio verified. Fatal previously observed graph-activation errors in the child logfile will now be surfaced. All D+ audio gain, EQ, limiter, speaker-channel map and Raw target remain unchanged.

The package includes an unambiguous 20-second moderate test WAV and local topology/self-checks that pass. **This is not a confirmed live sound fix**, because the test machine lacks PipeWire and a MacBook CS4208. Next test is precisely one owner-controlled `pw-play --target=MacBook_Speaker_D_Preview` audition while the fixed graph is running, keeping Raw default and avoiding KDE UI and suspend tests. Successful output would be the first required acceptance gate; later use a persistent PipeWire/WirePlumber speaker-specific design and accessible GUI, not more Python preview layers. Prior repository assumptions that any “Ready” meant live DSP were invalid.

### 2026-10-25 — Corrected topology AUDIBLE on actual MacBook

**Owner-confirmed hardware result:** the latest standalone `dplus-graph-topology-corrected-experimental.zip` produces **audible sound** from its 20-second test WAV sent directly with `pw-play --target=MacBook_Speaker_D_Preview`. This is the first on-device confirmation that the two-stage copy topology (`copyL` internal tee → `copyOutL` dedicated graph output, mirrored right) can successfully start and deliver audible PCM to the MacBook's speakers. The previous experimental graph revisions produced PipeWire runtime errors on activation and silent playback despite exposed sinks and links.

**Scope:** do not infer exact D+ v4 sonic/limiter parity, normal Firefox/KDE stream routing, audio/video latency, persistent default selection or suspend/resume recovery from one audible tone. The original owner-preferred +1 dB presence and conservative gain-limited DSP were unchanged by the topology repair. The test ZIP is still experimental and user-held; no production persistent service or GUI installer exists.

**Next gate with frozen DSP:** audition a brief real speech/music excerpt using the exact same corrected preview and `pw-play --target` WAV approach at comfortable volume. No further graph rewrites or resume-script iterations absent new evidence. Once ordinary content is proven through D+, prioritize a stable declarative PipeWire filter-chain and safe WirePlumber speaker-default policy with a one-click GUI installer, always retaining Raw as rollback.

### 2026-10-25 — Real music playback through corrected native D+

Owner reports **“works”** after using the existing `dplus-topology-preview.py` and directly targeting its sink with a familiar 30-second MP3 excerpt converted to 48-kHz stereo WAV (`pw-play --target=MacBook_Speaker_D_Preview`). Together with the previously audible 20-second tone, this confirms **real musical PCM reaches the speakers through the two-stage-copy PipeWire graph** on the actual MacBook8,1. This is more substantial than mere registration or a static graph test. Preserve this exact working topology and the owner-preferred **+1.0 dB presence setting**. Do not change the DSP to solve lifecycle problems.

**Boundaries:** the ephemeral preview is not a supported always-on product. Its direct `pw-play` route bypasses KDE. Normal-app routing, relative loudness, full D+ v4 limiter dynamics, long-session A/V sync, default-device safety, sleep recovery and recovery from PipeWire/WirePlumber restarts are not validated for this corrected graph. Earlier resume candidates had broken graph topology and must not be promoted.

**Delivery plan:** (1) capture the working generated filter-chain topology into an installed, managed, persistent *user-session* PipeWire unit with the same Raw playback target and safe stop/cleanup; (2) verify ordinary per-app music/video with Raw system default, and one wake without moving the global default; (3) implement an opt-in WirePlumber speaker-default strategy that avoids feedback and respects headphones/Bluetooth, with rollback; (4) build a GUI installer with safe Test/Enable/Use Raw/Restore controls, rather than requiring terminal interaction. The known-good Raw and the disabled legacy FFmpeg D+ bridge remain preserved.

### 2026-10-25 — Pinned native user-service candidate in GitHub

The exactly owner-audible corrected graph source is now in `scripts/dplus/dplus-topology-preview.py`, pinned by SHA-256 `105a8bd171248a1ec0707bfc552d8dfebe4bdd8f65873af071f67e190c8862c2`. A new `scripts/dplus/manage-native.py` locally renders the DSP config from the private profile and installs an **off-by-default** supervised `macbook81-dplus-native.service`. The service keeps the Raw-targeted processing client alive across terminal closure when manually started, has `Restart=no`, and stops rather than changing the global default or connecting to an unexpected sink. Eight simulated install/rollback/graph tests passed. This implementation has **not** yet passed the first manual `start`/sound/`stop` acceptance test on the MacBook, and **does not** provide reliable resume or automatic default selection yet. It neither modifies the patched HDA driver nor commits the private reference profile. Full instructions: [native D+ service and removal](dplus-native-service.md). Issue #39 tracks the remaining hardware gates.

## Approved D+ v4 reference contract

The owner-supplied `macbook81-dplus-engine-reference.py` (SHA-256 `43da928c7b1b7cd1b1628e47276820dcb2eeeeb841136a425ea25d280ec4076b`) implements:

```text
stereo float32, 44100 Hz
 → 11 ordered biquads / channel (FFmpeg f64, transposed DF-II)
 → +1 dB peaking EQ at 3000 Hz, Q=1
 → +8.31 dB pregain
 → 176400-Hz double-precision resampling (4×)
 → FFmpeg alimiter: limit=0.6683439175686147, attack=5 ms,
   release=80 ms, linked stereo; automatic level disabled
 → 44100-Hz resampling → -0.01 dB final trim
 → L,R,0,0 (four-channel S16LE, 44100 Hz; no dither)
 → MacBook_Speaker_Raw
```

The high pregain **must never be used without a verified limiter and headroom checks**. The exact 11 coefficient rows remain in the private extracted reference JSON; neither they nor the engine are currently packaged as redistributable release assets. Equal displayed volume percentages across macOS and CachyOS are not a calibrated loudness comparison.

## Architecture decision

**Keep driver and sound processing separate.**

- **Hardware layer:** retain the working three-module `macbook12-audio/0.1` CS4208 DKMS setup, mixer behavior and Raw sink. Fixes to hardware initialization, clock state, amplifier routing and kernel updates belong in [driver issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2) and [audio recovery](audio-update-recovery.md).
- **D+ layer:** prefer a real-time PipeWire/WirePlumber-compatible processing path using an existing maintained DSP/LV2 implementation where feasible. Use a small native plugin **only if** needed to reproduce the limiter or an essential real-time property. Do not return to the fragile `parecord → FFmpeg → pacat` bridge for production.
- **Rate contract:** keep the normal PipeWire 48-kHz system graph stable. Evaluate either **(A)** a measured 48-kHz response-matched DSP and limiter, or **(B)** properly isolated 44.1-kHz DSP with bounded resampling. Choose by measured audio parity, CPU use and latency, **not** by a frequency plot alone.
- **Routing:** initial output must be **manual, per-application, opt-in**, with safe mapping to Raw. Never stack upstream EQ or duplicate rear channels. Default-device selection and system volume integration are later work.

## Work plan — acceptance gates

Treat a checkbox as complete **only when the deliverable was observed**, not merely when a diagnostic script passed. Use [issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) for ongoing checkboxes and ownership.

### A. Preserve the known-good state — mostly complete

- [x] Verify current installed DKMS module files and working `MacBook_Speaker_Raw` routing.
- [x] Disable the failed old D+ user unit and confirm `disabled`/`inactive` and Raw as default.
- [ ] Confirm ordinary Raw speaker playback at modest volume after the latest changes; document a known-good kernel and fallback procedure.

**Gate:** known-good Raw output and a tested return path. Do not alter Limine, HDA modules or speaker GPIOs to develop D+.

### B. Freeze reference audio — mathematical baseline complete

- [x] Recover and inspect approved v4 engine and full filter order; preserve source digest.
- [x] Reproduce five offline full-chain synthetic cases on CachyOS, including silence, isolated left/right impulses, and quiet/loud signals; rear outputs exactly zero.
- [x] Reproduce 44.1-kHz biquad-only math on CachyOS; run 48-kHz response-drift audit.
- [ ] Add representative level-matched reference material, aligned impulse/transient checks, true-peak and limiter-response comparisons; review source/plugin attribution.

**Gate:** reproducible full-profile audio benchmarks with objective headroom and dynamics measurements, not just EQ magnitude.

### C. Deliver ONE listenable native D+ prototype — next priority

- [ ] Select and document the real-time host/limiter and version; check whether it can reproduce the FFmpeg limiter well enough.
- [ ] Resolve 48-kHz graph / 44.1-kHz Raw rate handling with measured response, phase, dynamic and latency parity. Avoid shipping the naive conversion.
- [ ] Build a **complete** opt-in processing chain: 11 biquads, +1 dB presence, bounded gain + working limiter, stereo output and explicit `L,R,0,0` Raw mapping.
- [ ] Produce an actual per-app listening A/B on the MacBook with one reproducible start/stop command and no persistent default change.
- [ ] Capture and compare processed PCM against the approved reference; measure clipping/peaks, CPU demand and end-to-end latency.

**Gate:** audible, safe, bounded-latency D+ playback on real hardware. If this approach cannot deliver actual PCM without more infrastructure churn, stop and switch DSP architecture instead of making another smoke harness.

### D. Stabilize actual playback

- [ ] Confirm owner-approved sound vs D+ v4 and Raw at matched levels.
- [ ] Run at least 20 pause/resume/seek video cycles, 30 minutes continuous playback and A/V alignment measurements relative to Raw; **no growing delay**.
- [ ] Confirm modest-volume behavior, no uncontrolled gain/clipping, and reasonable CPU/xrun results on Core M hardware.
- [ ] Verify stop/crash cleanup, PipeWire restart, lid suspend/resume, and headphone/Bluetooth handling without taking over other devices.

**Gate:** reproducible sound parity (or explicit owner acceptance of measured differences) and reliable video synchronization.

### E. Default output, packaging and maintenance — only after C/D pass

- [ ] Implement WirePlumber/KDE preferred internal-speaker output, normal volume keys, explicit fallback to Raw and respect for headphones/external devices.
- [ ] Verify three cold boots, login/logout, five suspend/resume cycles, failure recovery and a kernel update on hardware.
- [ ] Provide reversible `check/install/verify/uninstall` workflow; audit DSP and driver licensing, ownership and clean-install safety.
- [ ] Update README hardware status only after tests; release the first **opt-in** package before recommending D+ as default.

**Gate:** user does not need to start D+ manually and can always return to working Raw without rebuilding drivers.

## Operational safety and rollback

The old prototype intentionally **refuses to be the system default** and has a known transport latency/restart failure. Do not enable it for this plan:

```bash
systemctl --user is-enabled macbook81-dplus.service
systemctl --user is-active macbook81-dplus.service
pactl get-default-sink
```

Expected baseline: `disabled`, `inactive`, `MacBook_Speaker_Raw`. If the old prototype is unexpectedly active, stop and disable **that exact unit**:

```bash
systemctl --user disable --now macbook81-dplus.service
pactl set-default-sink MacBook_Speaker_Raw
```

This doesn't delete its local code or rebuild HDA. For any new D+ test, prefer an isolated per-app manual selector and provide a verified stop/cleanup operation **before** activation. Do not unload unknown PipeWire modules, force global sample-rate changes, run an unreviewed Ubuntu-oriented root installer, or replace a working kernel.

## References and maintenance

- [Offline D+ tests and experimental isolated PipeWire research](dplus-offline-testing.md) — **historical technical evidence, not the next required workflow**.
- [Audio-update recovery](audio-update-recovery.md) and [source packaging blockers](audio-packaging.md).
- [Earlier listening / speaker-tone work](https://github.com/ltorrecilla/macbook8.1/issues/1).
- [Implementation task tracker](https://github.com/ltorrecilla/macbook8.1/issues/39).

The previous multi-revision experimental diagnostics remain in Git history. Keep the repository small; **do not add more diagnostic-harness revisions** unless required to deliver an end-to-end audio output or to investigate a newly observed fault. Real hardware acceptance remains separate from simulated unit tests.
