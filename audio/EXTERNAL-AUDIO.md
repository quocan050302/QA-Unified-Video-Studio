# External audio

| Cue | Original | License | Changes |
| --- | --- | --- | --- |
| `external_dark_fog` | [Dark Fog by Kevin MacLeod (incompetech.com)](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1300031) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | First 41 seconds, fade-out, converted to mono 48 kHz PCM WAV |
| `external_gravel_step` | [Footstep on Gravel by Mildly Useless](https://mildlyuseless.com/res/foley-footstep-gravel) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Converted to 48 kHz PCM WAV |
| `external_water_drops` | [Drops of water #1 by Joseph Sardin / BigSoundBank](https://bigsoundbank.com/drops-of-water-1-s1384.html) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Converted to 48 kHz PCM WAV |

Include the Dark Fog credit and license link when sharing a video that uses it.
The Squire sample uses Dark Fog for its first music bed and the gravel cue in
its opening shot. Water drops are available for other projects.

Use the music ID as the storyboard's `music[].bed` and the SFX IDs as a
shot's `sfx[].name`. A shot's `sfx[].at` is relative to its start.
