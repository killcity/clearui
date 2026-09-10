# HF Listen — C9b test build

Experimental upper-HF listening for the **stock UV-K1**. This is a local test
feature, not a claim of validated HF performance or a replacement for a dedicated
shortwave receiver. The existing public C8c release is unchanged.

Open **Main menu → Radio → HF Listen**, or **Quick menu → HF Listen**.

## Controls

| Key | Action |
| --- | --- |
| Menu | Open the ham-band picker; press again to confirm a selection |
| Hold Menu | Open HF settings (receive mode and bandwidth) |
| Left / right | Tune down / up by 100 Hz; hold for repeated 5 kHz moves |
| Left / right in a menu | Previous / next option |
| Scan (`*`) | Switch between sweep and listening at the selected frequency |
| PTT | Same receive-only listen/sweep shortcut; does not transmit in HF Listen |
| Exit in a submenu | Cancel and go back |
| Exit while listening | Resume sweeping |
| Exit while sweeping | Leave HF Listen and restore the normal receiver |

The compact band picker shows all four bands together. Holding Menu opens
**Receive mode** (FM, AM, USB) and **Bandwidth** (25, 12.5, 6.25 kHz) in a separate
settings window. Opening a menu pauses the sweep. Selecting a band, mode or
bandwidth returns to sweeping; cancelling leaves the selection unchanged.

## Display and receiver limits

- Spectrum trace above the monochrome, density-dithered waterfall.
- One compact ClearUI status bar: HF, band, receive mode, Sweep/RX pill and
  the same saved battery display preference as the main VFO screen.
- Large frequency uses the existing ClearUI VFO font, with four decimal places
  to show 100 Hz tuning. Band-picker text uses the existing menu font.
- Both use the same frequency axis and sweep data; the dotted marker identifies
  the selected listening frequency. At band edges, the marker moves because the
  sweep remains inside the selected band.
- Nominal 32 kHz span: 64 samples at 500 Hz spacing, spanning 31.5 kHz between
  endpoints. This is a swept RSSI display, **not an FFT or 500 Hz resolution
  receiver**. The analog filter limits separation of nearby signals.
- New waterfall rows appear only after completed sweeps. While listening, history
  freezes; the radio cannot continuously sweep and receive audio simultaneously.
- Retuning clears old history so it cannot be relabeled with new frequencies.
- USB and 6.25 kHz are the entry defaults. This does not add LSB, a new demodulator,
  extra RF hardware, lower-HF coverage, or digital-mode decoding.
- The stock antenna and receiver front end limit actual reception. Signal traces
  can include noise, interference and receiver artifacts.

The four listening presets are 17 m (18.068–18.168 MHz), 15 m (21–21.450 MHz),
12 m (24.890–24.990 MHz), and 10 m (28–29.700 MHz).
Band-edge reference: [ARRL frequency bands](https://www.arrl.org/frequency-bands).
These are receiving presets, not a grant of transmitting privileges.

No channel memories, scan-list memberships, calibration, EEPROM layout, or CHIRP
ABI changes are required. Use the existing ClearUI C8 CHIRP driver. HF band choice
is retained only until reboot; normal scope settings/ranges are preserved.

## Validation

Host tests cover band-edge tuning and sweep bounds, selector commit/cancel,
held-key isolation, receive-only PTT dispatch, explicit sweep/listen transitions,
normal scope setting restoration, and framebuffer bounds under sanitizers.
They also cover short/held Menu isolation, the four-band window boundary,
and battery preference rendering without overwriting the receive-state pill.

Hardware validation is still required: enter from either VFO, try all four bands,
tune both directions, change modes/filters, verify sweep/listen audio behavior,
exit back to the original channel, and confirm normal scope operation afterward.
Follow [equipment-risk and lawful-operation guidance](SAFETY.md).
