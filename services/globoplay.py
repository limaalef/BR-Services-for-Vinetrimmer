import json
import click
from vinetrimmer.objects import AudioTrack, TextTrack, Title, Tracks, VideoTrack
from vinetrimmer.services.BaseService import BaseService
import m3u8

class Globoplay(BaseService):
    """
    Service code for Globoplay (https://globoplay.globo.com/).

    \b
    Authorization: Cookies 
    Security: UHD@L3, doesn't care about releases.
    """

    ALIASES = ["GLB","Globo","Globoplay"]

    TITLE_RE = [
        r"^https?://globoplay\.globo\.com/(?:v|[^/]+/[^/]+)/(?P<id>\d+)",
    ]

    AUDIO_CODEC_MAP = {
        "AAC": "mp4a",
        "AC3": "ac-3",
        "EC3": "ec-3"
    }

    @staticmethod
    @click.command(name="Globoplay", short_help="https://globoplay.globo.com/")
    @click.argument("title", type=str, required=False)
   
    @click.pass_context
    def cli(ctx, **kwargs):
        return Globoplay(ctx, **kwargs)

    def __init__(self, ctx, title):
        super().__init__(ctx)
        self.parse_title(ctx, title)
        
        import yaml
        #Read YAML file
        with open("./vinetrimmer/config/Services/globoplay.yml", 'r') as stream:
            self.config = yaml.safe_load(stream)

        self.acodec = ctx.parent.params["acodec"]
        
        self.headers = {
            'authority': 'globo.com',
            'referer': 'https://globoplay.globo.com/',
            'user-agent': self.config["UserAgent"]
        }
        
    def get_titles(self):
        glbapi=self.config["endpoints"]["title"]
        
        res = self.session.get(
                glbapi.format(title_id=self.title),
                headers=self.headers).json()
        try:
            res
        except json.JSONDecodeError:
            raise self.log.exit(f" - Failed to load title manifest: {res.text}")

        original_language = "pt-BR"
        fres=res["videos"]
        return Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=(fres[0]["program"]+" - "+fres[0]["title"]),
                original_lang=original_language,
                source=self.ALIASES[0],
                service_data=res,
            )
        
    def get_tracks(self, title):
        payload = { "player_type": self.config["video-request"]["playerType"], "video_id": self.title, "quality": "max", "content_protection": "widevine", "tz": "-03:00", "version": 2 }

        cookies = self.session.cookies.get_dict()
        self.session.cookies.update(cookies)
        self.session.headers.update({
			"authorization": f"Bearer {cookies['GLBID']}"
        })
        program_data = self.session.post(
			url=self.config["endpoints"]["video-session"],
			json=payload,
			headers=self.headers
		).json()

        manifest_url=program_data["sources"][0]["url"]
        self.log.warning(f" + Downloading Manifest ---> {manifest_url}")
        
        try:
            self.lic_url=program_data["resource"]["content_protection"]["server"].replace("{{deviceId}}", self.config["WVDeviceID"])
        except:
            pass
        
        if manifest_url.find(".mpd")>=1:
            return Tracks.from_mpd(
                url=manifest_url,
                session=self.session,
                source=self.ALIASES[0]
            )
        elif manifest_url.find(".ism")>=1:
            return Tracks.from_ism(
                url=manifest_url,
                session=self.session,
                source=self.ALIASES[0]
            )
        else:
            tracks = Tracks.from_m3u8(m3u8.load(manifest_url), source=self.ALIASES[0])
            if self.acodec:
                tracks.audios = [
                    x for x in tracks.audios if (x.codec or "").split("-")[0] in self.AUDIO_CODEC_MAP[self.acodec]
                ]
            for video in tracks.videos:
                # This is needed to remove weird glitchy NOP data at the end of stream
                video.needs_repack = True
            return tracks

    def get_chapters(self, title):
        return []

    def certificate(self, **kwargs):
        return self.license(**kwargs)

    def license(self, challenge, **_):
        lic = self.session.post(
            url=self.config["licenseUrl"],
            headers=self.headers,
            data=challenge  # expects bytes
        )
        return lic.content 
