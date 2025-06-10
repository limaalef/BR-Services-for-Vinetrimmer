![GitHub last commit](https://img.shields.io/github/last-commit/limaalef/BR-Services-for-Vinetrimmer?logo=github)

# BR Services for Vinetrimmer

This repository provides a collection of services for use with Vinetrimmer, focused on brazilian streamings, but not limited to them. I created from scratch or improved scripts that I found floating around web. If I just adapted a pre-existing code, the credits will be inside code.

> [!WARNING]
> All codes contained here DO NOT work standalone.
> It may be used inside a version of Vinetrimmer.
> All services were written and tested using the version maintained by [chu23465](https://github.com/chu23465/VT-PR).

## Usage

If your VT version doesn't recognize automatically the services, you must add these lines in the `__init__.py` file located inside `services` folder:

```python
from vinetrimmer.services.f1tv import F1tv
from vinetrimmer.services.meliplay import Meliplay
from vinetrimmer.services.maissbt import MaisSBT
```

---

## F1 TV
##### Version 1.0.0

```bash
poetry run vt dl --alang pt,en --slang en -r HDR -q 2160  F1TV 1000009032
```

> - gets portuguese audio and english audio + subtitle,
> - selects the 4K + HDR track,
> - from F1TV,
> - title-ID is 1000009032.

**How to Use:**  
- Login and extract cookies from any page and save to path `vinetrimmer\Cookies\f1tv\default.txt` (Case sensitive).
- Supported alias: `F1TV` and `F1`
- Either the full URL or just the content ID are supported.
- However, you will need to enter the URL for each session, as race weekend URLs are not yet supported.
- Commands `-al/--alang` and `-sl/--slang` are fully supported, use as you want.
- When you use the `-r HDR` or `-q 2160` command, if the content has DRM, it will respond as a stream with ClearKey and your VT version needs to support this.

---

## Globoplay
##### Version 1.0.0

```bash
poetry run vt dl -q 2160 --alang pt GLOBOPLAY https://globoplay.globo.com/v/13655941/
```

> - selects the 4K track,
> - gets portuguese audio,
> - from GLOBOPLAY,
> - title-ID is 13655941.

**How to Use:**  
- Login and extract cookies from any page and save to path `vinetrimmer\Cookies\Globoplay\default.txt` (Case sensitive).
- Supported alias: `GLB`, `GLOBO` and `GLOBOPLAY`
- Either the full Globoplay's URL or just the content ID are supported.
- Commands `-al/--alang` are fully supported.
- Use command `-q 2160` to get UHD content.

---

## Meli Play

> [!NOTE]
> In my tests, all countries served by Meli Play are supported. But feel free to open an issue if it doesn't work properly.
##### Version 1.0.0

```bash
poetry run vt dl -aleng pt,en --slang pt,es -w S01E12 MELI -s --no-cache https://play.mercadolivre.com.br/assistir/piloto/a61052a39bc44bdf8854b2cc3d1668a8
```

> - gets portuguese and english audio,
> - gets portuguese and spanish subtitles,
> - selects episode 12 from season 1,
> - from MELIPLAY,
> - gets all episodes from that season,
> - make news requests instead using cached,
> - title-ID is a61052a39bc44bdf8854b2cc3d1668a8.

**How to Use:**  
- Login and extract cookies from any page and save to path `vinetrimmer\Cookies\Meliplay\default.txt` (Case sensitive).
- Supported alias: `MELI`, `MELIPLAY` and `MLPLAY`
- Commands `-al/--alang` and `-sl/--slang` are fully supported, use as you want.
- If the content has several episodes and/or seasons, you must use the personalized commands to get all content:

Below flags to be passed after alias or URL in command.

|  Command Line Switch                | Description                                    |
|-------------------------------------|------------------------------------------------|
|  -s, --season       | Get all episodes matching the season of that episode from URL  |
|  -as, --all-seasons | Get all episodes from all season from that show (It may take a few minutes to process) |
|  --no-cache         | Make new requests instead of using cached requests             |

> [!IMPORTANT]
> When using `-s` or `-as`, all requests will be cached and used for the next 2 days. If the cached request
> is older than 2 days, it will be replaced with a new one. You can use `--no-cache` as it wants new requests.

---

# Contribution

Feel free to open issues or submit pull requests if you have suggestions or improvements for any of the services.
